#!/usr/bin/env python3
"""Verify deterministic thread-pool queue, shutdown, future, and ownership behavior."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests/fixtures/164.tb"
EXPECTED = ROOT / "tests/fixtures/164.out"
DRIVER = ROOT / "tests/thread_pool_lifecycle_test.c"
RUNTIME = ROOT / "compiler/tb/runtime/thread_pool_runtime.c"
COMPOSITE = ROOT / "compiler/tb/runtime/thread_pool_composite_runtime.c"
HEADER = ROOT / "compiler/tb/runtime/thread_pool_composite_runtime.h"
INPUTS = (Path(__file__), FIXTURE, EXPECTED, DRIVER, RUNTIME, COMPOSITE, HEADER)
HOOKS = {
    "address": r"\bcall\b[^\n]*@__asan_(?:report_(?:load|store)|(?:load|store))\w*\(",
    "thread": r"\bcall\b[^\n]*@__tsan_(?:read|write|unaligned_(?:read|write))\w*\(",
}
TSAN_ATOMIC_CALL = r"\bcall\b[^\n]*@__tsan_atomic(?:8|16|32|64|128)_\w+\s*\("
HOOKED_GENERATED_FUNCTIONS = (
    "lifecycle_string", "lifecycle_message", "lifecycle_array", "lifecycle_nested",
    "fail_lifecycle_int", "fail_lifecycle_bool", "fail_lifecycle_string",
    "fail_lifecycle_array", "fail_lifecycle_nested",
)
HOOKED_HELPERS = (
    "tb_retain", "tb_release", "tb_string_new",
    "tb_bootstrap_string_concat", "tb_bootstrap_string_copy",
    "tb_bootstrap_int_array_get",
    "tb_bootstrap_int_array_set", "tb_bootstrap_int_array_clone",
    "tb_bootstrap_int_array_array_get", "tb_bootstrap_int_array_array_set_owned",
    "tb_bootstrap_int_array_array_clone",
)
DIRECT_HOOK_HELPERS = (
    "tb_retain", "tb_release", "tb_string_new",
    "tb_bootstrap_int_array_get", "tb_bootstrap_int_array_set",
    "tb_bootstrap_int_array_clone", "tb_bootstrap_int_array_array_get",
    "tb_bootstrap_int_array_array_set_owned",
    "tb_bootstrap_int_array_array_clone",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(path):
    return sha256_bytes(Path(path).read_bytes())


def controlled_environment(sanitizer=None):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
    for name in ("TMPDIR", "DEVELOPER_DIR", "SDKROOT"):
        if name in os.environ:
            env[name] = os.environ[name]
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    env["TSAN_OPTIONS"] = "halt_on_error=1"
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, default=ROOT / "bin/tb")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--seed", type=int, default=7,
                        help="integer task input used by the deterministic scenario")
    parser.add_argument("--repeat", type=int, default=10,
                        help="TSan rounds when --sanitizers or --all is selected")
    parser.add_argument("--mode", choices=("focused", "sanitizers", "all"),
                        default="focused", help="focused O2 check or full sanitizer evidence batch")
    parser.add_argument("--sanitizers", action="store_true",
                        help="run O0/O2, real ASan, real TSan, and sanitizer controls")
    parser.add_argument("--all", action="store_true",
                        help="alias for --sanitizers and the complete scoped verification")
    args = parser.parse_args()
    full = args.sanitizers or args.all or args.mode in ("sanitizers", "all")
    if args.repeat < 10 and full:
        parser.error("sanitizer verification requires --repeat of at least 10")
    if args.seed < -1000000 or args.seed > 1000000 or (full and
            (args.seed + args.repeat < -1000000 or args.seed + args.repeat > 1000000)):
        parser.error("seed and repeated seeds must stay between -1000000 and 1000000")
    compiler = args.compiler.resolve()
    if not compiler.is_file():
        parser.error("missing compiler binary: " + str(compiler))
    clang = shutil.which(args.clang)
    if clang is None:
        parser.error("clang executable not found: " + args.clang)
    evidence = (args.evidence_dir or
                Path(tempfile.mkdtemp(prefix="tb-pool-lifecycle-"))).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    output_dir = evidence / "runs"
    output_dir.mkdir(exist_ok=True)
    env = controlled_environment()
    manifest = {
        "status": "running",
        "root": str(ROOT),
        "evidence_dir": str(evidence),
        "compiler": str(compiler),
        "compiler_sha256_at_emission": fingerprint(compiler),
        "inputs_sha256": {str(path): fingerprint(path) for path in INPUTS},
        "seed": args.seed,
        "repeat": args.repeat,
        "environment_policy": "clean environment; PATH, LC_ALL, TMPDIR, DEVELOPER_DIR, SDKROOT and sanitizer options only",
        "environment": env,
        "processes": [],
        "generated_llvm": {},
        "allocation_selectors": {},
        "sanitizer_audit": {},
    }

    def save():
        (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def run(command, label, expected=0, timeout=90, run_env=None, cwd=ROOT):
        index = len(manifest["processes"])
        prefix = output_dir / f"{index:03d}-{label}"
        start = time.monotonic()
        try:
            result = subprocess.run([str(item) for item in command], cwd=cwd,
                                    env=run_env or env, capture_output=True,
                                    text=True, timeout=timeout)
            code, stdout, stderr, timed_out = result.returncode, result.stdout, result.stderr, False
        except subprocess.TimeoutExpired as error:
            code, timed_out = None, True
            stdout = error.stdout or b""
            stderr = error.stderr or b""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
        stdout_path = Path(str(prefix) + ".stdout")
        stderr_path = Path(str(prefix) + ".stderr")
        stdout_path.write_text(stdout)
        stderr_path.write_text(stderr)
        record = {
            "label": label,
            "command": [str(item) for item in command],
            "cwd": str(cwd),
            "environment": run_env or env,
            "exit_code": code,
            "expected_exit": expected,
            "timed_out": timed_out,
            "timeout_seconds": timeout,
            "elapsed_seconds": time.monotonic() - start,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout_sha256": sha256_bytes(stdout.encode()),
            "stderr_sha256": sha256_bytes(stderr.encode()),
        }
        manifest["processes"].append(record)
        save()
        if timed_out or (expected is not None and code != expected):
            raise RuntimeError(f"{label}: status {code}, expected {expected}; see {prefix}")
        return code, stdout, stderr

    def compile_fixture(label, path):
        command = [compiler, FIXTURE, path]
        run(command, label + "-emit-llvm")
        return path.read_text()

    def rewrite_allocators(raw, output):
        renamed = re.sub(r"@main(?=\s*\()", "@tb_fixture_main", raw)
        exception_copies = {}
        for name in ("fail_lifecycle_int", "fail_lifecycle_bool", "fail_lifecycle_string",
                     "fail_lifecycle_array", "fail_lifecycle_nested"):
            match = re.search(r"^define [^\n]*@" + name +
                              r"\([^\n]*\).*?^}", renamed, re.M | re.S)
            if match is None:
                raise RuntimeError("missing generated failing worker for ownership selector: " + name)
            exception_copies[name] = len(re.findall(
                r"\bcall\b[^\n]*@tb_bootstrap_string_copy\s*\(", match.group()))
            if exception_copies[name] != 1:
                raise RuntimeError("expected exactly one owned throw-string copy in " + name)
        counts = {}
        for name in ("malloc", "calloc", "realloc", "free"):
            pattern = rf"@{name}(?=\s*\()"
            counts[name] = len(re.findall(rf"\bcall\b[^\n]*{pattern}", renamed))
            renamed = re.sub(pattern, "@tb_audit_" + name, renamed)
        remaining = re.findall(r"\bcall\b[^\n]*@(malloc|calloc|realloc|free)\s*\(", renamed)
        if remaining:
            raise RuntimeError("unwrapped allocator calls remain in generated LLVM: " + repr(remaining))
        output.write_text(renamed)
        observed = {name: len(re.findall(rf"\bcall\b[^\n]*@tb_audit_{name}\s*\(", renamed))
                    for name in counts}
        if counts != observed:
            raise RuntimeError("allocator selector rewrite count mismatch")
        manifest["allocation_selectors"] = {
            "scope": "all allocation calls in generated fixture LLVM; runtime and composite C included under the same wrappers",
            "before_rewrite_call_counts": counts,
            "after_rewrite_call_counts": observed,
            "wrapper_symbols": {name: "tb_audit_" + name for name in counts},
            "retained_failure_string_copy_calls": exception_copies,
            "source_sha256": sha256_bytes(raw.encode()),
            "rewritten_sha256": fingerprint(output),
            "note": "libc, pthread, sanitizer, and test-process allocations are outside the tracker",
        }
        return renamed

    def audit_hooks(mode, llvm_path):
        pattern = HOOKS[mode]
        source = llvm_path.read_text()
        all_hooks = len(re.findall(pattern, source))
        generated_counts = {}
        for name in HOOKED_GENERATED_FUNCTIONS + HOOKED_HELPERS:
            match = re.search(r"^define [^\n]*@" + re.escape(name) +
                              r"\([^\n]*\).*?^}", source, re.M | re.S)
            if match is None:
                raise RuntimeError("missing generated lifecycle worker in instrumented LLVM: " + name)
            count = len(re.findall(pattern, match.group()))
            generated_counts[name] = count
            atomic_count = len(re.findall(TSAN_ATOMIC_CALL, match.group()))
            if count == 0 and not (mode == "thread" and atomic_count) and name in DIRECT_HOOK_HELPERS:
                raise RuntimeError(f"no actual {mode} heap-memory hooks in generated helper {name}")
            if mode == "thread" and name in ("tb_retain", "tb_release") and atomic_count == 0:
                raise RuntimeError(f"no actual TSan refcount atomic hook in generated helper {name}")
        if all_hooks == 0:
            raise RuntimeError("no actual sanitizer calls found in generated LLVM")
        c_llvm = evidence / (mode + "-c-units.ll")
        flags = ["-O0", "-g", "-fno-omit-frame-pointer", "-fno-inline",
                 "-fsanitize=" + mode]
        run([clang, "-std=c11", *flags, "-pthread", "-I" + str(RUNTIME.parent),
             "-S", "-emit-llvm", DRIVER, "-o", c_llvm], mode + "-emit-c-units")
        c_source = c_llvm.read_text()
        c_hooks = len(re.findall(pattern, c_source))
        c_function_counts = {}
        for name in ("tb_thread_pool_new", "tb_thread_pool_worker",
                     "tb_thread_pool_int_array_snapshot",
                     "tb_thread_pool_int_array_array_snapshot"):
            match = re.search(r"^define [^\n]*@" + re.escape(name) +
                              r"\([^\n]*\).*?^}", c_source, re.M | re.S)
            count = 0 if match is None else len(re.findall(pattern, match.group()))
            c_function_counts[name] = count
            if count == 0:
                raise RuntimeError(f"no actual {mode} hooks in included C runtime function {name}")
        if c_hooks == 0:
            raise RuntimeError("no actual sanitizer calls found in included runtime/composite/test C units")
        manifest["sanitizer_audit"][mode] = {
            "generated_llvm_sha256": fingerprint(llvm_path),
            "generated_actual_hook_calls": all_hooks,
            "generated_function_hook_calls": generated_counts,
            "generated_function_tsan_atomic_calls": {
                name: len(re.findall(TSAN_ATOMIC_CALL,
                                     re.search(r"^define [^\n]*@" + re.escape(name) +
                                               r"\([^\n]*\).*?^}", source, re.M | re.S).group()))
                for name in HOOKED_GENERATED_FUNCTIONS + HOOKED_HELPERS
            },
            "generated_bulk_memory_helper_calls": len(re.findall(
                r"\bcall\b[^\n]*@__asan_mem(?:cpy|move|set)\s*\(", source)),
            "generated_tsan_atomic_calls": len(re.findall(
                TSAN_ATOMIC_CALL, source)),
            "included_c_units_llvm_sha256": fingerprint(c_llvm),
            "included_c_actual_hook_calls": c_hooks,
            "included_c_function_hook_calls": c_function_counts,
        }
        save()

    def annotate_generated_llvm(source_path, mode):
        attribute = "sanitize_address" if mode == "address" else "sanitize_thread"
        lines = Path(source_path).read_text().splitlines()
        definitions = 0
        annotated = []
        for line in lines:
            if re.match(r"^define\b", line) and line.rstrip().endswith("{"):
                line = line.rstrip()[:-1].rstrip() + " " + attribute + " {"
                definitions += 1
            annotated.append(line)
        if definitions == 0:
            raise RuntimeError("no generated LLVM function definitions to instrument")
        output = evidence / (mode + "-fixture164-annotated.ll")
        output.write_text("\n".join(annotated) + "\n")
        manifest.setdefault("sanitizer_attributes", {})[mode] = {
            "attribute": attribute,
            "generated_functions_annotated": definitions,
            "source_sha256": fingerprint(source_path),
            "annotated_llvm_path": str(output),
            "annotated_llvm_sha256": fingerprint(output),
        }
        save()
        return output

    def build_fixture_smoke(raw_llvm):
        binary = evidence / "fixture164-native"
        run([clang, raw_llvm, RUNTIME, COMPOSITE, "-pthread", "-o", binary],
            "fixture164-native-link")
        _, stdout, stderr = run([binary], "fixture164-native-run")
        expected = EXPECTED.read_text()
        if stdout != expected or stderr:
            raise RuntimeError("fixture164 native output differs from tests/fixtures/164.out")
        manifest["fixture164_native"] = {"stdout": stdout, "expected": expected,
                                         "source_sha256": fingerprint(FIXTURE),
                                         "output_sha256": fingerprint(EXPECTED),
                                         "llvm_sha256": fingerprint(raw_llvm),
                                         "binary_sha256": fingerprint(binary)}
        save()

    def build_harness(label, llvm_path, flags):
        binary = evidence / ("lifecycle-" + label)
        command = [clang, "-std=c11", "-Wall", "-Wextra", "-Werror",
                   "-Wno-override-module", *flags,
                   "-pthread", "-I" + str(RUNTIME.parent), llvm_path, DRIVER, "-o", binary]
        run(command, "build-" + label)
        manifest.setdefault("binaries", {})[str(binary)] = fingerprint(binary)
        return binary

    def run_harness(binary, label, seed, expected=0, timeout=90, run_env=None):
        code, stdout, stderr = run([binary, str(seed)], label, expected=expected,
                                   timeout=timeout, run_env=run_env)
        expected_pattern = rf"^lifecycle seed={seed} tasks=84 queue=80 checkpoint=110/(\d+) final=0/0\n$"
        match = re.fullmatch(expected_pattern, stdout)
        if expected == 0 and (match is None or stderr):
            raise RuntimeError(f"{label}: stdout/stderr did not match the exact lifecycle summary")
        if match is not None:
            manifest.setdefault("lifecycle_runs", {})[label] = {
                "seed": seed,
                "checkpoint_blocks": 110,
                "checkpoint_bytes": int(match.group(1)),
                "stdout": stdout,
                "stderr": stderr,
            }
            save()
        return code, stdout, stderr

    def cleanup_negative_control(rewritten_llvm):
        bad_root = evidence / "missing-task-cleanup"
        bad_tests = bad_root / "tests"
        bad_runtime = bad_root / "compiler/tb/runtime"
        bad_tests.mkdir(parents=True, exist_ok=True)
        bad_runtime.mkdir(parents=True, exist_ok=True)
        bad_driver = bad_tests / DRIVER.name
        bad_driver.write_bytes(DRIVER.read_bytes())
        original = RUNTIME.read_text()
        selector = "        free(task);"
        if original.count(selector) != 1:
            raise RuntimeError("runtime task cleanup selector did not match exactly once")
        (bad_runtime / RUNTIME.name).write_text(original.replace(selector,
            "        /* known-bad control: selected task allocation intentionally leaked */", 1))
        (bad_runtime / COMPOSITE.name).write_bytes(COMPOSITE.read_bytes())
        (bad_runtime / HEADER.name).write_bytes(HEADER.read_bytes())
        binary = evidence / "lifecycle-missing-task-cleanup"
        command = [clang, "-std=c11", "-Wall", "-Wextra", "-Werror",
                   "-Wno-override-module", "-O0",
                   "-pthread", "-I" + str(bad_runtime), rewritten_llvm, bad_driver,
                   "-o", binary]
        run(command, "build-known-bad-cleanup")
        code, _, stderr = run([binary, str(args.seed)], "known-bad-cleanup",
                              expected=91, timeout=90)
        if "live allocation checkpoint did not contain 110 selected blocks" not in stderr:
            raise RuntimeError("known-bad cleanup did not fail the selected allocation checkpoint")
        manifest["known_bad_cleanup"] = {
            "mutated_source": str(bad_runtime / RUNTIME.name),
            "selector": "free(task); in tb_thread_pool_worker",
            "mutation": "removed exactly one runtime task-node free",
            "exit_code": code,
            "expected_failure": "tracked selected live-block checkpoint is greater than 110",
        }
        save()

    try:
        manifest["formula_before_runs"] = {
            "checkpoint_live_blocks": 110,
            "expected_blocks": "40 futures + 6 managed string results + 12 int[] result allocations + 42 nested-array result allocations + 10 distinct owned error messages retained by the 10 failed futures",
            "checkpoint_bytes": "8*(sizeof(future_i64)+sizeof(future_bool)+sizeof(future_string)+2*sizeof(future_array)) + 6*(24+strlen(message)+1+1) + 10*(24+strlen(message)+1) + 6*(sizeof(int_array)+4*sizeof(int64_t)) + 6*(sizeof(int_array_array)+2*sizeof(void*)+2*sizeof(unsigned char)+2*(sizeof(int_array)+4*sizeof(int64_t)))",
            "empty_malloc_rule": "selected malloc(0) calls allocate one physical byte and retain requested size zero in the tracker",
            "scope": "explicit allocations from generated LLVM plus included thread-pool/composite C sources only",
        }
        (evidence / "allocation-formula.json").write_text(
            json.dumps(manifest["formula_before_runs"], indent=2) + "\n")
        save()

        run([clang, "--version"], "clang-version")
        raw_path = evidence / "fixture164-raw.ll"
        raw = compile_fixture("fixture164", raw_path)
        manifest["generated_llvm"] = {
            "compiler": str(compiler),
            "compiler_sha256": fingerprint(compiler),
            "fixture_source_sha256_at_emission": fingerprint(FIXTURE),
            "command": [str(compiler), str(FIXTURE), str(raw_path)],
            "cwd": str(ROOT),
            "environment": env,
            "raw_llvm_path": str(raw_path),
            "raw_llvm_sha256": fingerprint(raw_path),
        }
        rewritten_path = evidence / "fixture164-tracked.ll"
        rewritten = rewrite_allocators(raw, rewritten_path)
        build_fixture_smoke(raw_path)
        plain = build_harness("O2", rewritten_path, ["-O2"])
        run_harness(plain, "O2-seed-" + str(args.seed), args.seed)
        cleanup_negative_control(rewritten_path)

        if full:
            for optimization in ("O0",):
                binary = build_harness(optimization, rewritten_path, ["-" + optimization])
                run_harness(binary, optimization + "-seed-" + str(args.seed), args.seed)

            sanitizer_paths = {}
            for sanitizer in ("address", "thread"):
                flags = ["-O0", "-g", "-fno-omit-frame-pointer", "-fno-inline",
                         "-fsanitize=" + sanitizer]
                annotated_llvm = annotate_generated_llvm(rewritten_path, sanitizer)
                instrumented = evidence / (sanitizer + "-fixture164.ll")
                run([clang, "-x", "ir", *flags, "-S", "-emit-llvm", annotated_llvm,
                     "-o", instrumented], "instrument-" + sanitizer)
                audit_hooks(sanitizer, instrumented)
                binary = build_harness(sanitizer, annotated_llvm, flags)
                sanitizer_paths[sanitizer] = {"binary": binary, "flags": flags}
                manifest["sanitizer_audit"][sanitizer]["instrumented_binary_sha256"] = fingerprint(binary)
                manifest["sanitizer_audit"][sanitizer]["build_input_llvm_sha256"] = fingerprint(annotated_llvm)
                manifest["sanitizer_audit"][sanitizer]["audited_instrumented_llvm_sha256"] = fingerprint(instrumented)
                run_harness(binary, sanitizer + "-seed-" + str(args.seed), args.seed,
                            timeout=120)

            bad_address = evidence / "bad-address.c"
            bad_address.write_text("""#include <stdlib.h>
int main(int argc, char** argv) {
    (void)argv;
    int* value = (int*)malloc(sizeof(int));
    if (value == 0) return 2;
    value[0] = argc;
    volatile int* stale = value;
    free(value);
    int index = argc & 0;
    volatile int result = stale[index];
    return result == 0;
}
""")
            bad_address_binary = evidence / "bad-address"
            asan_flags = sanitizer_paths["address"]["flags"]
            run([clang, *asan_flags, bad_address, "-o", bad_address_binary],
                "build-known-bad-asan")
            asan_env = dict(env)
            asan_env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            asan_status, _, asan_stderr = run([bad_address_binary], "known-bad-asan",
                                               expected=None, run_env=asan_env)
            if asan_status == 0:
                raise RuntimeError("ASan known-bad control unexpectedly succeeded")
            if "AddressSanitizer:" not in asan_stderr or "heap-use-after-free" not in asan_stderr:
                raise RuntimeError("ASan known-bad use-after-free control was not detected")

            bad_thread = evidence / "bad-thread.c"
            bad_thread.write_text("""#include <pthread.h>
static volatile int shared_value;
static void* worker(void* ignored) {
    (void)ignored;
    for (int index = 0; index < 100000; index += 1) shared_value += 1;
    return 0;
}
int main(void) {
    pthread_t first, second;
    pthread_create(&first, 0, worker, 0);
    pthread_create(&second, 0, worker, 0);
    pthread_join(first, 0);
    pthread_join(second, 0);
    return 0;
}
""")
            bad_thread_binary = evidence / "bad-thread"
            tsan_flags = sanitizer_paths["thread"]["flags"]
            run([clang, *tsan_flags, "-pthread", bad_thread, "-o", bad_thread_binary],
                "build-known-bad-tsan")
            tsan_status, _, tsan_stderr = run([bad_thread_binary], "known-bad-tsan",
                                               expected=None, timeout=120)
            if tsan_status == 0:
                raise RuntimeError("TSan known-bad control unexpectedly succeeded")
            if "ThreadSanitizer: data race" not in tsan_stderr:
                raise RuntimeError("TSan known-bad race control was not detected")

            for round_index in range(args.repeat):
                seed = args.seed + round_index + 1
                run_harness(sanitizer_paths["thread"]["binary"],
                            f"thread-repeat-{round_index + 1:02d}-seed-{seed}",
                            seed, timeout=120)

        final_inputs = {str(path): fingerprint(path) for path in INPUTS}
        if final_inputs != manifest["inputs_sha256"]:
            raise RuntimeError("a verification input changed during the run")
        if fingerprint(compiler) != manifest["compiler_sha256_at_emission"]:
            raise RuntimeError("compiler binary changed during verification")
        manifest["status"] = "passed"
        manifest["final_inputs_sha256"] = final_inputs
        manifest["summary"] = {
            "fixture164": "passed exact native output comparison",
            "lifecycle": "passed 84-task blocked queue scenario; 80 queued behind four blockers",
            "allocation_checkpoint": "110 selected blocks with formula-derived exact bytes; zero after retained futures released",
            "full_sanitizers": full,
            "tsan_repeats": args.repeat if full else 0,
        }
        save()
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        save()
        raise
    print(json.dumps({"status": manifest["status"], "evidence_dir": str(evidence),
                      "processes": len(manifest["processes"]),
                      "summary": manifest["summary"]}, indent=2))


if __name__ == "__main__":
    main()
