#!/usr/bin/env python3
"""Check native compile-time enforcement for const bindings."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


NEGATIVE_CASES = {
    "plain_rebind": ("const int item = 1\n    item = 2", "assign", "item"),
    "compound_rebind": ("const int item = 1\n    item += 2", "assign", "item"),
    "postfix_rebind": ("const int item = 1\n    item++", "assign", "item"),
    "array_index": ("const int[] values = [1]\n    values[0] = 2", "mutate", "values"),
    "nested_index": ("const int[][] values = [[1]]\n    values[0][0] = 2", "mutate", "values"),
    "map_index": ("const map<string, int> values = {'x': 1}\n    values['x'] = 2", "mutate", "values"),
    "record_field": ("const Point point = Point(1, 2)\n    point.x = 3", "mutate", "point"),
    "nested_record": (
        "const Holder holder = Holder(Point(1, 2), [1])\n    holder.point.x = 3",
        "mutate",
        "holder",
    ),
    "nested_record_array_mutator": (
        "const Holder holder = Holder(Point(1, 2), [1])\n    holder.values.push(2)",
        "mutate",
        "holder",
    ),
    "builtin_ufcs_despite_helper_name": (
        "const int[] values = [1]\n    values.push(2)",
        "mutate",
        "values",
    ),
    "push_call": ("const int[] values = [1]\n    push(values, 2)", "mutate", "values"),
    "push_ufcs": ("const int[] values = [1]\n    values.push(2)", "mutate", "values"),
    "pop_expression": ("const int[] values = [1]\n    print(pop(values))", "mutate", "values"),
    "pop_ufcs": ("const int[] values = [1]\n    values.pop()", "mutate", "values"),
    "insert_call": ("const int[] values = [1]\n    insert(values, 0, 2)", "mutate", "values"),
    "insert_ufcs": ("const int[] values = [1]\n    values.insert(0, 2)", "mutate", "values"),
    "remove_call": ("const int[] values = [1]\n    remove_at(values, 0)", "mutate", "values"),
    "remove_ufcs": ("const int[] values = [1]\n    values.remove_at(0)", "mutate", "values"),
    "clear_call": ("const int[] values = [1]\n    clear(values)", "mutate", "values"),
    "clear_ufcs": ("const int[] values = [1]\n    values.clear()", "mutate", "values"),
    "sort_ufcs": (
        "const int[] values = [2, 1]\n    values.sort((int a, int b) -> a - b)",
        "mutate",
        "values",
    ),
    "sort_call": (
        "const int[] values = [2, 1]\n    sort(values, (int a, int b) -> a - b)",
        "mutate",
        "values",
    ),
    "lambda2_mutator": (
        "const int[] values = [2, 1]\n    sort([2, 1], (int a, int b) -> pop(values))",
        "mutate",
        "values",
    ),
    "set_add": ("const set<int> values = {1}\n    values.add(2)", "mutate", "values"),
    "set_add_call": ("const set<int> values = {1}\n    add(values, 2)", "mutate", "values"),
    "queue_push": (
        "const prio_q<int> values = create_prio_q([1], compare)\n    values.push(2)",
        "mutate",
        "values",
    ),
    "queue_pop_call": (
        "const prio_q<int> values = create_prio_q([1], compare)\n    print(pop(values))",
        "mutate",
        "values",
    ),
    "if_body": ("const int item = 1\n    if (true):\n        item = 2", "assign", "item"),
    "while_body": ("const int item = 1\n    while (false):\n        item = 2", "assign", "item"),
    "for_init": ("const int item = 1\n    for (item = 2; false; item++):\n        print(item)", "assign", "item"),
    "for_update": ("const int item = 1\n    for (int i = 0; i < 1; item++):\n        print(i)", "assign", "item"),
    "for_body": ("const int item = 1\n    for (int i = 0; i < 1; i++):\n        item = 2", "assign", "item"),
    "foreach_body": (
        "const int item = 1\n    for (int i : [1]):\n        item = 2",
        "assign",
        "item",
    ),
    "switch_case": (
        "const int item = 1\n    switch (1):\n        case 1:\n            item = 2\n        default:\n            print(item)",
        "assign",
        "item",
    ),
    "try_body": (
        "const int item = 1\n    try:\n        item = 2\n    catch (exception err):\n        print(err)",
        "assign",
        "item",
    ),
    "catch_body": (
        "const int item = 1\n    try:\n        throw 'x'\n    catch (exception err):\n        item = 2",
        "assign",
        "item",
    ),
    "lambda_mutator": (
        "const int[] values = [1]\n    int result = (int x -> pop(values))(1)",
        "mutate",
        "values",
    ),
    "forward_global": (
        "int change():\n    LATER[0] = 2\n    return 0\nconst int[] LATER = [1]\nint main(string[] args):\n    return change()",
        "mutate",
        "LATER",
    ),
}


def source_for(body: str, declarations: str = "") -> str:
    body_lines = []
    for line in body.splitlines():
        if line.startswith("    "):
            line = line[4:]
        body_lines.append("    " + line if line else "")
    return (
        "record Point(int x, int y);\n"
        "record Box(int value);\n"
        "record Holder(Point point, int[] values);\n"
        "int compare(int a, int b):\n    return a - b\n"
        + declarations
        + "int main(string[] args):\n"
        + "\n".join(body_lines)
        + "\n    return 0\n"
    )


def run_compile(compiler: Path, root: Path, name: str, source: str) -> subprocess.CompletedProcess[str]:
    source_path = root / f"{name}.tb"
    output_path = root / f"{name}.ll"
    source_path.write_text(source, encoding="utf-8")
    return subprocess.run(
        [str(compiler), str(source_path), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify native const-binding diagnostics.")
    parser.add_argument("--compiler", default="bin/tb", help="Path to the self-hosted tb compiler")
    args = parser.parse_args(argv)
    compiler = Path(args.compiler).resolve()
    if not compiler.is_file():
        print(f"Missing tb compiler binary: {compiler}", file=sys.stderr)
        return 1

    positives = {
        "read_and_mutable": (
            "int shadow(int fixed):\n"
            "    fixed += 1\n"
            "    return fixed\n",
            "const int[] fixed = [1]\n"
            "int[] mutable = [1]\n"
            "mutable.push(fixed[0])\n"
            "print(fixed[0])\n"
            "print(shadow(fixed[0]))"
        ),
        "user_helper_named_mutator": (
            "int sort(int value):\n    return value\n",
            "const int fixed = 3\n"
            "print(sort(fixed))"
        ),
        "ufcs_helper_name_on_scalar": (
            "int push(int value):\n    return value\n",
            "const int[] fixed = [1]\n"
            "const Box box = Box(2)\n"
            "print(fixed[0].push())\n"
            "print(box.value.push())"
        ),
        "free_helper_name_on_container": (
            "int push(int[] values, int value):\n    return 77\n",
            "const int[] fixed = [1]\n"
            "print(push(fixed, 2))"
        ),
        "mutable_parameter_shadows_global": (
            "const int fixed = 1\nint update(int fixed):\n"
            "    fixed += 1\n"
            "    return fixed\n",
            "print(update(fixed))"
        ),
        "foreach_binding_shadows_global": (
            "const int fixed = 1\n",
            "for (int fixed : [2]) { print(fixed); }"
        ),
        "const_union_is_pure": (
            "",
            "const set<int> fixed = {1}\n"
            "set<int> merged = fixed.union({2})\n"
            "print(merged.length())"
        ),
    }

    try:
        with tempfile.TemporaryDirectory(prefix="tb_const_bindings_") as tmp_dir:
            root = Path(tmp_dir)
            for name, (body, diagnostic, binding) in NEGATIVE_CASES.items():
                if name == "forward_global":
                    source = (
                        "int change():\n"
                        "    LATER[0] = 2\n"
                        "    return 0\n"
                        "const int[] LATER = [1]\n"
                        "int main(string[] args):\n"
                        "    return change()\n"
                    )
                else:
                    declarations = ""
                    if name == "builtin_ufcs_despite_helper_name":
                        declarations = "int push(int[] values, int value):\n    return 77\n"
                    source = source_for(body, declarations)
                result = run_compile(compiler, root, name, source)
                output = result.stdout + result.stderr
                if diagnostic == "assign":
                    expected = f"Cannot assign to const variable: {binding}"
                else:
                    expected = f"Cannot mutate const variable: {binding}"
                if result.returncode != 1 or expected not in output:
                    raise RuntimeError(
                        f"{name}: expected semantic compile failure (status 1) and {expected!r}; "
                        f"got status {result.returncode}, output {output!r}"
                    )
                print(f"PASS reject {name}")
            for name, (declarations, body) in positives.items():
                result = run_compile(compiler, root, name, source_for(body, declarations))
                output = result.stdout + result.stderr
                if result.returncode != 0:
                    raise RuntimeError(
                        f"{name}: expected successful compile; got status {result.returncode}, output {output!r}"
                    )
                print(f"PASS allow {name}")
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Verified {len(NEGATIVE_CASES)} rejections and {len(positives)} accepted controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
