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
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import CompilationError
from .foreign_modules import (
    foreign_module_c_sources,
    foreign_module_cflags,
    foreign_module_link_flags,
    injected_foreign_module_declarations,
    is_foreign_module,
    rewrite_foreign_module_uses,
)
from .ir import IRModule
from .ir_generator import generate_ir
from .lexer import Token, tokenize
from .llvm_emitter import emit_llvm
from .parser import parse


IMPORT_PATTERN = re.compile(r"^\s*import\s+([A-Za-z0-9_./-]+)\s*;?\s*$")


@dataclass(frozen=True, slots=True)
class LoadedSource:
    text: str
    foreign_modules: tuple[str, ...] = ()


def tokenize_source(source: str) -> list[Token]:
    return tokenize(source, emit_layout_tokens=True)


def parse_source(source: str):
    return parse(tokenize_source(source))


def build_ir(source: str, foreign_modules: list[str] | tuple[str, ...] | None = None) -> IRModule:
    active_modules = tuple(sorted(foreign_modules or ()))
    prepared_source = source
    injected = injected_foreign_module_declarations(list(active_modules))
    if injected:
        prepared_source = f"{injected}\n{source}"
    if active_modules:
        prepared_source = rewrite_foreign_module_uses(prepared_source, list(active_modules))
    module = generate_ir(parse_source(prepared_source), foreign_modules=list(active_modules))
    if module.entry_function_name is None:
        raise CompilationError("Program must declare int main(string[] args)", 1, 1)
    module.foreign_modules = list(active_modules)
    return module


def compile_source(source: str, foreign_modules: list[str] | tuple[str, ...] | None = None) -> str:
    return emit_llvm(build_ir(source, foreign_modules=foreign_modules))


def compile_file(input_path: str | Path, output_path: str | Path, import_dirs: list[str | Path] | None = None) -> None:
    loaded = load_source_bundle_with_imports(input_path, import_dirs=import_dirs)
    module = build_ir(loaded.text, foreign_modules=loaded.foreign_modules)
    llvm_output = emit_llvm(module)
    output_path = Path(output_path)
    output_path.write_text(llvm_output, encoding="utf-8")
    _write_foreign_build_metadata(output_path, list(loaded.foreign_modules))


def load_source_with_imports(input_path: str | Path, import_dirs: list[str | Path] | None = None) -> str:
    return load_source_bundle_with_imports(input_path, import_dirs=import_dirs).text


def load_source_bundle_with_imports(input_path: str | Path, import_dirs: list[str | Path] | None = None) -> LoadedSource:
    foreign_modules: set[str] = set()
    text = _load_source_recursive(Path(input_path).resolve(), _normalize_import_dirs(import_dirs), set(), foreign_modules)
    return LoadedSource(text, tuple(sorted(foreign_modules)))


def _load_source_recursive(path: Path, import_dirs: list[Path], loaded_paths: set[Path], foreign_modules: set[str]) -> str:
    if path in loaded_paths:
        return ""
    loaded_paths.add(path)

    segments: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = IMPORT_PATTERN.match(line)
        if match is None:
            segments.append(line)
            continue
        module_name = match.group(1)
        if is_foreign_module(module_name):
            foreign_modules.add(module_name)
            continue
        import_path = _resolve_import(module_name, path.parent, import_dirs)
        imported_source = _load_source_recursive(import_path, import_dirs, loaded_paths, foreign_modules)
        if imported_source and not imported_source.endswith("\n"):
            imported_source += "\n"
        segments.append(imported_source)
    return "".join(segments)


def _resolve_import(module_name: str, source_dir: Path, import_dirs: list[Path]) -> Path:
    candidate_name = module_name if module_name.endswith(".tb") else f"{module_name}.tb"
    search_dirs = [source_dir, *import_dirs, Path.cwd().resolve()]
    seen_dirs: set[Path] = set()
    for directory in search_dirs:
        resolved_dir = directory.resolve()
        if resolved_dir in seen_dirs:
            continue
        seen_dirs.add(resolved_dir)
        candidate = resolved_dir / candidate_name
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Unable to resolve import {module_name!r}")


def _normalize_import_dirs(import_dirs: list[str | Path] | None) -> list[Path]:
    if import_dirs is None:
        return []
    return [Path(directory).resolve() for directory in import_dirs]


def default_output_path(input_path: str | Path) -> Path:
    return Path.cwd() / Path(input_path).with_suffix(".ll").name


def _write_foreign_build_metadata(output_path: Path, active_modules: list[str]) -> None:
    link_flags_path = Path(f"{output_path}.linkflags")
    cflags_path = Path(f"{output_path}.cflags")
    c_sources_path = Path(f"{output_path}.csources")
    link_flags = foreign_module_link_flags(active_modules)
    cflags = foreign_module_cflags(active_modules)
    c_sources = foreign_module_c_sources(active_modules)
    if link_flags:
        link_flags_path.write_text("\n".join(link_flags) + "\n", encoding="utf-8")
    elif link_flags_path.exists():
        link_flags_path.unlink()
    if cflags:
        cflags_path.write_text("\n".join(cflags) + "\n", encoding="utf-8")
    elif cflags_path.exists():
        cflags_path.unlink()
    if c_sources:
        c_sources_path.write_text("\n".join(c_sources) + "\n", encoding="utf-8")
    elif c_sources_path.exists():
        c_sources_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile tb to LLVM IR.")
    parser.add_argument("-I", "--import-dir", action="append", default=[], help="Directory to search for imported .tb files")
    parser.add_argument("input", help="Path to the source file")
    parser.add_argument("output", nargs="?", help="Path to write the LLVM IR file")
    args = parser.parse_args(argv)

    try:
        compile_file(args.input, args.output or default_output_path(args.input), import_dirs=args.import_dir)
    except (CompilationError, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
