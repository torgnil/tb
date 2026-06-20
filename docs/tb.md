# tb: language reference and stdlib

Purpose: a concise reference for tb syntax, types, program structure, compile-time vs runtime behavior, and the standard library. Use this as the authoritative quick guide when developing programs in tb.

Checklist
- Program entry point and invocation
- Basic lexical rules and literals
- Types and declarations
- Expressions and operators
- Statements and control flow
- Functions and UFCS sugar
- Arrays, records, maps, enums
- Compile-time vs runtime folding rules
- Standard library function reference

Note: examples use single-quoted strings (tb requires single quotes). All `int` values are 64-bit. Programs must declare an explicit entry point such as `int main(string[] args) { ... }` or `int main(string[] args): ...`.

---

1. Quick start

Example program (prints argument count and first user arg if present):

```tb
int main(string[] args):
    print('args: ' + args.length())
    if (args.length() > 1):
        print('first user arg: ' + args[1])
```

Compile and run with the self-hosted compiler:

```bash
./build_tb.sh
./tb.sh input.tb
./input
```

Bootstrap path using the Python compiler:

```bash
python3 compiler/python/tb.py input.tb output.ll
clang output.ll -o program
./program
```

2. Lexical rules

- Strings: single quotes only. Example: `'hello'`.
- Supported string escapes inside single-quoted strings:
  - `\\`
  - `\'`
  - `\n`
  - `\r`
  - `\t`
- Single-quoted strings may span multiple lines; embedded literal newlines and indentation are preserved verbatim.
- Integers: sequences of digits, e.g. `123` (64-bit `int`).
- Num literals: represented internally as `value` + `scale` (fixed-point style); syntax uses decimal form like `12.34` where supported.
- Identifiers: letters, digits and `_`, not starting with a digit.
- Comments: `#` line comments and `/* ... */` block comments.
- Every token carries `type`, `value`, `line`, and `column`; lexer errors report exact line/column.

3. Program structure and entry point

- Every runnable program must declare `int main(string[] args) { ... }` or `int main(string[] args): ...` as the entry point.
- `args[0]` is the executable path from the generated `main(argc, argv)` wrapper. User-supplied CLI arguments start at `args[1]`.
- There is currently no built-in “user args only” helper; use manual indexing/slicing patterns or helpers such as `has_flag(args, '--flag')` and `option_value(args, '--opt')` on the full `args` array.
- Top-level variable declarations are allowed, including `const` globals; they run in the generated entry wrapper.
- Top-level executable statements are rejected: executable code belongs inside `main` or other functions.

4. Types

- int — 64-bit signed integer.
- void — no return value; valid for function return types such as `void log(string s) { ... }`.
- num — fixed-point numeric type (decimal stored as integer value + scale).
- string — immutable text value (single-quoted literal).
- bool — compile-time and runtime boolean values (`true`, `false`).
- file — runtime file handle produced by `open(...)`.
- T[] — arrays of T (e.g. `string[]`, `int[]`, `string[][]`).
- map<K, V> — currently implemented as `map<string, int>`. Use `{}` or `{'key': value}` in a typed context such as `map<string, int> counts = {};`.
  - Generic maps are not implemented yet; other key/value combinations are rejected today.
- record — user-defined record types with named fields.
- enum — named constants.

5. Declarations

- Variable declaration (typed):

  `int x = 1;`

  `string s = 'hello';`

- Immutable variable declaration:

  `const int answer = 42;`

  `const string greeting = 'hello';`

  `const` bindings are compile-time enforced. Reassignment such as `answer = 7;` fails at compile time. Direct mutation through a const array, set, or record binding such as `nums.push(3);`, `nums[0] = 1;`, or `point.x = 2;` also fails at compile time.
  By convention, fixed configuration values and named constants use `UPPER_CASE`.

- Record declaration (example):

  `record Point(int x, int y);`

  Constructor syntax: `Point(1, 2)` creates a record instance (lowered to heap-allocated record when needed).

- Function declaration (typed):

  `int add(int a, int b): return a + b`

- Cached function declaration:

  `cached int fib(int n): ...`

  `cached` memoizes `int`-returning helper functions. The current implementation supports a single cacheable parameter such as `int`, `string`, `bool`, enums, and cacheable record values. Cached record parameters may contain scalar fields, nested cacheable records, and nested cacheable arrays such as `int[]`, `int[][]`, `string[]`, or `bool[][]`.

6. Expressions and operators

- Arithmetic: `+`, `-`, `*`, `/`, `%`.
- Integer `/` and `%` use signed truncating division, matching LLVM runtime behavior. Division rounds toward zero, and the remainder keeps the sign of the left operand. Examples: `(0 - 5) / 3` is `-1`, `(0 - 5) % 3` is `-2`, `5 % (0 - 3)` is `2`, and `(0 - 5) % (0 - 3)` is `-2`.
- Compile-time `num` arithmetic keeps the highest operand precision for `+`, `-`, `*`, and `/`. For example, `1.5 + 2.50` yields `4.00`, `2.50 * 1.5` yields `3.75`, and `2.50 / 1.5` yields `1.67`.
- Bitwise integers: `&`, `|`, `^`, `<<`, `>>`.
- Integer shifts require a non-negative shift count. Counts `>= 64` shift all bits out: `x << 64` becomes `0`, and `x >> 64` becomes `0` for non-negative `x` or `-1` for negative `x`.
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`.
- Boolean: `&&`, `||`, unary `!` (and aliases `and`, `or`, `not`).
- Assignment: `=`, with compound operators `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, and `>>=`, plus postfix `++` / `--` shorthand for identifier assignments.
- Compound assignment also works on array element and record field targets such as `nums[i] += 1;`, `nums[i] >>= 1;`, and `point.x |= 1;`.
- Ternary (compile-time): `condition ? whenTrue : whenFalse`.
- Lambdas: single-parameter lambdas such as `int x -> x * 2`, block lambdas such as `int[] row -> { return row[0] < 0; }`, and multi-parameter comparator lambdas such as `(int a, int b) -> a - b`.
- UFCS (parser sugar): `value.method(args)` lowers to `method(value, args)` — parser-only sugar, no dynamic dispatch.

7. Statements and control flow

- Expression statement: `expr;`.
- Variable declaration statement: `int i = 0;`.
- Blocks support two forms:
  - braces: `if (cond) { ... }`
  - indentation with a mandatory colon: `if (cond): ...`
- In indented blocks, statements may end at newline instead of `;`.
- If/else: `if (cond) { ... } else { ... }` or `if (cond): ... else: ...`.
- While loops: `while (cond) { ... }` or `while (cond): ...`.
- For loops (C-style): `for (int i = 0; i < n; i++) { ... }` or `for (int i = 0; i < n; i++): ...` — lowers to structured IR with condition, body, update and end labels.
- Foreach (array or set iteration): `for (string line : lines) { ... }`, `for (string line : lines): ...`, `for (string line in lines) { ... }`, or `for (string line in lines): ...`.
- `for (int i : range(n))` iterates over the fixed array produced by `range(...)`; it does not observe later mutations to some other array while the loop runs.
- Switch: `switch (expr) { case value: { ... } default: { ... } }` or:

  ```tb
  switch (expr):
      case value:
          ...
      default:
          ...
  ```

  Switch has no fallthrough and supports `int`, `string`, and enum values.
- Continue and break are supported inside loop bodies, including nested `if` / `switch` blocks within `for`, `foreach`, and `while`.
- `return;` is allowed inside `void` functions for early exit.
- Exceptions use `throw expr`, where `expr` must be string-compatible. `exception` is currently a string-backed alias for catch bindings.
- Catch exceptions with `try` / `catch`:

  ```tb
  try:
      throw 'boom'
  catch (exception err):
      print(err)
  ```

  If an exception is not caught, the program prints `Unhandled exception: ...` and exits with a non-zero status.

8. Arrays and slices

- Array literal: `['a', 'b', 'c']`.
- Empty array literals are allowed in a typed context, for example `int[] nums = [];` or `string[] words = [];`.
- Indexing: `arr[0]`, with negative indexing like `arr[-1]` (last element) supported for arrays and strings.
- Slice notation with `[]` is supported for both arrays and strings. For example, `nums[1:3]` gives a subarray, and `text[2:5]` gives a substring. Open-ended, omitted-start, and negative-end slices are supported, e.g. `arr[1:]`, `text[:3]`, `text[:-1]`.
  - Negative end bounds follow Python-style exclusive semantics, so `text[:-1]` drops the last character and `nums[0:-1]` drops the last element.
  - Example (array): `int[] nums = [1, 2, 3, 4]; int[] mid = nums[1:3];  // [2, 3]`
  - Example (string): `string s = 'hello'; string sub = s[1:4];  // 'ell'`
- Runtime arrays are heap-backed when mutation or runtime flow requires it. Helpers: `push`, `pop`, `insert`, `remove_at`, `clear`, `sort`, `map_to`, `filter`, and `flat_map`.
- `filter` keeps the elements whose predicate returns `true` and returns a new array of the same item type.
- `prio_q<T>` is supported for runtime element types such as `int`, `bool`, `string`, enums, records, and arrays. Create one with `create_prio_q(values, comparator)` or UFCS form `values.create_prio_q(comparator)`, mutate it with `pq.push(value)`, test with `is_empty(pq)` or `pq.is_empty()`, and remove the highest-priority item with `pop(pq)` or `pq.pop()`. The queue copies the source array, so later mutations of the original array do not affect the queue.
- There are currently no built-in fill/copy helpers for arrays; initialize or clone arrays explicitly with loops or helper functions when needed.
- There is currently no stdlib disjoint-set / union-find helper.
- `sort` is in-place and mutates the target array. It accepts either a named comparator function `int compare(T a, T b)` or an inline comparator lambda `(T a, T b) -> ...`, where negative means left-first, zero means equal, and positive means right-first.
- `map_to` transforms each element with a single-parameter lambda and returns a new array of the lambda result type. Prefer it over hand-written “create result, loop, push” helpers when one array maps directly to another.
- `flat_map` transforms each element into an array and flattens one level, so `T[]` can become `U[]` through a `T -> U[]` lambda.

9. Records and fields

- Access: `r.field`.
- Field writes and reads lower to runtime heap-backed record values when needed.

10. Compile-time vs runtime evaluation

- Many helpers and expressions are folded at compile time when inputs are compile-time constants:
  - `to_int(...)`, `to_num(...)` resolve at compile time for constant string inputs.
  - `substring(...)`, `split(...)`, `trim()` may fold at compile time for constant strings.
- File IO is always runtime:
  - `read_lines(path)` always reads `path` when the compiled program runs.
  - `read_file(path)` always reads `path` when the compiled program runs.
  - The compiler emits the file path string, not the file contents, into the generated LLVM.
- Const enforcement is compile-time:
  - reassigning a `const` variable is rejected during compilation
  - direct mutation through a `const` array, set, or record binding is also rejected during compilation
- When values are not known at compile time, corresponding operations lower to runtime helpers and library calls.

11. Built-in calling and printing

- `print(...)` is provided by the standard library (resolved via `compiler/python/stdlib.py`), not a keyword.
- Integer printing uses `printf` with `%lld\n` via an emitted LLVM format string.
- Runtime string concatenation with `int` and `num` values is supported; the compiler automatically converts numeric values to strings when concatenating or printing. Explicit `to_string()` is also available for supported types.

12. Error reporting

- Lexer and parser errors include exact line and column. Runtime errors raise descriptive messages.

13. Standard library (stdlib) reference

All stdlib functions are defined in `compiler/python/stdlib.py`. The reference below describes their behavior and typical signatures.

Core IO and string helpers

- print(value) -> void
  - Print representation of `value` followed by newline. Works with `int`, `num`, `string`, `bool`, arrays and records (stringified).

- read_lines(path: string) -> string[]
  - Read an entire file and split into lines at runtime.

- read_file(path: string) -> string
  - Read the entire file contents at runtime and return them as one string.
  - Return file contents as a single string.

- open(path: string, mode: string = 'r') -> file
  - Open a file handle for runtime file IO. Lowered to runtime file operations.

- write_line(f: file, line: string) -> void
  - Append `line` with a newline to the file handle.

Conversion and numeric helpers

- to_int(s: string) -> int
  - Parse integer from string. If `s` is compile-time known, resolves at compile time.

- to_num(s: string) -> num
  - Parse decimal string into `num` representation (value + scale).

- to_string(value) -> string
  - Convert supported values to strings. Current overloads cover `string`, `int`, `num`, `bool`, `int[]`, `string[]`, `bool[]`, and `set<int>`.

- popcount(value: int) -> int
  - Count the set bits in the 64-bit two's-complement representation of `value`.

- round(n: num, target_scale: int) -> num
  - Round `num` to `target_scale` using half-up rounding (compile-time for constant inputs).
- Integer overflow is currently unchecked; tb does not yet expose widened integer types beyond 64-bit `int`.

String helpers

- split(s: string, sep: string) -> string[]
  - Split string on `sep`. Also available as UFCS: `s.split(',')`.
  - UFCS helpers can be used in assignments too, for example `parts = text.split(',');` and `text = text.trim();`.

- trim(s: string) -> string
  - Remove leading and trailing whitespace. UFCS sugar `s.trim()` supported.

- trim_left(s: string) -> string
  - Remove leading whitespace only. UFCS sugar `s.trim_left()` supported.

- trim_right(s: string) -> string
  - Remove trailing whitespace only. UFCS sugar `s.trim_right()` supported.

- substring(s: string, start: int) -> string
  - Return the substring from `start` to the end.

- substring(s: string, start: int, end: int) -> string
  - Return the substring from `start` up to `end` (exclusive).

- char_at(s: string, index: int) -> string
  - Return the single-character string at `index`. `s[index]`, `s.char_at(index)`, and `s[index:index+1]` are equivalent practical options.

- index_of(s: string, sub: string) -> int
  - Returns index of `sub` in `s` or -1.

- contains(s: string, sub: string) -> bool
  - True when `sub` appears in `s`.

- is_digit(ch: string) -> bool
  - True when `ch` is a single ASCII digit.

- is_alpha(ch: string) -> bool
  - True when `ch` is a single ASCII letter.

- is_alnum(ch: string) -> bool
  - True when `ch` is a single ASCII letter or digit.

- is_whitespace(ch: string) -> bool
  - True when `ch` is a single whitespace character.

- is_space(ch: string) -> bool
  - Alias for `is_whitespace(ch)`.

- last(s: string) -> string
  - Return the last character as a single-character string, or `''` for the empty string.

- replace(s: string, old: string, new: string) -> string
  - Replace occurrences of `old` with `new`.

- join(arr: string[], sep: string) -> string
  - Join array elements with `sep`.

Array helpers

- length(x: T[] | string | map) -> int
  - Return length of array, string, set, or `map<string, int>`.

- push(arr: T[], value: T) -> void
  - Append `value` to `arr` (may cause runtime heap-backed array representation).
  - Works for nested arrays too, for example `int[][] rows = []; rows.push([1, 2]);`.

- pop(arr: T[]) -> T
  - Remove and return last element.

- last(arr: T[]) -> T
  - Return the last element. Empty arrays still follow normal runtime bounds behavior.

- insert(arr: T[], index: int, value: T) -> void

- remove_at(arr: T[], index: int) -> T

- clear(arr: T[]) -> void

- contains(arr: T[], value: T) -> bool
  - Return `true` when the array contains `value`. Also available via UFCS (`arr.contains(value)`) and membership syntax (`value in arr`) for supported arrays, sets, and map keys.

- is_empty(x: string | T[] | set<T> | map<K, V> | prio_q<T>) -> bool
  - Return `true` when the value has no items. UFCS sugar such as `arr.is_empty()` and `scores.is_empty()` is supported.

- sort(arr: T[], compare: (T, T) -> int) -> void
  - Sort the array in place using the provided comparator.
  - Comparator can be a named function such as `compare` with signature `int compare(T a, T b)` or an inline lambda such as `(int a, int b) -> a - b`.

- map_to(arr: T[], item -> expr) -> U[]
  - Transform each element with a single-parameter lambda and return a new array containing the lambda results.
  - Example: `lines.map_to(string line -> parse_point(line))`
  - Example: `range(5).map_to(int i -> i * i)` builds a new `int[]` without a manual push loop.

- filter(arr: T[], item -> bool) -> T[]
  - Keep the items for which the predicate returns `true` and return a new array.
  - Example: `lines.filter(string line -> { return !line.trim().is_empty(); })`

- flat_map(arr: T[], item -> U[]) -> U[]
  - Transform each element into an array and flatten the results by one level.
  - Example: `range(n).flat_map(int i -> edges_for_point(points, i))`

- sum(arr: int[]) -> int
  - Aggregate helper for integer arrays (compile-time for constant arrays).

- abs(x: int | num) -> int | num
  - Return the absolute value. `num` remains compile-time today; runtime lowering currently covers `int`.

- min(a: int | num, b: int | num) -> int | num
  - Return the smaller value. `int` lowers at runtime; `num` is currently folded at compile time.

- max(a: int | num, b: int | num) -> int | num
  - Return the larger value. `int` lowers at runtime; `num` is currently folded at compile time.

- sqrt(x: int | num) -> num
  - Return the square root as `num`. Constant inputs are folded at compile time.

Set and map helpers

- map literal syntax: `{'a': 1, 'b': 2}` in a typed context such as `map<string, int> counts = {'a': 1};`
- empty map literal: `map<string, int> counts = {};`
- `map<K, V>` supports cache-stringifiable keys such as `int`, `string`, arrays, and records with cache-stringifiable fields.
- map.keys() -> `K[]`
- map.values() -> `V[]`
- contains(map<K, V>, key: K) -> bool
  - Return `true` when `key` exists in the map. Also available as `map.contains(key)` and `key in map`.
- Set literals support cache-stringifiable complex values such as arrays and records, for example `set<Row> rows = {Row(1, 2)};`

Hashing, misc

- hash(v) -> int
  - Compute integer hash for `int`, `num`, `string` and arrays; UFCS sugar `v.hash()`.

- range(n) -> int[]
  - `range(end)` yields integers `0`..`end-1`.

- range(start, end) -> int[]
  - Yields `start`..`end-1`.

File and IO advanced

- split_lines(s: string) -> string[]
  - Efficient split by newlines.

- write_all(path: string, s: string) -> void
  - Convenience to overwrite file contents.

14. Examples

- Read lines and print numbered:

```tb
int main(string[] args):
    string[] lines = read_lines('input.txt')
    for (int i : range(lines.length())):
        print(i + ': ' + lines[i])
```

- Record usage:

```tb
record Person(string name, int age);

int main(string[] args):
    Person p = Person('Alice', 30)
    print(p.name + ' is ' + p.age)
```
