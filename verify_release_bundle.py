#!/usr/bin/env python3
"""Build and verify a release bundle from an exact committed or staged tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BUILD_TIMEOUT = 600
PROGRAM_TIMEOUT = 60
EXPECTED_FIXTURES = (1, 160, 161, 162)
GATE_NAMES = (
    "revision", "archive-inputs", "toolchain", "fresh-build", "native-fixtures",
    "python-fixtures", "const-bindings", "source-unchanged", "bundle-files",
    "bundle-allowlist", "bundle-content", "bundle-checksum", "bundle-extraction",
    "bundle-readonly", "bundle-smoke", "import-smoke", "error-control",
    "workspace-unchanged",
)
FORBIDDEN_ARCHIVE_PATHS = (
    "bin/tb",
    "VERSION",
    "scripts/",
    "README.release.md",
    ".agent/",
    ".codex/",
)
REQUIRED_INPUTS = (
    "CHANGELOG.md",
    "README.md",
    "build_tb.sh",
    "bundle_release.sh",
    "compiler/python/tb.py",
    "compiler/tb/tb.tb",
    "release/resources.txt",
    "release/README.md",
    "release/tb",
    "release/tb-build",
    "docs/tb.md",
    "tests/fixtures/162.tb",
    "verify_fixtures_tb.py",
    "verify_const_bindings_tb.py",
    "verify_release_bundle.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_fingerprints(root: Path, paths: list[str] | None = None) -> dict[str, dict[str, Any]]:
    if paths is None:
        selected = sorted(path for path in root.rglob("*") if path.is_file())
        names = [path.relative_to(root).as_posix() for path in selected]
    else:
        names = sorted(paths)
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        path = root / name
        if not path.is_file():
            result[name] = {"missing": True}
            continue
        info = path.stat()
        result[name] = {
            "sha256": sha256(path),
            "mode": stat.S_IMODE(info.st_mode),
            "size": info.st_size,
        }
    return result


def filesystem_fingerprints(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in [root, *sorted(root.rglob("*"))]:
        relative = "." if item == root else item.relative_to(root).as_posix()
        info = item.lstat()
        entry: dict[str, Any] = {
            "mode": stat.S_IMODE(info.st_mode),
            "kind": "directory" if item.is_dir() else "file",
        }
        if item.is_file():
            entry["sha256"] = sha256(item)
            entry["size"] = info.st_size
        result[relative] = entry
    return result


class Verification:
    def __init__(self, evidence_dir: Path, revision: str, version: str):
        evidence_dir = evidence_dir.expanduser().resolve()
        evidence_dir.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="run-", dir=evidence_dir))
        self.revision = revision
        self.version = version
        self.started = time.time()
        self.processes: list[dict[str, Any]] = []
        self.gates: dict[str, dict[str, Any]] = {}
        self.tree_hash: str | None = None
        self.commit_hash: str | None = None
        self.source_root: Path | None = None
        self.source_paths: list[str] = []
        self.archive_path: Path | None = None
        self.workspace_before: dict[str, dict[str, Any]] = {}
        self.manifest: dict[str, Any] = {
            "schema_version": 1,
            "status": "incomplete",
            "revision_requested": revision,
            "version_requested": version,
            "scope": "tracked-source build and standalone bundle verification",
            "runtime_readiness_established": False,
            "evidence_dir": str(self.root),
            "started_unix": self.started,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "python": sys.version,
            },
            "gates": self.gates,
            "processes": self.processes,
            "failures": [],
            "incomplete_gates": [],
        }
        self.gates.update({name: {"status": "pending"} for name in GATE_NAMES})
        self.save()

    def save(self) -> None:
        self.manifest["updated_unix"] = time.time()
        (self.root / "manifest.json").write_text(
            json.dumps(self.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def gate(self, name: str, status: str, **details: Any) -> None:
        self.gates[name] = {"status": status, **details}
        self.save()

    def require(self, condition: bool, message: str, gate: str) -> None:
        if not condition:
            self.gate(gate, "failed", reason=message)
            raise RuntimeError(message)

    def run(
        self,
        name: str,
        argv: list[str],
        cwd: Path,
        *,
        env_overrides: dict[str, str | None] | None = None,
        timeout: int = PROGRAM_TIMEOUT,
        expected_status: int | None = 0,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for key, value in (env_overrides or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        env_bytes = "\0".join(f"{key}={value}" for key, value in sorted(env.items())).encode()
        record: dict[str, Any] = {
            "name": name,
            "argv": argv,
            "cwd": str(cwd.resolve()),
            "timeout_seconds": timeout,
            "expected_status": "any" if expected_status is None else expected_status,
            "env_overrides": env_overrides or {},
            "environment": {
                key: env[key]
                for key in sorted({"PATH", "TB_RESOURCE_ROOT", "TMPDIR", "PYTHONPATH", "CC", "CFLAGS", *(env_overrides or {}).keys()})
                if key in env
            },
            "environment_sha256": hashlib.sha256(env_bytes).hexdigest(),
        }
        started = time.time()
        try:
            process = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout,
            )
            record.update(
                {
                    "exit_status": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                }
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or ""
            stderr = error.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            process = subprocess.CompletedProcess(argv, 124, stdout, stderr)
            record.update(
                {
                    "exit_status": 124,
                    "timed_out": True,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
        except OSError as error:
            process = subprocess.CompletedProcess(argv, 127, "", str(error))
            record.update({"exit_status": 127, "spawn_error": str(error), "stdout": "", "stderr": str(error)})
        record["elapsed_seconds"] = time.time() - started
        log_base = self.root / "logs" / f"{len(self.processes):03d}-{name.replace('/', '_').replace(' ', '_')}"
        log_base.parent.mkdir(parents=True, exist_ok=True)
        (log_base.with_suffix(".stdout")).write_text(record["stdout"], encoding="utf-8")
        (log_base.with_suffix(".stderr")).write_text(record["stderr"], encoding="utf-8")
        record["stdout_log"] = str(log_base.with_suffix(".stdout"))
        record["stderr_log"] = str(log_base.with_suffix(".stderr"))
        self.processes.append(record)
        self.save()
        if expected_status is not None and process.returncode != expected_status:
            raise RuntimeError(
                f"{name} exited {process.returncode}, expected {expected_status}; "
                f"stderr: {process.stderr[-2000:]}"
            )
        return process

    def git_text(self, name: str, args: list[str], expected_status: int = 0) -> str:
        process = self.run(name, ["git", *args], ROOT, timeout=PROGRAM_TIMEOUT, expected_status=expected_status)
        return process.stdout.strip()

    def resolve_revision(self) -> None:
        tree_spec = f"{self.revision}^{{tree}}"
        try:
            process = self.run(
                "resolve-revision-tree",
                ["git", "rev-parse", "--verify", "--end-of-options", tree_spec],
                ROOT,
                expected_status=0,
            )
        except RuntimeError as error:
            self.gate("revision", "failed", requested=self.revision, reason=str(error))
            raise
        self.tree_hash = process.stdout.strip().splitlines()[-1]
        commit_spec = f"{self.revision}^{{commit}}"
        commit = self.run(
            "resolve-revision-commit",
            ["git", "rev-parse", "-q", "--verify", "--end-of-options", commit_spec],
            ROOT,
            expected_status=None,
        )
        self.commit_hash = commit.stdout.strip().splitlines()[-1] if commit.returncode == 0 else None
        self.manifest.update({"resolved_tree": self.tree_hash, "resolved_commit": self.commit_hash})
        self.gate("revision", "passed", tree_hash=self.tree_hash, commit_hash=self.commit_hash)

    def archive_source(self) -> None:
        assert self.tree_hash
        archive = self.root / "source.tar"
        self.archive_path = archive
        self.run(
            "git-archive-source",
            ["git", "archive", "--format=tar", f"--output={archive}", self.tree_hash],
            ROOT,
            timeout=PROGRAM_TIMEOUT,
        )
        self.manifest["source_archive"] = {"path": str(archive), "sha256": sha256(archive)}
        self.source_root = self.root / "fresh source tree with spaces"
        self.source_root.mkdir()
        with tarfile.open(archive, "r:") as source_tar:
            members = source_tar.getmembers()
            for member in members:
                target = (self.source_root / member.name).resolve()
                self.require(
                    target == self.source_root.resolve() or self.source_root.resolve() in target.parents,
                    f"archive entry escapes extraction root: {member.name}",
                    "archive-inputs",
                )
            if hasattr(tarfile, "data_filter"):
                source_tar.extractall(self.source_root, members=members, filter="data")
            else:
                source_tar.extractall(self.source_root, members=members)
        self.source_paths = sorted(
            item.relative_to(self.source_root).as_posix()
            for item in self.source_root.rglob("*")
            if item.is_file()
        )
        missing = [path for path in REQUIRED_INPUTS if path not in self.source_paths]
        forbidden = [path for path in self.source_paths if any(path == item.rstrip("/") or path.startswith(item) for item in FORBIDDEN_ARCHIVE_PATHS)]
        ignored_outputs = [path for path in self.source_paths if path.startswith(".build/") or "/lib/" in path]
        self.require(not missing, f"archive lacks required tracked inputs: {missing}", "archive-inputs")
        self.require(not forbidden, f"archive contains forbidden local inputs: {forbidden}", "archive-inputs")
        self.require(not ignored_outputs, f"archive contains ignored build/runtime outputs: {ignored_outputs}", "archive-inputs")
        initial = tree_fingerprints(self.source_root, self.source_paths)
        self.manifest["source_tree_before_build"] = initial
        self.manifest["source_files_before_build_sha256"] = {
            path: value["sha256"] for path, value in initial.items()
        }
        self.gate("archive-inputs", "passed", tracked_file_count=len(self.source_paths))
        self.workspace_before = self.workspace_fingerprints()
        self.manifest["workspace_public_fingerprints_before"] = self.workspace_before
        self.save()

    def workspace_fingerprints(self) -> dict[str, dict[str, Any]]:
        names = self.git_text("list-workspace-tracked-paths", ["ls-files", "-z"])
        paths = [path for path in names.split("\0") if path]
        return tree_fingerprints(ROOT, paths)

    def toolchain(self) -> None:
        results: dict[str, Any] = {}
        for name, argv in (
            ("clang", ["clang", "--version"]),
            ("python3", ["python3", "--version"]),
            ("git", ["git", "--version"]),
            ("uname", ["uname", "-a"]),
        ):
            result = self.run(f"toolchain-{name}", argv, ROOT)
            results[name] = {"argv": argv, "stdout": result.stdout, "stderr": result.stderr}
        self.manifest["toolchain"] = results
        self.save()
        self.require(
            platform.system() == "Darwin" and platform.machine() in {"arm64", "x86_64"},
            f"release packaging supports macOS arm64 or x86_64; got {platform.system()} {platform.machine()}",
            "toolchain",
        )
        self.gate("toolchain", "passed", platform=f"{platform.system()} {platform.machine()}", arm64_is_only_previously_verified=True)

    def build_and_suites(self) -> Path:
        assert self.source_root
        unrelated = self.root / "unrelated build working directory"
        unrelated.mkdir()
        source_build = self.source_root / "build_tb.sh"
        self.run(
            "fresh-source-build",
            [str(source_build)],
            unrelated,
            env_overrides={"TB_RESOURCE_ROOT": None, "PYTHONPATH": None},
            timeout=BUILD_TIMEOUT,
        )
        compiler = self.source_root / "bin/tb"
        self.require(compiler.is_file() and os.access(compiler, os.X_OK), "fresh build did not produce executable bin/tb", "fresh-build")
        self.manifest["fresh_compiler"] = {"path": str(compiler), "sha256": sha256(compiler)}
        self.gate("fresh-build", "passed", compiler_sha256=sha256(compiler))
        compiler_arg = str(compiler)
        build_root = self.root / "native fixture build outputs"
        native_count = len([path for path in (self.source_root / "tests/fixtures").glob("*.tb") if path.stem.isdigit()])
        native_result = self.run(
            "native-fixtures-all",
            ["python3", str(self.source_root / "verify_fixtures_tb.py"), "--compiler", compiler_arg,
             "--build-root", str(build_root), str(self.source_root / "tests/fixtures")],
            self.source_root,
            env_overrides={"TB_RESOURCE_ROOT": None, "PYTHONPATH": None},
            timeout=BUILD_TIMEOUT,
        )
        native_summary = f"{native_count}/{native_count} fixtures passed"
        self.require(
            native_count >= 162 and native_summary in native_result.stdout,
            f"expected all {native_count} native fixtures to pass (162 minimum): {native_result.stdout[-500:]}",
            "native-fixtures",
        )
        self.gate("native-fixtures", "passed", fixture_count=native_count)
        python_result = self.run(
            "python-fixtures-through-76",
            ["python3", "-m", "compiler.python.fixture_runner", str(self.source_root / "tests/fixtures"), "--max-phase", "76"],
            self.source_root,
            env_overrides={"TB_RESOURCE_ROOT": None, "PYTHONPATH": None},
            timeout=BUILD_TIMEOUT,
        )
        self.require(
            "76/76 fixtures passed" in python_result.stdout,
            f"expected Python suite 76/76: {python_result.stdout[-500:]}",
            "python-fixtures",
        )
        self.gate("python-fixtures", "passed", max_phase=76)
        const_result = self.run(
            "const-bindings",
            ["python3", str(self.source_root / "verify_const_bindings_tb.py"), "--compiler", compiler_arg],
            self.source_root,
            env_overrides={"TB_RESOURCE_ROOT": None, "PYTHONPATH": None},
            timeout=BUILD_TIMEOUT,
        )
        const_match = re.search(r"Verified (\d+) rejections and (\d+) accepted controls\.", const_result.stdout)
        rejection_count = int(const_match.group(1)) if const_match else 0
        control_count = int(const_match.group(2)) if const_match else 0
        self.require(
            const_match is not None and rejection_count >= 38 and control_count >= 8,
            f"unexpected const check counts: {const_result.stdout[-500:]}",
            "const-bindings",
        )
        self.gate("const-bindings", "passed", rejection_count=rejection_count, accepted_control_count=control_count)
        source_after = tree_fingerprints(self.source_root, self.source_paths)
        self.manifest["source_tree_after_suites"] = source_after
        source_unchanged = source_after == self.manifest["source_tree_before_build"]
        self.require(source_unchanged, "tracked source archive inputs changed during build or suites", "source-unchanged")
        self.gate("source-unchanged", "passed", tracked_file_count=len(self.source_paths))
        return compiler

    def bundle(self, compiler: Path) -> tuple[Path, Path]:
        assert self.source_root
        output_dir = self.root / "bundle output with spaces"
        output_dir.mkdir()
        self.run(
            "create-release-bundle",
            [str(self.source_root / "bundle_release.sh"), self.version, str(output_dir)],
            self.source_root,
            timeout=BUILD_TIMEOUT,
        )
        arch = platform.machine()
        archive = output_dir / f"tb-{self.version}-macos-{arch}.zip"
        checksum = Path(str(archive) + ".sha256")
        self.require(archive.is_file() and checksum.is_file(), "release packager omitted archive or checksum", "bundle-files")
        self.run("check-release-sha256", ["shasum", "-a", "256", "-c", checksum.name], output_dir)
        with zipfile.ZipFile(archive) as zf:
            names = sorted(name.rstrip("/") for name in zf.namelist() if not name.endswith("/"))
            root_name = f"tb-{self.version}-macos-{arch}"
            resources = (self.source_root / "release/resources.txt").read_text(encoding="utf-8").splitlines()
            self.require(len([item for item in resources if item]) == 23, "release resource list is not the reviewed 23-file manifest", "bundle-allowlist")
            expected = {
                f"{root_name}/README.md",
                f"{root_name}/CHANGELOG.md",
                f"{root_name}/LICENSE",
                f"{root_name}/VERSION",
                f"{root_name}/docs/tb.md",
                f"{root_name}/compiler/tb/resources.txt",
                f"{root_name}/libexec/tb",
                f"{root_name}/tb",
                f"{root_name}/tb-build",
                *(f"{root_name}/compiler/tb/{item}" for item in resources if item),
            }
            self.require(set(names) == expected, f"bundle file allowlist mismatch: missing={sorted(expected - set(names))}, extra={sorted(set(names) - expected)}", "bundle-allowlist")
            self.require(len(names) == 32, f"expected 32 packaged files, found {len(names)}", "bundle-allowlist")
            expected_hashes = {
                f"{root_name}/README.md": self.source_root / "release/README.md",
                f"{root_name}/CHANGELOG.md": self.source_root / "CHANGELOG.md",
                f"{root_name}/LICENSE": self.source_root / "LICENSE",
                f"{root_name}/docs/tb.md": self.source_root / "docs/tb.md",
                f"{root_name}/compiler/tb/resources.txt": self.source_root / "release/resources.txt",
                f"{root_name}/tb": self.source_root / "release/tb",
                f"{root_name}/tb-build": self.source_root / "release/tb-build",
                f"{root_name}/libexec/tb": compiler,
                **{f"{root_name}/compiler/tb/{item}": self.source_root / "compiler/tb" / item for item in resources if item},
            }
            contents: dict[str, str] = {}
            for name in names:
                payload = zf.read(name)
                contents[name] = hashlib.sha256(payload).hexdigest()
                if name in expected_hashes:
                    self.require(contents[name] == sha256(expected_hashes[name]), f"packaged content differs from fresh source: {name}", "bundle-content")
            version_bytes = zf.read(f"{root_name}/VERSION")
            self.require(version_bytes == (self.version + "\n").encode(), "bundle VERSION does not match requested version", "bundle-content")
        self.manifest["bundle"] = {
            "archive": str(archive), "archive_sha256": sha256(archive),
            "checksum": str(checksum), "checksum_sha256": sha256(checksum),
            "file_allowlist": names, "file_sha256": contents,
        }
        self.gate("bundle-files", "passed", archive_sha256=sha256(archive), checksum_sha256=sha256(checksum))
        self.gate("bundle-allowlist", "passed", file_count=len(names))
        self.gate("bundle-content", "passed")
        self.gate("bundle-checksum", "passed")
        extract = self.root / "extracted release with spaces"
        extract.mkdir()
        self.run("extract-release-bundle", ["ditto", "-x", "-k", str(archive), str(extract)], self.root)
        bundle_root = extract / f"tb-{self.version}-macos-{arch}"
        self.require(bundle_root.is_dir(), "extracted archive has no expected top-level directory", "bundle-extraction")
        self.make_read_only(bundle_root)
        readonly_before = filesystem_fingerprints(bundle_root)
        self.require(all(not (item.stat().st_mode & 0o222) for item in [bundle_root, *bundle_root.rglob("*")]), "extracted bundle is not read-only", "bundle-readonly")
        self.manifest["extracted_bundle_before"] = readonly_before
        self.manifest["extracted_bundle_path"] = str(bundle_root)
        self.gate("bundle-extraction", "passed", path=str(bundle_root))
        self.gate("bundle-readonly", "passed", file_count=len(readonly_before))
        return bundle_root, archive

    @staticmethod
    def make_read_only(root: Path) -> None:
        for item in sorted(root.rglob("*"), key=lambda value: len(value.parts), reverse=True):
            mode = stat.S_IMODE(item.stat().st_mode)
            item.chmod(mode & ~0o222)
        root.chmod(stat.S_IMODE(root.stat().st_mode) & ~0o222)

    def smoke(self, bundle_root: Path) -> None:
        assert self.source_root
        unrelated_a = self.root / "unrelated caller cwd one"
        unrelated_b = self.root / "unrelated caller cwd two"
        unrelated_a.mkdir()
        unrelated_b.mkdir()
        outputs = self.root / "program outputs with spaces"
        outputs.mkdir()
        env_bad_root = self.root / "bad inherited resource root"
        env = {"TB_RESOURCE_ROOT": str(env_bad_root)}
        expected_by_fixture = {}
        for fixture in EXPECTED_FIXTURES:
            source = self.source_root / f"tests/fixtures/{fixture}.tb"
            expected = (self.source_root / f"tests/fixtures/{fixture}.out").read_text(encoding="utf-8")
            expected_by_fixture[str(fixture)] = expected
            output = outputs / f"fixture {fixture} program"
            self.run(
                f"bundle-smoke-fixture-{fixture}",
                [str(bundle_root / "tb-build"), str(source), str(output)],
                unrelated_a,
                env_overrides=env,
                timeout=PROGRAM_TIMEOUT,
            )
            result = self.run(f"bundle-smoke-fixture-{fixture}-run", [str(output)], unrelated_a, timeout=PROGRAM_TIMEOUT)
            self.require(result.stdout == expected and result.stderr == "", f"fixture {fixture} output mismatch", "bundle-smoke")
        self.manifest["fixture_smoke_expected"] = expected_by_fixture

        module_source = "import support;\n\nint work(int n):\n    return transform(n)\n\nint main(string[] args):\n    int n = args.length()\n    thread_pool pool = thread_pool(2)\n    future<int> pending = pool.submit(work, n)\n    print(transform(n + 1))\n    print(pending.await())\n    return 0\n"
        support_source = "int transform(int n):\n    return n * n + 3\n"
        generations: list[dict[str, Any]] = []
        for cwd, invocation in ((unrelated_a, "absolute"), (unrelated_b, "PATH")):
            inputs = cwd / "source inputs with spaces"
            inputs.mkdir()
            (inputs / "main.tb").write_text(module_source, encoding="utf-8")
            (inputs / "support.tb").write_text(support_source, encoding="utf-8")
            main_source = inputs / "main.tb"
            support = inputs / "support.tb"
            wrapper = bundle_root / "tb"
            if invocation == "absolute":
                compile_argv = [str(wrapper), "source inputs with spaces/main.tb", "generated program.ll"]
                compile_cwd = cwd
            else:
                compile_argv = ["tb", "main.tb", "generated program.ll"]
                compile_cwd = inputs
            compile_env = dict(env)
            if invocation == "PATH":
                compile_env["PATH"] = f"{bundle_root}{os.pathsep}{os.environ.get('PATH', '')}"
                compile_argv = ["tb", "main.tb", "generated program.ll"]
            raw_llvm = compile_cwd / "generated program.ll"
            source_import_before = {str(path): sha256(path) for path in (main_source, support)}
            resource_before = filesystem_fingerprints(bundle_root / "compiler/tb")
            compiler_before = sha256(bundle_root / "libexec/tb")
            result = self.run(f"bundle-import-{invocation}-compile", compile_argv, compile_cwd,
                              env_overrides={**compile_env, "TB_RESOURCE_ROOT": str(env_bad_root)}, timeout=PROGRAM_TIMEOUT)
            self.require(raw_llvm.is_file(), f"{invocation} launcher produced no LLVM", "import-smoke")
            source_import_after = {str(path): sha256(path) for path in (main_source, support)}
            resource_after = filesystem_fingerprints(bundle_root / "compiler/tb")
            self.require(source_import_after == source_import_before, f"source or import changed during {invocation} compile", "import-smoke")
            self.require(resource_after == resource_before, f"bundle resources changed during {invocation} compile", "bundle-readonly")
            self.require(sha256(bundle_root / "libexec/tb") == compiler_before, "bundled compiler changed during generation", "bundle-readonly")
            generations.append({
                "invocation": invocation,
                "compiler_path": str(bundle_root / "libexec/tb"), "compiler_sha256_before": compiler_before,
                "source_and_import_sha256_before": source_import_before,
                "source_and_import_sha256_after": source_import_after,
                "resource_tree_before": resource_before, "resource_tree_after": resource_after,
                "raw_llvm": str(raw_llvm), "raw_llvm_sha256": sha256(raw_llvm),
                "argv": compile_argv, "cwd": str(compile_cwd),
                "exit_status": result.returncode,
            })
            for optimization in ("-O0", "-O2"):
                binary = inputs / f"native program {optimization[1:]}"
                build_argv = [str(bundle_root / "tb-build"), "main.tb", str(binary), optimization]
                if invocation == "PATH":
                    build_argv[0] = "tb-build"
                self.run(
                    f"bundle-import-{invocation}-native-build-{optimization}", build_argv, inputs,
                    env_overrides={**env, "PATH": f"{bundle_root}{os.pathsep}{os.environ.get('PATH', '')}"},
                    timeout=PROGRAM_TIMEOUT,
                )
                for argc in (1, 2, 3):
                    args = [f"arg{i}" for i in range(argc - 1)]
                    execution = self.run(
                        f"bundle-import-{invocation}-{optimization}-run-argc-{argc}",
                        [str(binary), *args], unrelated_b if invocation == "PATH" else unrelated_a,
                    )
                    expected = f"{(argc + 1) * (argc + 1) + 3}\n{argc * argc + 3}\n"
                    self.require(execution.stdout == expected and execution.stderr == "", f"imported thread result mismatch argc={argc}: {execution.stdout!r} {execution.stderr!r}", "import-smoke")
        self.manifest["generations"] = generations
        self.gate("import-smoke", "passed", modes=["absolute launcher", "PATH launcher"], argc=[1, 2, 3], optimization=["-O0", "-O2"])

        # A compiler failure must stop tb-build before Clang can replace its output.
        error_dir = unrelated_b / "compile error control"
        error_dir.mkdir()
        broken = error_dir / "broken.tb"
        broken.write_text("int main(string[] args):\n    return missing_function()\n", encoding="utf-8")
        sentinel = error_dir / "existing output sentinel"
        sentinel.write_text("keep this output\n", encoding="utf-8")
        before = sha256(sentinel)
        failure = self.run("bundle-error-control-missing-function", [str(bundle_root / "tb-build"), str(broken), str(sentinel)],
                           unrelated_b, env_overrides=env, expected_status=None, timeout=PROGRAM_TIMEOUT)
        self.require(failure.returncode != 0, "tb-build accepted undefined missing_function", "error-control")
        diagnostic = failure.stdout + failure.stderr
        self.require("missing_function" in diagnostic, "compiler failure did not identify missing_function", "error-control")
        self.require(sha256(sentinel) == before, "tb-build replaced output after compiler failure", "error-control")
        missing_args = self.run("bundle-error-control-missing-arguments", [str(bundle_root / "tb-build")], unrelated_b,
                                env_overrides=env, expected_status=None)
        self.require(missing_args.returncode != 0, "tb-build accepted missing arguments", "error-control")
        malformed = error_dir / "malformed.tb"
        malformed.write_text("int main(\n", encoding="utf-8")
        malformed_result = self.run("bundle-error-control-malformed-source", [str(bundle_root / "tb"), str(malformed), str(error_dir / "malformed.ll")],
                                    unrelated_b, env_overrides=env, expected_status=None)
        self.require(malformed_result.returncode != 0, "tb accepted malformed source", "error-control")
        self.gate("error-control", "passed", diagnostic_contains="missing_function", output_sentinel_preserved=True)

        bool_dir = unrelated_a / "valid bool import after error control"
        bool_dir.mkdir()
        (bool_dir / "main.tb").write_text(
            "import support;\n\nint main(string[] args):\n"
            "    thread_pool pool = thread_pool(2)\n"
            "    future<bool> ready = pool.submit(is_ready)\n"
            "    print(ready.await())\n"
            "    return 0\n",
            encoding="utf-8",
        )
        (bool_dir / "support.tb").write_text("bool is_ready():\n    return true\n", encoding="utf-8")
        bool_binary = bool_dir / "bool result program"
        self.run("bundle-valid-bool-import-after-error", [str(bundle_root / "tb-build"), "main.tb", str(bool_binary), "-O2"],
                 bool_dir, env_overrides=env)
        bool_result = self.run("bundle-valid-bool-import-run-after-error", [str(bool_binary)], unrelated_b)
        self.require(bool_result.stdout == "true\n" and bool_result.stderr == "", "valid bool future failed after error control", "error-control")
        self.gate("error-control", "passed", diagnostic_contains="missing_function", output_sentinel_preserved=True,
                  valid_imported_bool_future_after_failure=True)

        after = filesystem_fingerprints(bundle_root)
        before = self.manifest["extracted_bundle_before"]
        self.require(after == before, "read-only extracted bundle content or modes changed during smoke tests", "bundle-readonly")
        self.gate("bundle-readonly", "passed", verified_after_smoke=True, file_count=len(after))
        self.gate("bundle-smoke", "passed", fixtures=list(EXPECTED_FIXTURES))

    def close(self) -> None:
        if self.workspace_before:
            if self.source_root and self.source_paths:
                source_after = tree_fingerprints(self.source_root, self.source_paths)
                self.manifest["source_tree_after_all_checks"] = source_after
                same_source = source_after == self.manifest.get("source_tree_before_build")
                self.gate("source-unchanged", "passed" if same_source else "failed", unchanged=same_source)
                if not same_source:
                    self.manifest["failures"].append("tracked archived source fingerprints changed during verification")
            if self.archive_path and self.archive_path.is_file() and "source_archive" in self.manifest:
                archive_unchanged = sha256(self.archive_path) == self.manifest["source_archive"]["sha256"]
                self.manifest["source_archive_unchanged_after"] = archive_unchanged
                if not archive_unchanged:
                    self.manifest["failures"].append("source archive fingerprint changed during verification")
            bundle_record = self.manifest.get("bundle", {})
            for key, digest_key in (("archive", "archive_sha256"), ("checksum", "checksum_sha256")):
                artifact = Path(bundle_record[key]) if bundle_record.get(key) else None
                if artifact and artifact.is_file():
                    unchanged_artifact = sha256(artifact) == bundle_record.get(digest_key)
                    self.manifest[f"release_{key}_unchanged_after"] = unchanged_artifact
                    if not unchanged_artifact:
                        self.manifest["failures"].append(f"release {key} fingerprint changed during verification")
            fresh_compiler = self.manifest.get("fresh_compiler", {})
            if fresh_compiler.get("path"):
                compiler_unchanged = sha256(Path(fresh_compiler["path"])) == fresh_compiler.get("sha256")
                self.manifest["fresh_compiler_unchanged_after"] = compiler_unchanged
                if not compiler_unchanged:
                    self.manifest["failures"].append("fresh compiler fingerprint changed during verification")
            after = self.workspace_fingerprints()
            self.manifest["workspace_public_fingerprints_after"] = after
            unchanged = self.workspace_before == after
            self.gate("workspace-unchanged", "passed" if unchanged else "failed", unchanged=unchanged)
            if not unchanged:
                self.manifest["failures"].append("tracked workspace fingerprints changed during verification")
        incomplete = [name for name, value in self.gates.items() if value["status"] == "pending"]
        failed = [name for name, value in self.gates.items() if value["status"] == "failed"]
        self.manifest["incomplete_gates"] = incomplete
        self.manifest["status"] = "passed" if not failed and not incomplete and not self.manifest["failures"] else "failed" if failed or self.manifest["failures"] else "incomplete"
        self.manifest["completed_unix"] = time.time()
        self.save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default="HEAD", help="Commit or treeish to verify (default: HEAD)")
    parser.add_argument("--version", default="0.2.0", help="Bundle version to create and verify")
    parser.add_argument(
        "--evidence-dir", type=Path, default=ROOT / ".build/release_bundle_verification",
        help="Parent directory for an immutable per-run evidence directory",
    )
    args = parser.parse_args(argv)
    verification = Verification(args.evidence_dir, args.revision, args.version)
    try:
        verification.resolve_revision()
        verification.archive_source()
        verification.toolchain()
        compiler = verification.build_and_suites()
        bundle_root, _archive = verification.bundle(compiler)
        verification.smoke(bundle_root)
    except Exception as error:
        verification.manifest["failures"].append(str(error))
        pending = [name for name in (
            "archive-inputs", "toolchain", "fresh-build", "native-fixtures", "python-fixtures",
            "const-bindings", "source-unchanged", "bundle-files", "bundle-allowlist", "bundle-content",
            "bundle-checksum", "bundle-extraction", "bundle-readonly", "bundle-smoke",
            "import-smoke", "error-control", "workspace-unchanged",
        ) if name not in verification.gates]
        for name in pending:
            verification.gate(name, "pending")
        verification.close()
        print(f"Release verification failed: {error}", file=sys.stderr)
        print(f"Evidence: {verification.root / 'manifest.json'}", file=sys.stderr)
        return 1
    verification.close()
    print(f"Release verification {verification.manifest['status']}: {verification.root}")
    return 0 if verification.manifest["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
