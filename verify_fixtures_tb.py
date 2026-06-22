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
        expected_path = input_path.with_suffix(".out")
        if not expected_path.exists():
            raise FileNotFoundError(
                f"Missing expected output file for {input_path.name}: {expected_path.name}"
            )
        fixtures.append((input_path, expected_path))
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
        workspace_path = tmp_path / "workspace"
        fixture_workspace = workspace_path / fixtures_dir.name
        shutil.copytree(fixtures_dir, fixture_workspace)
        if fixtures_dir.name != "test-files":
            compat_workspace = workspace_path / "test-files"
            shutil.copytree(fixtures_dir, compat_workspace)

        compile_result = subprocess.run(
            [str(compiler_bin), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(
                f"tb compiler failed for {input_path.name}:\n{compile_result.stdout}{compile_result.stderr}"
            )

        clang_result = subprocess.run(
            ["clang", str(output_path), "-o", str(binary_path)],
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
    if shutil.which("clang") is None:
        raise RuntimeError("clang is required to verify fixtures")
    if not compiler_bin.exists():
        raise FileNotFoundError(f"Missing tb compiler binary: {compiler_bin}")

    fixtures = discover_fixtures(fixtures_dir, max_phase=max_phase)
    if not fixtures:
        raise FileNotFoundError(f"No .tb fixtures found in {fixtures_dir}")

    build_root.mkdir(parents=True, exist_ok=True)
    return [run_fixture(compiler_bin, fixtures_dir, build_root, input_path, expected_path) for input_path, expected_path in fixtures]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile and verify tb fixtures with the self-hosted compiler."
    )
    parser.add_argument(
        "fixtures_dir",
        nargs="?",
        default="tests/fixtures",
        help="Directory containing .tb and .out fixture pairs",
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
