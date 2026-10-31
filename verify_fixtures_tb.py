#!/usr/bin/env python3
# Copyright 2026 Torbjörn Nilsson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, write_through=True)


@dataclass(slots=True)
class FixtureResult:
    name: str
    output: str
    expected_output: str

    @property
    def passed(self) -> bool:
        return self.output == self.expected_output


def discover_fixtures(fixtures_dir: Path, max_phase: int | None = None) -> list[tuple[Path, Path]]:
    fixtures: list[tuple[Path, Path]] = []
    for input_path in sorted(fixtures_dir.glob("*.tb"), key=lambda path: (0, int(path.stem)) if path.stem.isdigit() else (1, path.stem)):
        if not input_path.stem.isdigit():
            continue
        if max_phase is not None and int(input_path.stem) > max_phase:
            continue
        expected_paths = [input_path.with_suffix(suffix) for suffix in (".out", ".err")]
        expected_paths = [path for path in expected_paths if path.exists()]
        if not expected_paths:
            raise FileNotFoundError(
                f"Missing .out or .err expectation for {input_path.name}"
            )
        if len(expected_paths) != 1:
            raise RuntimeError(f"Ambiguous expectations for {input_path.name}: use either .out or .err")
        fixtures.append((input_path, expected_paths[0]))
    return fixtures


def latest_fixture_phase(fixtures_dir: Path) -> int | None:
    phases = [int(path.stem) for path in fixtures_dir.glob("*.tb") if path.stem.isdigit()]
    if not phases:
        return None
    return max(phases)


def find_runtime_output_target(source_text: str) -> Path | None:
    matches = re.findall(r"open\('([^']+)'\)", source_text)
    if not matches:
        return None
    return Path(matches[0])


def prepare_fixture_workspace(
    workspace_path: Path,
    fixtures_dir: Path,
    input_path: Path,
    source_text: str,
) -> None:
    fixture_names = [fixtures_dir.name]
    if fixtures_dir.name != "test-files":
        fixture_names.append("test-files")

    fixture_assets: set[Path] = set()
    for suffix in (".in", ".out", ".err", ".tb"):
        companion = input_path.with_suffix(suffix)
        if companion.is_file():
            fixture_assets.add(Path(companion.name))

    for literal_path in re.findall(r"['\"]([^'\"]+)['\"]", source_text):
        path_parts = Path(literal_path).parts
        if len(path_parts) < 2 or path_parts[0] not in fixture_names:
            continue
        relative_path = Path(*path_parts[1:])
        if ".." in relative_path.parts:
            continue
        if (fixtures_dir / relative_path).is_file():
            fixture_assets.add(relative_path)

    for fixture_name in fixture_names:
        fixture_workspace = workspace_path / fixture_name
        fixture_workspace.mkdir(parents=True, exist_ok=True)
        for relative_path in sorted(fixture_assets):
            source_path = fixtures_dir / relative_path
            if not source_path.is_file():
                continue
            destination = fixture_workspace / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)


def run_fixture(
    compiler_bin: Path,
    fixtures_dir: Path,
    build_root: Path,
    input_path: Path,
    expected_path: Path,
) -> FixtureResult:
    source_text = input_path.read_text(encoding="utf-8")
    expected_output = expected_path.read_text(encoding="utf-8")
    runtime_output_target = find_runtime_output_target(source_text)

    with tempfile.TemporaryDirectory(prefix=f"fixture_{input_path.stem}_", dir=build_root) as tmp_dir:
        tmp_path = Path(tmp_dir)
        output_path = tmp_path / f"{input_path.stem}.ll"
        binary_path = tmp_path / input_path.stem
        compile_result = subprocess.run(
            [str(compiler_bin), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if expected_path.suffix == ".err":
            if not expected_output.strip():
                raise RuntimeError(f"Empty diagnostic expectation for {input_path.name}")
            if compile_result.returncode != 1 or compile_result.stderr or output_path.exists():
                raise RuntimeError(
                    f"Expected compiler rejection for {input_path.name}: status 1, empty stderr, no LLVM; "
                    f"got status {compile_result.returncode}, LLVM present: {output_path.exists()}\n"
                    f"{compile_result.stdout}{compile_result.stderr}"
                )
            return FixtureResult(
                name=input_path.stem,
                output=compile_result.stdout,
                expected_output=expected_output,
            )
        if compile_result.returncode != 0:
            raise RuntimeError(
                f"tb compiler failed for {input_path.name}:\n{compile_result.stdout}{compile_result.stderr}"
            )

        workspace_path = tmp_path / "workspace"
        prepare_fixture_workspace(workspace_path, fixtures_dir, input_path, source_text)

        linkflags_path = Path(f"{output_path}.linkflags")
        cflags_path = Path(f"{output_path}.cflags")
        csources_path = Path(f"{output_path}.csources")
        linkflags = linkflags_path.read_text(encoding="utf-8").split() if linkflags_path.exists() else []
        cflags = cflags_path.read_text(encoding="utf-8").split() if cflags_path.exists() else []
        objects: list[str] = []
        if csources_path.exists():
            platform_os = subprocess.check_output(["uname", "-s"], text=True).strip().lower()
            platform_arch = subprocess.check_output(["uname", "-m"], text=True).strip()
            if platform_os == "darwin":
                platform_os = "macos"
            platform_suffix = f"{platform_os}_{platform_arch}"
            for c_source in [line.strip() for line in csources_path.read_text(encoding="utf-8").splitlines() if line.strip()]:
                resolved_c_source = Path(c_source)
                if not resolved_c_source.is_absolute():
                    resolved_c_source = Path.cwd() / resolved_c_source
                object_dir = resolved_c_source.parent / "lib"
                object_dir.mkdir(parents=True, exist_ok=True)
                object_output = object_dir / f"{resolved_c_source.stem}_{platform_suffix}.o"
                if not object_output.exists() or resolved_c_source.stat().st_mtime > object_output.stat().st_mtime:
                    c_compile_result = subprocess.run(
                        ["clang", "-c", *cflags, str(resolved_c_source), "-o", str(object_output)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if c_compile_result.returncode != 0:
                        raise RuntimeError(f"clang C runtime compile failed for {input_path.name}:\n{c_compile_result.stderr}")
                objects.append(str(object_output))

        clang_result = subprocess.run(
            ["clang", str(output_path), *objects, "-o", str(binary_path), *linkflags],
            capture_output=True,
            text=True,
            check=False,
        )
        if clang_result.returncode != 0:
            raise RuntimeError(f"clang failed for {input_path.name}:\n{clang_result.stderr}")

        run_result = subprocess.run(
            [str(binary_path)],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if run_result.returncode != 0:
            raise RuntimeError(f"binary failed for {input_path.name}:\n{run_result.stderr}")

        actual_output = run_result.stdout
        if runtime_output_target is not None:
            actual_output = (workspace_path / runtime_output_target).read_text(encoding="utf-8")

        return FixtureResult(
            name=input_path.stem,
            output=actual_output,
            expected_output=expected_output,
        )


def verify_fixtures(
    compiler_bin: Path,
    fixtures_dir: Path,
    build_root: Path,
    max_phase: int | None = None,
) -> list[FixtureResult]:
    if not compiler_bin.exists():
        raise FileNotFoundError(f"Missing tb compiler binary: {compiler_bin}")

    fixtures = discover_fixtures(fixtures_dir, max_phase=max_phase)
    if not fixtures:
        raise FileNotFoundError(f"No .tb fixtures found in {fixtures_dir}")
    if any(expected.suffix == ".out" for _, expected in fixtures) and shutil.which("clang") is None:
        raise RuntimeError("clang is required to verify runtime fixtures")

    build_root.mkdir(parents=True, exist_ok=True)
    return [run_fixture(compiler_bin, fixtures_dir, build_root, input_path, expected_path) for input_path, expected_path in fixtures]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify tb runtime outputs (.out) and compiler rejections (.err)."
    )
    parser.add_argument(
        "fixtures_dir",
        nargs="?",
        default="tests/fixtures",
        help="Directory containing numbered .tb files paired with either .out or .err",
    )
    parser.add_argument(
        "--compiler",
        default="bin/tb",
        help="Path to the self-hosted tb compiler binary",
    )
    parser.add_argument(
        "--build-root",
        default=".build/fixtures_tb",
        help="Directory for temporary LLVM, binaries, and workspace copies",
    )
    parser.add_argument(
        "--max-phase",
        type=int,
        default=None,
        help="Highest numbered fixture to verify (default: latest discovered fixture)",
    )
    args = parser.parse_args(argv)

    try:
        results = verify_fixtures(
            compiler_bin=Path(args.compiler),
            fixtures_dir=Path(args.fixtures_dir),
            build_root=Path(args.build_root),
            max_phase=args.max_phase,
        )
    except (FileNotFoundError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1

    failures = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}")
        if not result.passed:
            print("expected:")
            print(result.expected_output, end="" if result.expected_output.endswith("\n") else "\n")
            print("actual:")
            print(result.output, end="" if result.output.endswith("\n") else "\n")

    print(f"{len(results) - len(failures)}/{len(results)} fixtures passed")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
