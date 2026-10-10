#!/usr/bin/env python3
"""Verify self-hosted compiler resource lookup outside the checkout cwd."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED = {1: "4\n1\n", 2: "9\n4\n", 3: "16\n9\n"}
MAIN_SOURCE = """import support;

int work(int value):
    return square(value)

int main(string[] args):
    int n = args.length()
    thread_pool pool = thread_pool(2)
    future<int> pending = pool.submit(work, n)
    print(square(n + 1))
    print(pending.await())
    return 0
"""
SUPPORT_SOURCE = """int square(int value):
    return value * value
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(value for value in path.rglob("*") if value.is_file()):
        name = item.relative_to(path).as_posix().encode()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(bytes.fromhex(sha256(item)))
    return digest.hexdigest()


def resource_tree_sha256(root: Path) -> str:
    paths = list((root / "compiler/tb/llvm_helpers").rglob("*"))
    paths.extend(
        root / "compiler/tb/runtime" / name
        for name in (
            "thread_pool_runtime.c",
            "thread_pool_composite_runtime.c",
            "thread_pool_composite_runtime.h",
        )
    )
    digest = hashlib.sha256()
    for item in sorted(path for path in paths if path.is_file()):
        name = item.relative_to(root).as_posix().encode()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(bytes.fromhex(sha256(item)))
    return digest.hexdigest()


def assets_are_read_only(root: Path) -> bool:
    return all(not (item.stat().st_mode & 0o222) for item in [root, *root.rglob("*")])


class Verifier:
    def __init__(self, compiler: Path, evidence_dir: Path):
        self.compiler = compiler.resolve()
        self.evidence_dir = evidence_dir.resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.runs: list[dict[str, object]] = []
        self.generations: list[dict[str, object]] = []
        self.compiler_hash = sha256(self.compiler)

    def run(
        self,
        name: str,
        argv: list[str],
        cwd: Path,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for key, value in (env_overrides or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        process = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        self.runs.append(
            {
                "name": name,
                "argv": argv,
                "cwd": str(cwd),
                "env_overrides": env_overrides or {},
                "exit_status": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
            }
        )
        return process

    def compile_and_run(
        self,
        name: str,
        source: Path,
        output: Path,
        cwd: Path,
        env: dict[str, str | None],
        profile: bool = False,
    ) -> None:
        source_inputs = sorted(source.parent.glob("*.tb"))
        source_fingerprints = {str(path): sha256(path) for path in source_inputs}
        asset_root = Path(env["TB_RESOURCE_ROOT"]).resolve() if env.get("TB_RESOURCE_ROOT") else None
        asset_fingerprint = resource_tree_sha256(asset_root) if asset_root else None
        argv = [str(self.compiler)]
        if profile:
            argv.append("--profile-phases")
        argv.extend([str(source), str(output)])
        process = self.run(name + " compile", argv, cwd, env)
        self.require(process.returncode == 0, f"{name} compile failed: {process.stderr}{process.stdout}")
        self.require(sha256(self.compiler) == self.compiler_hash, f"compiler changed during {name}")
        self.require(
            {str(path): sha256(path) for path in source_inputs} == source_fingerprints,
            f"source/import inputs changed during {name}",
        )
        if asset_root is not None:
            self.require(resource_tree_sha256(asset_root) == asset_fingerprint, f"resource assets changed during {name}")
        self.generations.append(
            {
                "name": name,
                "compiler": str(self.compiler),
                "compiler_sha256": self.compiler_hash,
                "source_sha256": sha256(source),
                "raw_llvm": str(output),
                "raw_llvm_sha256": sha256(output),
                "source_and_import_sha256": source_fingerprints,
                "resource_asset_root": str(asset_root) if asset_root else None,
                "resource_asset_tree_sha256": asset_fingerprint,
                "compile_argv": argv,
                "cwd": str(cwd),
                "env_overrides": env,
            }
        )
        metadata = Path(str(output) + ".csources")
        cflags = Path(str(output) + ".cflags").read_text(encoding="utf-8").splitlines()
        sources = metadata.read_text(encoding="utf-8").splitlines()
        self.generations[-1]["runtime_c_sources"] = sources
        resource_root = env.get("TB_RESOURCE_ROOT")
        if resource_root:
            expected_root = Path(resource_root).resolve()
            expected_sources = [
                expected_root / "compiler/tb/runtime/thread_pool_runtime.c",
                expected_root / "compiler/tb/runtime/thread_pool_composite_runtime.c",
            ]
            self.require(
                [Path(source_path).resolve() for source_path in sources] == expected_sources,
                f"unexpected relocated runtime metadata: {sources!r}",
            )
            for source_path in sources:
                resolved_source = Path(source_path)
                self.require(
                    resolved_source.is_absolute()
                    and expected_root in resolved_source.resolve().parents
                    and resolved_source.is_file(),
                    f"runtime metadata did not resolve within relocated assets: {source_path!r}",
                )
        objects: list[Path] = []
        for index, c_source in enumerate(sources):
            resolved = Path(c_source)
            if not resolved.is_absolute():
                resolved = ROOT / resolved
            object_path = output.parent / f"{name}_{index}.o"
            clang_argv = ["clang", *cflags, "-c", str(resolved), "-o", str(object_path)]
            clang_result = self.run(name + f" compile runtime C {index}", clang_argv, cwd)
            self.require(clang_result.returncode == 0, f"{name} C compile failed: {clang_result.stderr}")
            objects.append(object_path)
        binary = output.parent / (name.replace(" ", "_") + "_program")
        linkflags = Path(str(output) + ".linkflags").read_text(encoding="utf-8").splitlines()
        link_argv = ["clang", str(output), *(str(obj) for obj in objects), *linkflags, "-o", str(binary)]
        link_result = self.run(name + " link", link_argv, cwd)
        self.require(link_result.returncode == 0, f"{name} link failed: {link_result.stderr}")
        for argc, expected in EXPECTED.items():
            program_argv = [str(binary), *(f"arg{index}" for index in range(argc - 1))]
            result = self.run(name + f" run argc={argc}", program_argv, cwd)
            self.require(
                result.returncode == 0 and result.stdout == expected and result.stderr == "",
                f"{name} argc={argc} mismatch: status={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}",
            )

    @staticmethod
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(message)

    def save(self, inputs: dict[str, object]) -> None:
        if "asset_root" in inputs:
            self.require(sha256(self.compiler) == self.compiler_hash, "compiler changed before evidence close")
            self.require(
                resource_tree_sha256(Path(str(inputs["asset_root"]))) == inputs["asset_tree_sha256"],
                "relocated assets changed before evidence close",
            )
            self.require(assets_are_read_only(Path(str(inputs["asset_root"]))), "relocated assets became writable")
            self.require(inputs.get("assets_read_only") is True, "read-only asset check was not accepted")
        for source_path, expected_hash in inputs.get("source_files", {}).items():
            self.require(sha256(Path(source_path)) == expected_hash, f"source/import changed before evidence close: {source_path}")
        if "tb_compiler_sha256" in inputs:
            self.require(
                sha256(ROOT / "bin/tb") == inputs["tb_compiler_sha256"],
                "tb.sh compiler changed before evidence close",
            )
        if "checkout_resource_tree_sha256" in inputs:
            self.require(
                resource_tree_sha256(ROOT) == inputs["checkout_resource_tree_sha256"],
                "checkout resources changed before evidence close",
            )
        record = {
            "compiler": str(self.compiler),
            "compiler_sha256": self.compiler_hash,
            "inputs": inputs,
            "generations": self.generations,
            "runs": self.runs,
        }
        (self.evidence_dir / "resource-path-verification.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", type=Path, default=ROOT / "bin/tb")
    parser.add_argument(
        "--evidence-dir", type=Path, default=ROOT / ".build/resource_path_verification"
    )
    args = parser.parse_args()
    verifier = Verifier(args.compiler, args.evidence_dir)
    scratch = Path(tempfile.mkdtemp(prefix="tb resource paths ", dir=verifier.evidence_dir))
    try:
        unrelated = scratch / "empty unrelated cwd"
        unrelated.mkdir()
        assets = scratch / "read only resource assets"
        (assets / "compiler/tb").mkdir(parents=True)
        shutil.copytree(ROOT / "compiler/tb/llvm_helpers", assets / "compiler/tb/llvm_helpers")
        runtime = assets / "compiler/tb/runtime"
        runtime.mkdir()
        for filename in (
            "thread_pool_runtime.c",
            "thread_pool_composite_runtime.c",
            "thread_pool_composite_runtime.h",
        ):
            shutil.copy2(ROOT / "compiler/tb/runtime" / filename, runtime / filename)
        for item in assets.rglob("*"):
            item.chmod(0o555 if item.is_dir() else 0o444)
        assets.chmod(0o555)
        read_only_assets = assets_are_read_only(assets)
        verifier.require(read_only_assets, "relocated assets were not read-only before testing")
        sources = scratch / "source inputs with spaces"
        sources.mkdir()
        main_source = sources / "main.tb"
        support_source = sources / "support.tb"
        main_source.write_text(MAIN_SOURCE, encoding="utf-8")
        support_source.write_text(SUPPORT_SOURCE, encoding="utf-8")
        output_dir = scratch / "outputs with spaces"
        output_dir.mkdir()
        resource_env = {"TB_RESOURCE_ROOT": str(assets)}
        trailing_resource_env = {"TB_RESOURCE_ROOT": str(assets) + "/"}

        verifier.compile_and_run(
            "normal cli relocated", main_source, output_dir / "normal cli.ll", unrelated, resource_env
        )
        verifier.compile_and_run(
            "profile cli relocated",
            main_source,
            output_dir / "profile cli.ll",
            unrelated,
            trailing_resource_env,
            profile=True,
        )

        for label, override in (("unset", None), ("empty", "")):
            fallback_output = output_dir / f"fallback {label}.ll"
            env = {"TB_RESOURCE_ROOT": override}
            fallback_source = ROOT / "tests/fixtures/162.tb"
            fallback_compiler_hash = sha256(verifier.compiler)
            fallback_source_hash = sha256(fallback_source)
            fallback_resource_hash = resource_tree_sha256(ROOT)
            fallback = verifier.run(
                f"{label} resource root fallback compile",
                [str(verifier.compiler), str(fallback_source), str(fallback_output)],
                ROOT,
                env,
            )
            verifier.require(fallback.returncode == 0, f"{label} fallback failed: {fallback.stdout}{fallback.stderr}")
            verifier.require(sha256(verifier.compiler) == fallback_compiler_hash, f"compiler changed during {label} fallback")
            verifier.require(sha256(fallback_source) == fallback_source_hash, f"fixture changed during {label} fallback")
            verifier.require(resource_tree_sha256(ROOT) == fallback_resource_hash, f"resources changed during {label} fallback")
            runtime_sources = Path(str(fallback_output) + ".csources").read_text(encoding="utf-8").splitlines()
            verifier.require(
                runtime_sources
                == [
                    "compiler/tb/runtime/thread_pool_runtime.c",
                    "compiler/tb/runtime/thread_pool_composite_runtime.c",
                ],
                f"{label} fallback metadata changed: {runtime_sources!r}",
            )
            verifier.generations.append(
                {
                    "name": f"fallback {label}",
                    "compiler_sha256": fallback_compiler_hash,
                    "source_sha256": fallback_source_hash,
                    "source_and_import_sha256": {str(fallback_source): fallback_source_hash},
                    "resource_root_expected": str(ROOT),
                    "resource_tree_sha256": fallback_resource_hash,
                    "raw_llvm": str(fallback_output),
                    "raw_llvm_sha256": sha256(fallback_output),
                    "argv": fallback.args,
                    "cwd": str(ROOT),
                    "env_overrides": env,
                    "runtime_sources": runtime_sources,
                }
            )

        missing_root = scratch / "missing resource root"
        missing = verifier.run(
            "missing resource root diagnostic",
            [str(verifier.compiler), str(ROOT / "tests/fixtures/1.tb"), str(output_dir / "missing.ll")],
            unrelated,
            {"TB_RESOURCE_ROOT": str(missing_root)},
        )
        expected_missing = str(missing_root / "compiler/tb/llvm_helpers/string_base.ll")
        verifier.require(
            missing.returncode != 0 and expected_missing in missing.stdout + missing.stderr,
            f"missing-root diagnostic absent: {missing.stdout!r} {missing.stderr!r}",
        )

        absolute_tb_output = sources / "main"
        explicit_asset_hash = resource_tree_sha256(assets)
        explicit_source_hashes = {str(path): sha256(path) for path in (main_source, support_source)}
        tb_compiler = ROOT / "bin/tb"
        explicit_tb_compiler_hash = sha256(tb_compiler)
        tb_process = verifier.run(
            "tb.sh explicit relocated root and absolute source",
            [str(ROOT / "tb.sh"), str(main_source), "-O0"],
            unrelated,
            resource_env,
        )
        verifier.require(
            tb_process.returncode == 0,
            f"tb.sh absolute source failed: {tb_process.stdout}{tb_process.stderr}",
        )
        tb_llvm = ROOT / ".build/main.ll"
        tb_csources = Path(str(tb_llvm) + ".csources").read_text(encoding="utf-8").splitlines()
        expected_explicit_sources = [
            str(assets / "compiler/tb/runtime/thread_pool_runtime.c"),
            str(assets / "compiler/tb/runtime/thread_pool_composite_runtime.c"),
        ]
        verifier.require(
            [Path(path).resolve() for path in tb_csources]
            == [Path(path).resolve() for path in expected_explicit_sources],
            f"tb.sh relocated metadata mismatch: {tb_csources!r}",
        )
        verifier.require(sha256(tb_compiler) == explicit_tb_compiler_hash, "tb.sh compiler changed during build")
        verifier.require(resource_tree_sha256(assets) == explicit_asset_hash, "assets changed during tb.sh")
        verifier.require(
            explicit_source_hashes == {str(path): sha256(path) for path in (main_source, support_source)},
            "source/import inputs changed during tb.sh",
        )
        verifier.generations.append(
            {
                "name": "tb.sh absolute source",
                "compiler": str(tb_compiler),
                "compiler_sha256": explicit_tb_compiler_hash,
                "source_sha256": sha256(main_source),
                "source_and_import_sha256": explicit_source_hashes,
                "resource_asset_root": str(assets),
                "resource_asset_tree_sha256": explicit_asset_hash,
                "support_source_sha256": sha256(support_source),
                "raw_llvm": str(tb_llvm),
                "raw_llvm_sha256": sha256(tb_llvm),
                "runtime_c_sources": tb_csources,
                "binary": str(absolute_tb_output),
                "binary_sha256": sha256(absolute_tb_output),
                "env_overrides": {"TB_RESOURCE_ROOT": str(assets)},
            }
        )
        binary = absolute_tb_output
        for argc, expected in EXPECTED.items():
            run = verifier.run(
                f"tb.sh linked program argc={argc}",
                [str(binary), *(f"arg{index}" for index in range(argc - 1))],
                unrelated,
            )
            verifier.require(
                run.returncode == 0 and run.stdout == expected and run.stderr == "",
                f"tb.sh program argc={argc} mismatch: {run.stdout!r} {run.stderr!r}",
            )

        default_resource_hash = resource_tree_sha256(ROOT)
        default_source_hashes = {str(path): sha256(path) for path in (main_source, support_source)}
        default_tb_compiler_hash = sha256(tb_compiler)
        default_tb = verifier.run(
            "tb.sh default resource root absolute source",
            [str(ROOT / "tb.sh"), str(main_source), "-O0"],
            unrelated,
            {"TB_RESOURCE_ROOT": None},
        )
        verifier.require(default_tb.returncode == 0, f"tb.sh default root failed: {default_tb.stdout}{default_tb.stderr}")
        verifier.require(sha256(tb_compiler) == default_tb_compiler_hash, "tb.sh compiler changed during default build")
        verifier.require(resource_tree_sha256(ROOT) == default_resource_hash, "checkout resources changed during default tb.sh")
        verifier.require(
            default_source_hashes == {str(path): sha256(path) for path in (main_source, support_source)},
            "source/import inputs changed during default tb.sh",
        )
        default_sources = Path(str(tb_llvm) + ".csources").read_text(encoding="utf-8").splitlines()
        expected_default_sources = [
            str(ROOT / "compiler/tb/runtime/thread_pool_runtime.c"),
            str(ROOT / "compiler/tb/runtime/thread_pool_composite_runtime.c"),
        ]
        verifier.require(default_sources == expected_default_sources, f"tb.sh default metadata mismatch: {default_sources!r}")
        verifier.generations.append(
            {
                "name": "tb.sh default root absolute source",
                "compiler": str(tb_compiler),
                "compiler_sha256": default_tb_compiler_hash,
                "source_and_import_sha256": default_source_hashes,
                "raw_llvm": str(tb_llvm),
                "raw_llvm_sha256": sha256(tb_llvm),
                "runtime_c_sources": default_sources,
                "resource_root_expected": str(ROOT),
                "resource_tree_sha256": default_resource_hash,
                "binary": str(absolute_tb_output),
                "binary_sha256": sha256(absolute_tb_output),
            }
        )
        for argc, expected in EXPECTED.items():
            run = verifier.run(
                f"tb.sh default program argc={argc}",
                [str(binary), *(f"arg{index}" for index in range(argc - 1))],
                unrelated,
            )
            verifier.require(
                run.returncode == 0 and run.stdout == expected and run.stderr == "",
                f"tb.sh default program argc={argc} mismatch: {run.stdout!r} {run.stderr!r}",
            )

        verifier.save(
            {
                "asset_root": str(assets),
                "asset_tree_sha256": resource_tree_sha256(assets),
                "checkout_resource_tree_sha256": default_resource_hash,
                "tb_compiler_sha256": default_tb_compiler_hash,
                "assets_read_only": read_only_assets and assets_are_read_only(assets),
                "source_files": {
                    str(main_source): sha256(main_source),
                    str(support_source): sha256(support_source),
                    str(ROOT / "tests/fixtures/162.tb"): sha256(ROOT / "tests/fixtures/162.tb"),
                },
                "expected_output_by_args_length": EXPECTED,
                "tb_sh_expected_binary": str(binary),
            }
        )
        print(f"resource path process verification passed; evidence: {verifier.evidence_dir / 'resource-path-verification.json'}")
        return 0
    except Exception:
        verifier.save({"scratch": str(scratch), "failed": True})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
