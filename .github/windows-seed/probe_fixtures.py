import argparse
from collections import Counter
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory

from target_ir import target_ir


def run(command, cwd):
    return subprocess.run(command, cwd=cwd, capture_output=True, timeout=30)


def normalized(data):
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def probe(source, compiler, shim, work, root):
    ir = work / "fixture.raw.ll"
    compiled = run([compiler, source.relative_to(root).as_posix(), ir.as_posix()], root)
    error = source.with_suffix(".err")
    if error.is_file():
        if (compiled.returncode == 1 and not compiled.stderr and not ir.exists()
                and normalized(compiled.stdout) == normalized(error.read_bytes())):
            return "pass", "expected rejection"
        return "rejection", repr((compiled.returncode, compiled.stdout, compiled.stderr, ir.exists()))
    if compiled.returncode != 0 or not ir.is_file():
        return "compile", repr((compiled.returncode, compiled.stdout, compiled.stderr))

    sidecars = [suffix for suffix in ("csources", "cflags", "linkflags")
                if (path := ir.with_suffix(".ll." + suffix)).is_file() and path.read_bytes().strip()]
    if sidecars:
        return "skipped", "runtime C sources or link flags: " + ", ".join(sidecars)

    windows_ir = work / "fixture.ll"
    binary = work / "fixture.exe"
    target_ir(ir, windows_ir)
    linked = run(["clang", windows_ir, shim, "-Wl,--stack,16777216", "-o", binary], root)
    if linked.returncode != 0:
        return "link", repr(linked.stderr)

    contents = source.read_text(encoding="utf-8")
    literals = re.findall(r"""'([^'\n]*)'|"([^"\n]*)["]""", contents)
    assets = {source.with_suffix(suffix).name for suffix in (".tb", ".in", ".out")}
    for single, double in literals:
        prefix, _, relative = (single or double).partition("/")
        if prefix in ("fixtures", "test-files") and relative:
            candidate = (source.parent / relative).resolve()
            if candidate.is_relative_to(source.parent) and candidate.is_file():
                assets.add(relative)

    for name in ("fixtures", "test-files"):
        (work / name).mkdir()
        for asset in assets:
            original = source.parent / asset
            if original.is_file():
                destination = work / name / asset
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)

    ran = run([binary], work)
    if ran.returncode != 0:
        return "run", repr((ran.returncode, ran.stdout, ran.stderr))
    actual = ran.stdout
    output_file = re.search(r"\bopen\('([^'\n]+)'", contents)
    if output_file:
        path = (work / output_file[1]).resolve()
        if not path.is_relative_to(work) or not path.is_file():
            return "output", "expected output file missing from workspace"
        actual = path.read_bytes()
    expected = source.with_suffix(".out").read_bytes()
    if normalized(actual) != normalized(expected):
        return "output", repr(actual)
    return "pass", "expected output"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("compiler", type=Path)
    parser.add_argument("shim", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    sources = sorted(
        (path for path in (root / "tests/fixtures").glob("*.tb") if path.stem.isdecimal()),
        key=lambda path: int(path.stem),
    )
    if not sources:
        parser.error("no numbered fixtures found")
    compiler, shim = args.compiler.resolve(), args.shim.resolve()
    if not compiler.is_file() or not shim.is_file() or not shutil.which("clang"):
        parser.error("the compiler, runtime shim and clang are required")
    totals = Counter()
    with args.report.open("w", encoding="utf-8") as report:
        for source in sources:
            if sum(source.with_suffix(suffix).is_file() for suffix in (".out", ".err")) != 1:
                result, details = "expectation", "expected exactly one .out or .err file"
            else:
                with TemporaryDirectory(prefix="fixture-", dir=args.report.resolve().parent) as temp:
                    try:
                        result, details = probe(source, compiler, shim, Path(temp), root)
                    except subprocess.TimeoutExpired as error:
                        result, details = "timeout", repr(error)
                    except (OSError, ValueError) as error:
                        result, details = "probe-error", repr(error)
            totals[result] += 1
            print(f"{source.name}\t{result}\t{details[:4000]}", file=report, flush=True)
        summary = " | ".join(f"{category}: {count}" for category, count in sorted(totals.items()))
        print(summary, file=report)
    print(summary)


if __name__ == "__main__":
    main()
