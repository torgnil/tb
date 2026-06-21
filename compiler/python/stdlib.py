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

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuiltinOverload:
    argument_types: tuple[str, ...]
    return_type: str
    lowering: str


@dataclass(frozen=True, slots=True)
class BuiltinFunction:
    name: str
    overloads: tuple[BuiltinOverload, ...]


STANDARD_LIBRARY: dict[str, BuiltinFunction] = {
    "print": BuiltinFunction(
        "print",
        (
            BuiltinOverload(("string",), "void", "print_string"),
            BuiltinOverload(("num",), "void", "print_number"),
            BuiltinOverload(("int",), "void", "print_int"),
            BuiltinOverload(("bool",), "void", "print_bool"),
            BuiltinOverload(("int[]",), "void", "print_int_array"),
            BuiltinOverload(("string[]",), "void", "print_string_array"),
            BuiltinOverload(("bool[]",), "void", "print_bool_array"),
            BuiltinOverload(("set<int>",), "void", "print_int_set"),
        ),
    ),
    "read_lines": BuiltinFunction(
        "read_lines",
        (
            BuiltinOverload(("string",), "string[]", "read_lines"),
        ),
    ),
    "read_file": BuiltinFunction(
        "read_file",
        (
            BuiltinOverload(("string",), "string", "read_file"),
        ),
    ),
    "time_ms": BuiltinFunction(
        "time_ms",
        (
            BuiltinOverload((), "int", "time_ms"),
        ),
    ),
    "dump_runtime_activity": BuiltinFunction(
        "dump_runtime_activity",
        (
            BuiltinOverload((), "void", "dump_runtime_activity"),
        ),
    ),
    "reset_runtime_activity": BuiltinFunction(
        "reset_runtime_activity",
        (
            BuiltinOverload((), "void", "reset_runtime_activity"),
        ),
    ),
    "to_int": BuiltinFunction(
        "to_int",
        (
            BuiltinOverload(("string",), "int", "to_int"),
        ),
    ),
    "to_num": BuiltinFunction(
        "to_num",
        (
            BuiltinOverload(("string",), "num", "to_num"),
        ),
    ),
    "to_string": BuiltinFunction(
        "to_string",
        (
            BuiltinOverload(("string",), "string", "to_string_string"),
            BuiltinOverload(("int",), "string", "to_string_int"),
            BuiltinOverload(("num",), "string", "to_string_num"),
            BuiltinOverload(("bool",), "string", "to_string_bool"),
            BuiltinOverload(("int[]",), "string", "to_string_int_array"),
            BuiltinOverload(("string[]",), "string", "to_string_string_array"),
            BuiltinOverload(("bool[]",), "string", "to_string_bool_array"),
            BuiltinOverload(("set<int>",), "string", "to_string_int_set"),
        ),
    ),
    "abs": BuiltinFunction(
        "abs",
        (
            BuiltinOverload(("int",), "int", "abs_int"),
            BuiltinOverload(("num",), "num", "abs_num"),
        ),
    ),
    "popcount": BuiltinFunction(
        "popcount",
        (
            BuiltinOverload(("int",), "int", "popcount_int"),
        ),
    ),
    "min": BuiltinFunction(
        "min",
        (
            BuiltinOverload(("int", "int"), "int", "min_int"),
            BuiltinOverload(("num", "num"), "num", "min_num"),
        ),
    ),
    "max": BuiltinFunction(
        "max",
        (
            BuiltinOverload(("int", "int"), "int", "max_int"),
            BuiltinOverload(("num", "num"), "num", "max_num"),
        ),
    ),
    "sqrt": BuiltinFunction(
        "sqrt",
        (
            BuiltinOverload(("int",), "num", "sqrt_int"),
            BuiltinOverload(("num",), "num", "sqrt_num"),
        ),
    ),
    "to_set": BuiltinFunction(
        "to_set",
        (
            BuiltinOverload(("int[]",), "set<int>", "to_set_int_array"),
        ),
    ),
    "hash": BuiltinFunction(
        "hash",
        (
            BuiltinOverload(("int",), "int", "hash_int"),
            BuiltinOverload(("num",), "int", "hash_num"),
            BuiltinOverload(("string",), "int", "hash_string"),
        ),
    ),
    "range": BuiltinFunction(
        "range",
        (
            BuiltinOverload(("int",), "int[]", "range_int"),
            BuiltinOverload(("int", "int"), "int[]", "range_int_int"),
        ),
    ),
    "trim": BuiltinFunction(
        "trim",
        (
            BuiltinOverload(("string",), "string", "trim_string"),
        ),
    ),
    "substring": BuiltinFunction(
        "substring",
        (
            BuiltinOverload(("string", "int"), "string", "substring_from"),
            BuiltinOverload(("string", "int", "int"), "string", "substring_range"),
        ),
    ),
    "slice": BuiltinFunction(
        "slice",
        (
            BuiltinOverload(("string", "int", "int"), "string", "slice_string"),
            BuiltinOverload(("$item[]", "int", "int"), "$item[]", "slice_array"),
        ),
    ),
    "char_at": BuiltinFunction(
        "char_at",
        (
            BuiltinOverload(("string", "int"), "string", "char_at"),
        ),
    ),
    "index_of": BuiltinFunction(
        "index_of",
        (
            BuiltinOverload(("string", "string"), "int", "index_of"),
        ),
    ),
    "contains": BuiltinFunction(
        "contains",
        (
            BuiltinOverload(("string", "string"), "bool", "contains"),
            BuiltinOverload(("int[]", "int"), "bool", "array_contains_int"),
            BuiltinOverload(("string[]", "string"), "bool", "array_contains_string"),
            BuiltinOverload(("bool[]", "bool"), "bool", "array_contains_bool"),
            BuiltinOverload(("map<string,int>", "string"), "bool", "map_contains_key_string_int"),
            BuiltinOverload(("set<$item>", "$item"), "bool", "set_contains"),
            BuiltinOverload(("map<$key,$value>", "$key"), "bool", "map_contains_key"),
        ),
    ),
    "starts_with": BuiltinFunction(
        "starts_with",
        (
            BuiltinOverload(("string", "string"), "bool", "starts_with"),
        ),
    ),
    "starts_with_at": BuiltinFunction(
        "starts_with_at",
        (
            BuiltinOverload(("string", "string", "int"), "bool", "starts_with_at"),
        ),
    ),
    "ends_with": BuiltinFunction(
        "ends_with",
        (
            BuiltinOverload(("string", "string"), "bool", "ends_with"),
        ),
    ),
    "has_flag": BuiltinFunction(
        "has_flag",
        (
            BuiltinOverload(("string[]", "string"), "bool", "has_flag"),
        ),
    ),
    "option_value": BuiltinFunction(
        "option_value",
        (
            BuiltinOverload(("string[]", "string"), "string", "option_value"),
        ),
    ),
    "getenv": BuiltinFunction(
        "getenv",
        (
            BuiltinOverload(("string",), "string", "getenv"),
        ),
    ),
    "is_empty": BuiltinFunction(
        "is_empty",
        (
            BuiltinOverload(("string",), "bool", "is_empty"),
            BuiltinOverload(("$item[]",), "bool", "is_empty"),
            BuiltinOverload(("set<$item>",), "bool", "is_empty"),
            BuiltinOverload(("map<$key,$value>",), "bool", "is_empty"),
            BuiltinOverload(("prio_q<$item>",), "bool", "prio_q_is_empty"),
        ),
    ),
    "is_digit": BuiltinFunction(
        "is_digit",
        (
            BuiltinOverload(("string",), "bool", "is_digit"),
        ),
    ),
    "is_alpha": BuiltinFunction(
        "is_alpha",
        (
            BuiltinOverload(("string",), "bool", "is_alpha"),
        ),
    ),
    "is_alnum": BuiltinFunction(
        "is_alnum",
        (
            BuiltinOverload(("string",), "bool", "is_alnum"),
        ),
    ),
    "is_whitespace": BuiltinFunction(
        "is_whitespace",
        (
            BuiltinOverload(("string",), "bool", "is_whitespace"),
        ),
    ),
    "is_space": BuiltinFunction(
        "is_space",
        (
            BuiltinOverload(("string",), "bool", "is_space"),
        ),
    ),
    "length": BuiltinFunction(
        "length",
        (
            BuiltinOverload(("string",), "int", "string_length"),
            BuiltinOverload(("$item[]",), "int", "array_length"),
            BuiltinOverload(("set<$item>",), "int", "set_length"),
            BuiltinOverload(("map<string,int>",), "int", "map_length"),
            BuiltinOverload(("map<$key,$value>",), "int", "map_length"),
        ),
    ),
    "split": BuiltinFunction(
        "split",
        (
            BuiltinOverload(("string", "string"), "string[]", "split_string"),
        ),
    ),
    "split_lines": BuiltinFunction(
        "split_lines",
        (
            BuiltinOverload(("string",), "string[]", "split_lines"),
        ),
    ),
    "replace": BuiltinFunction(
        "replace",
        (
            BuiltinOverload(("string", "string", "string"), "string", "replace_string"),
        ),
    ),
    "trim_left": BuiltinFunction(
        "trim_left",
        (
            BuiltinOverload(("string",), "string", "trim_left_string"),
        ),
    ),
    "trim_right": BuiltinFunction(
        "trim_right",
        (
            BuiltinOverload(("string",), "string", "trim_right_string"),
        ),
    ),
    "last": BuiltinFunction(
        "last",
        (
            BuiltinOverload(("string",), "string", "last_string"),
            BuiltinOverload(("$item[]",), "$item", "last_array"),
        ),
    ),
    "round": BuiltinFunction(
        "round",
        (
            BuiltinOverload(("num", "int"), "num", "round_number"),
        ),
    ),
    "open": BuiltinFunction(
        "open",
        (
            BuiltinOverload(("string",), "file", "open_file"),
        ),
    ),
    "write_line": BuiltinFunction(
        "write_line",
        (
            BuiltinOverload(("file", "string"), "void", "write_line"),
        ),
    ),
    "close": BuiltinFunction(
        "close",
        (
            BuiltinOverload(("file",), "void", "close_file"),
        ),
    ),
    "push": BuiltinFunction(
        "push",
        (
            BuiltinOverload(("$item[]", "$item"), "void", "array_push"),
            BuiltinOverload(("prio_q<$item>", "$item"), "void", "prio_q_push"),
        ),
    ),
    "pop": BuiltinFunction(
        "pop",
        (
            BuiltinOverload(("$item[]",), "$item", "array_pop"),
            BuiltinOverload(("prio_q<$item>",), "$item", "prio_q_pop"),
        ),
    ),
    "create_prio_q": BuiltinFunction(
        "create_prio_q",
        (
            BuiltinOverload(("$item[]", "lambda<$item,$item,int>"), "prio_q<$item>", "create_prio_q"),
        ),
    ),
    "insert": BuiltinFunction(
        "insert",
        (
            BuiltinOverload(("$item[]", "int", "$item"), "void", "array_insert"),
        ),
    ),
    "remove_at": BuiltinFunction(
        "remove_at",
        (
            BuiltinOverload(("$item[]", "int"), "$item", "array_remove_at"),
        ),
    ),
    "clear": BuiltinFunction(
        "clear",
        (
            BuiltinOverload(("$item[]",), "void", "array_clear"),
        ),
    ),
    "sort": BuiltinFunction(
        "sort",
        (
            BuiltinOverload(("$item[]", "lambda<$item,$item,int>"), "void", "array_sort"),
        ),
    ),
    "flat_map": BuiltinFunction(
        "flat_map",
        (
            BuiltinOverload(("$item[]", "lambda<$item,$result[]>"), "$result[]", "flat_map_array"),
        ),
    ),
    "map_to": BuiltinFunction(
        "map_to",
        (
            BuiltinOverload(("$item[]", "lambda<$item,$result>"), "$result[]", "map_array"),
        ),
    ),
    "filter": BuiltinFunction(
        "filter",
        (
            BuiltinOverload(("$item[]", "lambda<$item,bool>"), "$item[]", "filter_array"),
        ),
    ),
    "keys": BuiltinFunction(
        "keys",
        (
            BuiltinOverload(("map<string,int>",), "string[]", "map_keys_string_int"),
            BuiltinOverload(("map<$key,$value>",), "$key[]", "map_keys"),
        ),
    ),
    "values": BuiltinFunction(
        "values",
        (
            BuiltinOverload(("map<string,int>",), "string[]", "map_values_string_int"),
            BuiltinOverload(("map<$key,$value>",), "$value[]", "map_values"),
        ),
    ),
    "join": BuiltinFunction(
        "join",
        (
            BuiltinOverload(("string[]", "string"), "string", "join_strings"),
        ),
    ),
    "sum": BuiltinFunction(
        "sum",
        (
            BuiltinOverload(("int[]",), "int", "sum_int_array"),
            BuiltinOverload(("bool[]",), "int", "sum_bool_array"),
        ),
    ),
}


def is_builtin_function(name: str) -> bool:
    return name in STANDARD_LIBRARY


def resolve_builtin(name: str, argument_types: tuple[str, ...]) -> BuiltinOverload:
    builtin = STANDARD_LIBRARY.get(name)
    if builtin is None:
        raise TypeError(f"Unknown builtin function: {name}")

    for overload in builtin.overloads:
        matched = _match_overload(overload, argument_types)
        if matched is not None:
            return matched

    raise TypeError(f"No overload for builtin {name!r} with arguments {argument_types}")


def _match_overload(overload: BuiltinOverload, actual_types: tuple[str, ...]) -> BuiltinOverload | None:
    if len(overload.argument_types) != len(actual_types):
        return None

    bindings: dict[str, str] = {}
    for expected, actual in zip(overload.argument_types, actual_types, strict=True):
        if not _match_type_pattern(expected, actual, bindings):
            return None

    return BuiltinOverload(
        overload.argument_types,
        _substitute_type_pattern(overload.return_type, bindings),
        overload.lowering,
    )


def _match_type_pattern(expected: str, actual: str, bindings: dict[str, str]) -> bool:
    if expected.startswith("lambda<") and expected.endswith(">"):
        if not (actual.startswith("lambda<") and actual.endswith(">")):
            return False
        expected_parts = _split_generic_arguments(expected[7:-1])
        actual_parts = _split_generic_arguments(actual[7:-1])
        if len(expected_parts) != len(actual_parts):
            return False
        return all(_match_type_pattern(exp, act, bindings) for exp, act in zip(expected_parts, actual_parts, strict=True))
    if "<" in expected and expected.endswith(">"):
        expected_name, expected_args = expected.split("<", 1)
        if not ("<" in actual and actual.endswith(">")):
            return False
        actual_name, actual_args = actual.split("<", 1)
        if expected_name != actual_name:
            return False
        expected_parts = _split_generic_arguments(expected_args[:-1])
        actual_parts = _split_generic_arguments(actual_args[:-1])
        if len(expected_parts) != len(actual_parts):
            return False
        return all(_match_type_pattern(exp, act, bindings) for exp, act in zip(expected_parts, actual_parts, strict=True))
    if expected.endswith("[]"):
        if not actual.endswith("[]"):
            return False
        return _match_type_pattern(expected[:-2], actual[:-2], bindings)
    if expected.startswith("$"):
        bound = bindings.get(expected)
        if bound is None:
            bindings[expected] = actual
            return True
        return bound == actual
    return expected == actual


def _split_generic_arguments(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(value):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return parts


def _substitute_type_pattern(type_name: str, bindings: dict[str, str]) -> str:
    if type_name.startswith("lambda<") and type_name.endswith(">"):
        substituted = ", ".join(_substitute_type_pattern(part, bindings) for part in _split_generic_arguments(type_name[7:-1]))
        return f"lambda<{substituted}>"
    if "<" in type_name and type_name.endswith(">"):
        type_base, type_args = type_name.split("<", 1)
        substituted = ", ".join(_substitute_type_pattern(part, bindings) for part in _split_generic_arguments(type_args[:-1]))
        return f"{type_base}<{substituted}>"
    if type_name.endswith("[]"):
        return f"{_substitute_type_pattern(type_name[:-2], bindings)}[]"
    if type_name.startswith("$"):
        return bindings.get(type_name, type_name)
    return type_name
