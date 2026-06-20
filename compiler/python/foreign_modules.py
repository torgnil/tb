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

from collections.abc import Callable
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ForeignFunction:
    member_name: str
    symbol_name: str
    argument_types: tuple[str, ...]
    return_type: str
    llvm_declaration: str


@dataclass(frozen=True, slots=True)
class ForeignConstant:
    member_name: str
    symbol_name: str
    type_name: str
    value: str


@dataclass(frozen=True, slots=True)
class ForeignModule:
    name: str
    functions: tuple[ForeignFunction, ...]
    constants: tuple[ForeignConstant, ...] = ()
    link_flags: tuple[str, ...] | Callable[[], tuple[str, ...]] = ()
    cflags: tuple[str, ...] | Callable[[], tuple[str, ...]] = ()
    c_sources: tuple[str, ...] | Callable[[], tuple[str, ...]] = ()

    def constant_declarations(self) -> str:
        lines = [f"const {constant.type_name} {constant.symbol_name} = {constant.value}" for constant in self.constants]
        return "\n".join(lines)

    def resolved_link_flags(self) -> tuple[str, ...]:
        return self._resolve_metadata(self.link_flags)

    def resolved_cflags(self) -> tuple[str, ...]:
        return self._resolve_metadata(self.cflags)

    def resolved_c_sources(self) -> tuple[str, ...]:
        return self._resolve_metadata(self.c_sources)

    @staticmethod
    def _resolve_metadata(value: tuple[str, ...] | Callable[[], tuple[str, ...]]) -> tuple[str, ...]:
        if callable(value):
            return value()
        return value


def _load_foreign_module_definitions() -> dict[str, ForeignModule]:
    repo_root = Path(__file__).resolve().parents[1]
    modules: dict[str, ForeignModule] = {}
    for manifest_path in sorted(repo_root.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        module_name = manifest["name"]
        module_file = manifest["module"]
        export_name = manifest.get("export", "FOREIGN_MODULE")
        module_path = manifest_path.parent / module_file
        spec = importlib.util.spec_from_file_location(f"tb_foreign_module_{module_name}", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load foreign module definition from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        foreign_module = getattr(module, export_name)
        if not isinstance(foreign_module, ForeignModule):
            raise TypeError(f"Expected {export_name} in {module_path} to be a ForeignModule")
        if foreign_module.name != module_name:
            raise TypeError(f"Manifest name {module_name!r} does not match ForeignModule name {foreign_module.name!r}")
        modules[module_name] = foreign_module
    return modules


FOREIGN_MODULES = _load_foreign_module_definitions()


def is_foreign_module(name: str) -> bool:
    return name in FOREIGN_MODULES


def get_foreign_module(name: str) -> ForeignModule:
    return FOREIGN_MODULES[name]


def rewrite_foreign_module_uses(source: str, active_modules: list[str]) -> str:
    rewritten = source
    for module_name in active_modules:
        rewritten = _rewrite_module_uses(rewritten, FOREIGN_MODULES[module_name])
    return rewritten


def injected_foreign_module_declarations(active_modules: list[str]) -> str:
    declarations: list[str] = []
    for module_name in active_modules:
        rendered = FOREIGN_MODULES[module_name].constant_declarations()
        if rendered:
            declarations.append(rendered)
    return "\n".join(declarations)


def foreign_module_functions(active_modules: list[str]) -> list[ForeignFunction]:
    functions: list[ForeignFunction] = []
    for module_name in active_modules:
        functions.extend(FOREIGN_MODULES[module_name].functions)
    return functions


def foreign_module_link_flags(active_modules: list[str]) -> list[str]:
    flags: list[str] = []
    for module_name in active_modules:
        flags.extend(FOREIGN_MODULES[module_name].resolved_link_flags())
    return flags


def foreign_module_cflags(active_modules: list[str]) -> list[str]:
    flags: list[str] = []
    for module_name in active_modules:
        flags.extend(FOREIGN_MODULES[module_name].resolved_cflags())
    return flags


def foreign_module_c_sources(active_modules: list[str]) -> list[str]:
    sources: list[str] = []
    for module_name in active_modules:
        sources.extend(FOREIGN_MODULES[module_name].resolved_c_sources())
    return sources


def _rewrite_module_uses(source: str, module: ForeignModule) -> str:
    mappings = {function.member_name: function.symbol_name for function in module.functions}
    mappings.update({constant.member_name: constant.symbol_name for constant in module.constants})
    output: list[str] = []
    index = 0
    line_comment = False
    block_comment = False
    in_string = False
    while index < len(source):
        current = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if in_string:
            output.append(current)
            if current == "'":
                in_string = False
            index += 1
            continue
        if line_comment:
            output.append(current)
            if current == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            output.append(current)
            if current == "*" and next_char == "/":
                output.append(next_char)
                index += 2
                block_comment = False
            else:
                index += 1
            continue
        if current == "'":
            output.append(current)
            in_string = True
            index += 1
            continue
        if current == "#":
            output.append(current)
            line_comment = True
            index += 1
            continue
        if current == "/" and next_char == "*":
            output.append(current)
            output.append(next_char)
            block_comment = True
            index += 2
            continue
        if source.startswith(module.name, index):
            before = source[index - 1] if index > 0 else ""
            after_index = index + len(module.name)
            after = source[after_index] if after_index < len(source) else ""
            if (not before or not (before.isalnum() or before == "_")) and after == ".":
                member_start = after_index + 1
                member_end = member_start
                while member_end < len(source) and (source[member_end].isalnum() or source[member_end] == "_"):
                    member_end += 1
                member_name = source[member_start:member_end]
                replacement = mappings.get(member_name)
                if replacement is not None:
                    output.append(replacement)
                    index = member_end
                    continue
        output.append(current)
        index += 1
    return "".join(output)
