#!/usr/bin/env python3
"""Verify checked thread-pool startup using deterministic C fault injection."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "compiler/tb/runtime"
CASES = {
    "malloc1": (0, 0, 0, 0),
    "malloc2": (1, 0, 0, 0),
    "mutex": (2, 0, 0, 0),
    "cond": (2, 1, 0, 0),
    "create0": (2, 1, 1, 0),
    "create1": (2, 1, 1, 1),
    "create2": (2, 1, 1, 2),
    "create3": (2, 1, 1, 3),
    "zero": (0, 0, 0, 0),
    "negative": (0, 0, 0, 0),
    "overflow": (0, 0, 0, 0),
    "success1": (4, 2, 2, 1),
    "success2": (4, 2, 2, 2),
    "success4": (4, 2, 2, 4),
}


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--sanitizers", action="store_true",
                        help="also verify instrumented ASan/TSan runs and bad controls")
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    evidence = args.evidence_dir or Path(tempfile.mkdtemp(prefix="tb-pool-startup-"))
    evidence = evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    inputs = [Path(__file__), ROOT / "tests/thread_pool_startup_test.c",
              RUNTIME / "thread_pool_runtime.c",
              RUNTIME / "thread_pool_composite_runtime.c",
              RUNTIME / "thread_pool_composite_runtime.h"]
    manifest = {"status": "running", "inputs": {str(p): fingerprint(p) for p in inputs},
                "processes": [], "sanitizer_hooks": {}}
    env = os.environ.copy()
    env.pop("TB_RESOURCE_ROOT", None)
    env.pop("PYTHONPATH", None)
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    env["TSAN_OPTIONS"] = "halt_on_error=1"
    manifest["environment_overrides"] = {
        key: env.get(key) for key in
        ("TB_RESOURCE_ROOT", "PYTHONPATH", "ASAN_OPTIONS", "TSAN_OPTIONS")}

    def save():
        (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def run(command, label, expected=0, timeout=30):
        index = len(manifest["processes"])
        start = time.monotonic()
        try:
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                    text=True, timeout=timeout)
            status, stdout, stderr = result.returncode, result.stdout, result.stderr
            timed_out = False
        except subprocess.TimeoutExpired as error:
            status, timed_out = None, True
            stdout = error.stdout or b""
            stderr = error.stderr or b""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
        prefix = evidence / f"{index:03d}-{label}"
        Path(str(prefix) + ".stdout").write_text(stdout)
        Path(str(prefix) + ".stderr").write_text(stderr)
        record = {"command": [str(c) for c in command], "cwd": str(ROOT),
                  "label": label, "exit_code": status, "expected_exit": expected,
                  "timeout": timed_out, "elapsed_seconds": time.monotonic() - start,
                  "stdout": str(prefix) + ".stdout", "stderr": str(prefix) + ".stderr"}
        manifest["processes"].append(record)
        save()
        if timed_out or (expected is not None and status != expected):
            raise RuntimeError(f"{label}: unexpected status {status}; see {prefix}")
        return status, stdout, stderr

    def compile_test(name, flags, runtime=RUNTIME):
        binary = evidence / name
        command = [args.clang, "-std=c11", "-Wall", "-Wextra", "-Werror",
                   *flags, "-pthread", "-I" + str(runtime),
                   str(ROOT / "tests/thread_pool_startup_test.c"),
                   str(RUNTIME / "thread_pool_composite_runtime.c"), "-o", str(binary)]
        run(command, "build-" + name)
        manifest.setdefault("binaries", {})[str(binary)] = fingerprint(binary)
        return binary

    def verify_case(binary, mode, label):
        success = mode.startswith("success")
        _, stdout, stderr = run([str(binary), mode], label, 0 if success else 1)
        allocations, mutexes, conditions, workers = CASES[mode]
        expected = (f"allocated={allocations} freed={allocations} "
                    f"mutex={mutexes}/{mutexes} cond={conditions}/{conditions} "
                    f"started={workers} entered={workers} joined={workers} "
                    f"jobs={int(success)}\n")
        diagnostic = ("" if success else
                      "thread_pool requires a thread count from 1 to 2147483647\n"
                      if mode in ("zero", "negative", "overflow") else
                      "thread_pool startup failed\n")
        if stdout != expected or stderr != diagnostic:
            raise RuntimeError(f"{label}: accounting or diagnostic mismatch")

    try:
        run([args.clang, "--version"], "clang-version")
        for optimization in ("O0", "O2"):
            binary = compile_test(optimization, ["-" + optimization])
            for mode in CASES:
                verify_case(binary, mode, optimization + "-" + mode)

        # An actual broken cleanup implementation must fail the same accounting.
        bad_runtime = evidence / "missing-cleanup-runtime"
        bad_runtime.mkdir(exist_ok=True)
        original = (RUNTIME / "thread_pool_runtime.c").read_text()
        marker = "startup_failed:\n"
        if original.count(marker) != 1:
            raise RuntimeError("startup cleanup selector did not match exactly once")
        bad = original.replace(marker, marker +
                               '    fputs("thread_pool startup failed\\n", stderr);\n'
                               "    exit(1);\n", 1)
        (bad_runtime / "thread_pool_runtime.c").write_text(bad)
        (bad_runtime / "thread_pool_composite_runtime.h").write_bytes(
            (RUNTIME / "thread_pool_composite_runtime.h").read_bytes())
        binary = compile_test("missing-cleanup", ["-O0"], bad_runtime)
        status, _, stderr = run([str(binary), "create2"], "bad-cleanup-control", 90)
        if "startup test failed: allocation leak" not in stderr:
            raise RuntimeError("broken cleanup control was not detected")

        if args.sanitizers:
            controls = {
                "address": """#include <stdlib.h>
int main(int argc, char** argv) {
    (void)argv;
    volatile int* p = malloc(sizeof(int));
    p[argc] = 7;
    free((void*)p);
    return 0;
}
""",
                "thread": """#include <pthread.h>
static volatile int value;
static void* work(void* p) { (void)p; for (int i=0;i<10000;i++) value++; return 0; }
int main(void) {
    pthread_t a,b;
    pthread_create(&a,0,work,0); pthread_create(&b,0,work,0);
    pthread_join(a,0); pthread_join(b,0); return value == -1;
}
""",
            }
            for sanitizer in ("address", "thread"):
                flags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=" + sanitizer]
                binary = compile_test(sanitizer, flags)
                llvm = evidence / (sanitizer + ".ll")
                run([args.clang, "-std=c11", *flags, "-pthread", "-I" + str(RUNTIME),
                     "-S", "-emit-llvm", str(ROOT / "tests/thread_pool_startup_test.c"),
                     "-o", str(llvm)], "instrumentation-" + sanitizer)
                ir = llvm.read_text()
                expression = (r"\bcall\b[^\n]*@__asan_(?:report_(?:load|store)|(?:load|store))\w*\("
                              if sanitizer == "address" else
                              r"\bcall\b[^\n]*@__tsan_(?:read|write)\w*\(")
                hooks = len(re.findall(expression, ir))
                runtime_hooks = {}
                for function in ("tb_thread_pool_new", "tb_thread_pool_worker"):
                    match = re.search(r"^define [^\n]*@" + function +
                                      r"\([^\n]*\).*?^}", ir, re.M | re.S)
                    if match is None:
                        raise RuntimeError("missing instrumented runtime function: " + function)
                    runtime_hooks[function] = len(re.findall(expression, match.group()))
                    if runtime_hooks[function] == 0:
                        raise RuntimeError("no actual memory hooks in " + function)
                composite_llvm = evidence / (sanitizer + "-composite.ll")
                run([args.clang, "-std=c11", *flags, "-pthread", "-S", "-emit-llvm",
                     str(RUNTIME / "thread_pool_composite_runtime.c"),
                     "-o", str(composite_llvm)], "instrumentation-composite-" + sanitizer)
                composite_hooks = len(re.findall(expression, composite_llvm.read_text()))
                if composite_hooks == 0:
                    raise RuntimeError("no actual composite runtime memory hooks: " + sanitizer)
                manifest["sanitizer_hooks"][sanitizer] = {
                    "actual_calls": hooks, "runtime_functions": runtime_hooks,
                    "llvm_sha256": fingerprint(llvm),
                    "composite_actual_calls": composite_hooks,
                    "composite_llvm_sha256": fingerprint(composite_llvm)}
                if hooks == 0:
                    raise RuntimeError("no actual sanitizer memory hooks: " + sanitizer)
                for mode in CASES:
                    verify_case(binary, mode, sanitizer + "-" + mode)
                control = evidence / ("bad-" + sanitizer + ".c")
                control.write_text(controls[sanitizer])
                control_binary = evidence / ("bad-" + sanitizer)
                run([args.clang, *flags, "-pthread", str(control), "-o", str(control_binary)],
                    "build-bad-" + sanitizer)
                status, _, stderr = run([str(control_binary)], "bad-" + sanitizer,
                                        expected=None)
                required = "AddressSanitizer: heap-buffer-overflow" if sanitizer == "address" else "ThreadSanitizer: data race"
                if status == 0 or required not in stderr:
                    raise RuntimeError("sanitizer bad control was not detected: " + sanitizer)

        final_inputs = {str(p): fingerprint(p) for p in inputs}
        if final_inputs != manifest["inputs"]:
            raise RuntimeError("inputs changed while verification ran")
        manifest["status"] = "passed"
        save()
        print("thread-pool startup checks passed; evidence: " + str(evidence / "manifest.json"))
        return 0
    except (OSError, RuntimeError) as error:
        manifest["status"] = "failed"
        manifest["error"] = str(error)
        save()
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
