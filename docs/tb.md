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

Build and invocation details are documented in the repository or release `README.md`. This document focuses on language and standard library behavior.

2. Lexical rules

- Strings: single quotes only. Example: `'hello'`.
- String literals live for the duration of the program and can be stored in containers or passed to and returned from functions.
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
- Comments: `#` line comments and `/* ... */` block comments. Delimiters and quotes after `#` are comment text and do not affect strings or block comments; `#` inside a string or block comment remains part of that content.
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

  `const` bindings are compile-time enforced. Reassignment such as `answer = 7;` fails at compile time. Direct mutation through a const array, set, or record binding such as `nums.push(3);`, `nums[0] = 1;`, or `point.x = 2;` also fails at compile time. Const controls mutation permission, not ownership: runtime-managed const locals are released with other function locals on normal function exit, and returning a const string preserves its value before that cleanup.
  By convention, fixed configuration values and named constants use `UPPER_CASE`.

- Record declaration (example):

  `record Point(int x, int y);`

  Constructor syntax: `Point(1, 2)` creates a record instance (lowered to heap-allocated record when needed).

- Function declaration (typed):

  `int add(int a, int b): return a + b`

- Cached function declaration:

  `cached int fib(int n): ...`

  `cached` memoizes `int`-returning helper functions. The current implementation supports a single cacheable parameter such as `int`, `string`, `bool`, enums, and cacheable record values. Cached record parameters may contain scalar fields, nested cacheable records, and nested cacheable arrays such as `int[]`, `int[][]`, `string[]`, or `bool[][]`.

  Native memoization currently covers one `int` parameter or a simple record with one or two `int` fields. These tables are synchronized across workers. The function body runs outside the cache lock, so recursive calls and exceptions remain supported. Simultaneous misses may evaluate the body more than once. A full native cache evaluates missing keys without storing them.

6. Expressions and operators

- Arithmetic: `+`, `-`, `*`, `/`, `%`.
- Integer `/` and `%` use signed truncating division, matching LLVM runtime behavior. Division rounds toward zero, and the remainder keeps the sign of the left operand. Examples: `(0 - 5) / 3` is `-1`, `(0 - 5) % 3` is `-2`, `5 % (0 - 3)` is `2`, and `(0 - 5) % (0 - 3)` is `-2`.
- Compile-time `num` arithmetic keeps the highest operand precision for `+`, `-`, `*`, and `/`. For example, `1.5 + 2.50` yields `4.00`, `2.50 * 1.5` yields `3.75`, and `2.50 / 1.5` yields `1.67`.
- Bitwise integers: `&`, `|`, `^`, `<<`, `>>`.
- Integer shifts require a non-negative shift count; a negative runtime count aborts. Counts `>= 64` shift all bits out: `x << 64` becomes `0`, and `x >> 64` becomes `0` for non-negative `x` or `-1` for negative `x`.
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`.
- Boolean: `&&`, `||`, unary `!` (and aliases `and`, `or`, `not`).
- Assignment: `=`, with compound operators `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, and `>>=`, plus postfix `++` / `--` shorthand for identifier assignments.
- Compound assignment also works on array element and record field targets such as `nums[i] += 1;`, `nums[i] >>= 1;`, and `point.x |= 1;`. The target base and index are evaluated once, and the selected element or field value is read before the right-hand side. Negative array indices select their element before right-hand-side effects, including changes to the array length. Explicit ordinary assignment such as `nums[f()] = nums[f()] + 1;` evaluates both written calls independently.
- Ternary (compile-time): `condition ? whenTrue : whenFalse`.
- Lambdas: single-parameter lambdas such as `int x -> x * 2`, block lambdas such as `int[] row -> { return row[0] < 0; }`, and multi-parameter comparator lambdas such as `(int a, int b) -> a - b`.
- UFCS (parser sugar): `value.method(args)` lowers to `method(value, args)` — parser-only sugar, no dynamic dispatch.

### Thread pools and futures

- `thread_pool(n)` creates an explicit pool with exactly `n` worker threads. `n` must be from `1` to `2147483647`. If allocation, synchronization initialization, or worker creation fails during startup, any started workers are stopped and joined, initialized resources are released, and the process exits with `thread_pool startup failed`. A partially started pool is never returned. Allocation failures are not handled uniformly, including failures during task submission.
- `pool.submit(work)` or `pool.submit(work, value)` queues a top-level named function and returns `future<T>` immediately.
- Const pool bindings support `submit`; const future bindings support `await`, `is_done`, and `wait_for`. Const still prevents reassignment.
- Submitted functions may return `int`, `bool`, `string`, `int[]`, or `int[][]`; they may accept zero arguments or one `int`, `bool`, `string`, `int[]`, or `int[][]` argument.
- `future.await()` blocks until completion and returns the task result. A task exception is rethrown by `await()` on the calling thread. The future preserves its message independently of submitted argument bindings; repeated awaits each produce a catch-owned message.
- `future.is_done()` returns whether the task has completed without blocking.
- `future.wait_for(milliseconds)` waits for the requested timeout using the system wall clock and returns whether the task completed; clock adjustments can affect the elapsed duration. It does not consume the result; call `await()` afterward. Nonpositive durations only check the current completion state. Avoid pool dependency deadlocks: tasks must not all block waiting for work queued to the same fixed-size pool.
- String task arguments and results share immutable managed values across workers; repeated awaits preserve the result. Internal string reference counts, character caching, runtime counters, and native memoization tables for `cached` functions are synchronized. The scoped audit and concurrency/lifetime checks cover these runtime paths on macOS arm64; they do not establish safety for arbitrary user code or foreign libraries. User globals and mutable containers, including accesses made inside cached function bodies, are not synchronized.
- `int[]` and `int[][]` arguments cross the queue as deep-copy snapshots. `int[]` and `int[][]` results are retained by their futures and each `await()` returns a fresh snapshot. Records, maps, sets, priority queues, files, pools, futures, and closures cannot yet be returned or otherwise passed across a task boundary.
- Do not start worker tasks from global initializers if they may read globals that have not finished initializing. Initialize shared state before starting tasks, preferably from `main`.

```tb
int worker_id():
    return 7

int main(string[] args):
    thread_pool pool = thread_pool(2)
    future<int> id = pool.submit(worker_id)
    print(id.await())
    return 0
```

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
- Values changed in a runtime loop use their current iteration values, including in reads that appear before the write in the loop body. Unmodified constants remain eligible for compile-time folding.
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
- A `continue` in a C-style `for` loop runs its update before testing the condition again; `break` and `return` skip the update.
- `return;` is allowed inside `void` functions for early exit.
- Reaching the end of a `void` function releases its managed local values just like an explicit `return;`. Borrowed parameters remain available to the caller.
- Empty brace bodies such as `void noop(string text) {}` are allowed. Calls still evaluate their arguments, and borrowed values remain available to the caller. An empty `int main` returns `0`; other non-void functions must return a value or throw on every reachable path.
- Reaching the end of an `int main` without an explicit return releases its managed local values before the generated entry point returns `0`, including local thread pools that must stop and join their workers. Borrowed parameters and globals remain outside that local cleanup.
- No extra trailing return is needed when every reachable path in a non-void function returns or throws.
- Returning a local map transfers its owned value to the caller, which keeps it alive until that value is released. Mutable and const local maps follow this rule. Returning a borrowed parameter or global map produces an independent copy.
- Returning a function-local `int[]`, `bool[]`, `int[][]`, or `string[]` transfers that owned array to the caller, which releases it normally. Const local arrays follow the same rule. Returning a borrowed parameter or global array produces an independent copy. Returning a borrowed `bool[]` field of a record parameter also produces an independent copy.
- Returning a string from a function preserves the value before releasing that function's local variables. This includes direct local bindings and strings read from a local array or record field; borrowed parameters and literals keep their existing behavior.
- Exceptions use `throw expr`, where `expr` must be string-compatible. `exception` is currently a string-backed alias for catch bindings.
- Catch exceptions with `try` / `catch`:

  ```tb
  try:
      throw 'boom'
  catch (exception err):
      print(err)
  ```

  A direct throw caught in the same function preserves preceding local mutations
  and live arrays, strings, and other function-owned values. The catch receives
  a string snapshot that remains valid if the original message binding changes.
  Nested throws use the nearest active try; a throw from a catch uses an enclosing
  try, if present. Catch messages own their string snapshot, including messages
  thrown by another function or worker, and may be returned or rethrown safely.

  If an exception is not caught, the program prints its message and exits with a non-zero status. Missing `read_file` and `read_lines` inputs print `<helper>: <path>` and exit with status 1 when uncaught. Nonlocal exception transfer can bypass cleanup in intervening function frames, leaking managed values or other owned resources. Catch inside the function that owns resources when cleanup matters; normal return paths perform cleanup. This is not general exception-unwind safety.

8. Arrays and slices

- Array literal: `['a', 'b', 'c']`.
- Empty array literals are allowed in a typed context, for example `int[] nums = [];`, `string[] words = [];`, or `box.values = [];` when `values` is an array-valued record field. The field's declared array type determines the empty array's element type.
- Empty rows in a typed nested array literal use the row element type, for example `int[][] rows = [[1], []];` creates an empty `int[]` row.
- Indexing: `arr[0]`, with negative indexing like `arr[-1]` (last element) supported for arrays and strings. For arrays, negative indices count from the end for both reads and writes: `arr[-length(arr)]` refers to the first element.
- Slice notation with `[]` is supported for both arrays and strings. For example, `nums[1:3]` gives a subarray, and `text[2:5]` gives a substring. Open-ended, omitted-start, and negative-end slices are supported, e.g. `arr[1:]`, `text[:3]`, `text[:-1]`.
  - Negative start and end bounds count from the end before being clamped, following Python-style exclusive semantics. For example, `nums[-3:-1]` selects the middle two elements, and `nums[:-1]` drops the last element.
  - Example (array): `int[] nums = [1, 2, 3, 4]; int[] mid = nums[-3:-1];  // [2, 3]`
  - Runtime slices of `bool[]` also return independent mutable arrays, including when the source is const; changing either array leaves the other unchanged.
  - Runtime slices of `int[]` and `string[]` are owned independent arrays. Discarded slices release their storage, while returning a slice or storing it in a record transfers ownership without an extra snapshot. String elements retain their normal shared immutable values.
  - Example (string): `string s = 'hello'; string sub = s[1:4];  // 'ell'`
- Function-local `int[]` declarations and reassignment copy borrowed arrays, including const arrays, parameters, globals, indexed rows, and record fields. Mutating the copy leaves its source unchanged. Owned array literals and call results transfer into the local binding. Record construction and field replacement snapshot borrowed `int[]` arrays, and record cloning copies owned `int[]` fields; owned array temporaries transfer into the field. Returning an `int[]` field from a local record snapshots it before the record is released, while returning an owned local array transfers it directly to the caller.
- Function-local `bool[]` declarations and reassignment also copy borrowed arrays, including const arrays, parameters, globals, and record fields. Mutating the copy leaves its source unchanged. Owned array literals and call results transfer into the local binding.
- Function-local `string[][]` declarations and reassignment copy borrowed arrays by cloning the outer array and its child `string[]` arrays. Strings remain shared immutable values. Owned literals and call results transfer into the local binding.
- Returning `string[][]` snapshots a borrowed parameter, global, or record field before local cleanup. Returning an owned local transfers it to the caller; nested array structure is independent while immutable strings are shared.
- `copy(array)` and `array.copy()` return an independent mutable snapshot for `int[]`, `bool[]`, `string[]`, `int[][]`, and `string[][]`. Nested copies clone both array structure levels; immutable strings remain shared. Const sources are accepted, and the result can be mutated independently.
- Runtime arrays are heap-backed when mutation or runtime flow requires it. Helpers: `push`, `pop`, `insert`, `remove_at`, `clear`, `sort`, `map_to`, `filter`, and `flat_map`.
- Cleanup of inline owned array temporaries used as borrowed call arguments or method receivers is incomplete. Bind an array result to a local variable before querying it when cleanup matters.
- `filter` keeps the elements whose predicate returns `true` and returns a new array of the same item type.
- `prio_q<T>` is supported for runtime element types such as `int`, `bool`, `string`, enums, records, and arrays. Create one with `create_prio_q(values, comparator)` or UFCS form `values.create_prio_q(comparator)`, mutate it with `pq.push(value)`, test with `is_empty(pq)` or `pq.is_empty()`, and remove the highest-priority item with `pop(pq)` or `pq.pop()`. The queue copies the source array, so later mutations of the original array do not affect the queue.
- `fill(array, value)` and `array.fill(value)` replace every element in a mutable `int[]` or `bool[]`, preserve the array length, and return `void`. Empty arrays are unchanged. The value may be a constant or runtime `int` / `bool` matching the array element type. A user-defined function named `fill` takes precedence.
- There is currently no stdlib disjoint-set / union-find helper.
- `sort` is in-place and mutates the target array. It accepts either a named comparator function `int compare(T a, T b)` or an inline comparator lambda `(T a, T b) -> ...`, where negative means left-first, zero means equal, and positive means right-first.
- `map_to` transforms each element with a single-parameter lambda and returns a new array of the lambda result type. Prefer it over hand-written “create result, loop, push” helpers when one array maps directly to another.
- `flat_map` transforms each element into an array and flattens one level, so `T[]` can become `U[]` through a `T -> U[]` lambda.

9. Records and fields

- Access: `r.field`.
- Field writes and reads lower to runtime heap-backed record values when needed.
- Const record bindings allow field reads, including nested record fields and array-valued fields; the binding remains protected from direct field writes.
- Record names follow normal identifier rules, including lowercase and underscore-prefixed names.

10. Compile-time vs runtime evaluation

- Many helpers and expressions are folded at compile time when inputs are compile-time constants:
  - `to_int(...)`, `to_num(...)` resolve at compile time for constant string inputs.
  - `substring(...)`, `split(...)`, `trim()` may fold at compile time for constant strings.
- File IO is always runtime:
  - `read_lines(path)` always reads `path` when the compiled program runs.
  - `read_file(path)` always reads `path` when the compiled program runs.
  - `write_all(path, text)` always opens `path` with mode `w` and writes `text` without adding a newline.
  - The compiler emits the file path string, not the file contents, into the generated LLVM.
  - Missing `read_file` and `read_lines` inputs report the helper name and path and exit with status 1 when uncaught; inside a `try` block they can be caught as an exception. `write_all` raises the path when opening, writing, or closing fails, and an uncaught failure prints `write_all: <path>` and exits with status 1. After a successful open it closes the file once, including when writing fails.
  - `open(path)` opens a file for writing; use `read_file` and `read_lines` to read files. Call `close(file)` when finished. The `open`, `write_line`, `write_lines`, and `close` helpers do not consistently report open, write, or close failures.
- Const enforcement is compile-time and applies to the binding:
  - reassigning a `const` variable and direct writes through its array, map, set, or record target are rejected during compilation
  - known mutating array, set, and priority-queue operations through a `const` binding are rejected, including UFCS and free-function forms
  - const maps support the same read operations as mutable maps, including indexed value reads, key membership, and `keys()` / `values()`
  - passing a const value to an arbitrary user function does not make that function's parameters const
- When values are not known at compile time, corresponding operations lower to runtime helpers and library calls.
- Local declarations and reassignment transfer owned `int[]`, `bool[]`, `string[]`, `int[][]`, `string[][]`, map, and record temporaries. Assigning a managed local directly to itself preserves its existing value and ownership. Borrowed values keep their existing copy behavior, and reassignment to a different value releases the previous owned local value. Record fields of type `bool[]` are independent snapshots when constructed, replaced, or cloned; returning a bool-array field from a local record also returns an independent snapshot. Returning an owned local array or slice transfers it to the caller, including a const local.

11. Built-in calling and printing

- `print(...)` is provided by the standard library (resolved via `compiler/python/stdlib.py`), not a keyword.
- Integer printing uses `printf` with `%lld\n` via an emitted LLVM format string.
- Runtime string concatenation with `int` and `num` values is supported; the compiler automatically converts numeric values to strings when concatenating or printing. Explicit `to_string()` is also available for supported types.
- A runtime string concatenation produces an owned string value. Returning it transfers that value to the caller, while an unused result is released when its expression is dropped.

12. Error reporting

- Lexer and parser errors include exact line and column. Runtime errors print a diagnostic and exit non-zero when uncaught; the message format depends on the failing operation.
- The self-hosted compiler writes generated LLVM before resolving all foreign-module build metadata. A later metadata failure can leave LLVM in the requested output path, so output preservation is not guaranteed for every compiler failure.
- The `raylib` foreign module searches Homebrew roots under `/opt/homebrew/opt/raylib` and `/usr/local/opt/raylib`. Set `TB_RAYLIB_ROOT` to override discovery; the bundle does not include raylib or its external dependencies.

13. Standard library (stdlib) reference

The reference below lists supported standard library behavior and typical signatures.

Core IO and string helpers

- print(value) -> void
  - Print representation of `value` followed by newline. Works with `int`, `num`, `string`, `bool`, arrays and records (stringified).

- read_lines(path: string) -> string[]
  - Read an entire file and split into lines at runtime.

- read_file(path: string) -> string
  - Read the entire file contents at runtime and return them as one string.
  - Return file contents as a single string.

- split_lines(text: string) -> string[]
  - Split text efficiently at newline characters.

- write_all(path: string, text: string) -> void
  - The self-hosted compiler supports this helper. It overwrites or creates `path` at runtime, writing `text` exactly without adding a newline. Empty text creates or truncates the file to zero bytes.
  - Opening, writing, or closing failures raise `path`; an uncaught failure prints `write_all: <path>` and exits with status 1.
  - It borrows both strings, accepts const string bindings, and supports UFCS as `path.write_all(text)`. A user-defined function named `write_all` takes precedence over the builtin.

- open(path: string) -> file
  - Open a file handle for writing at runtime. Use `read_file` or `read_lines` for reads.

- write_line(f: file, line: string) -> void
  - Append `line` with a newline to the file handle.

- close(f: file) -> void
  - Close a file handle after writing. Output failures from opening, writing, and closing are not consistently reported.

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
  - Remove and return the last element. For `bool[]`, `pop(flags)` and `flags.pop()` return the last boolean and reduce the array length by one. Popping an empty `bool[]` returns `false` and leaves it empty. A user-defined function named `pop` takes precedence for `bool[]` calls.

- last(arr: T[]) -> T
  - Return the last element. Empty arrays still follow normal runtime bounds behavior.

- insert(arr: T[], index: int, value: T) -> void

- remove_at(arr: T[], index: int) -> T

- fill(arr: int[] | bool[], value: int | bool) -> void
  - Replace every existing element with `value`, preserving length. The value type must match the array element type. Also available as `arr.fill(value)`.

- copy(arr: int[] | bool[] | string[] | int[][] | string[][]) -> same array type
  - Return an independent mutable snapshot. Also available as `arr.copy()`.
  - Nested arrays copy their rows as well as the outer array; immutable strings may be shared.

- clear(arr: T[]) -> void
  - For `string[]`, clear releases owned strings in live slots and keeps the array storage available for reuse. Also available as `arr.clear()`.

- contains(arr: T[], value: T) -> bool
  - For `int[]`, `bool[]`, and `string[]`, return `true` when the array contains `value`. Also available via UFCS (`arr.contains(value)`) and membership syntax (`value in arr`). Queries borrow the array and item, preserve the array contents and length, and require the item type to match the array element type.

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

- sum(arr: int[] | bool[]) -> int
  - Aggregate helper for integer and boolean arrays. `true` contributes 1 and `false` contributes 0; empty arrays sum to 0. Runtime calls borrow the array and do not modify it. Constant arrays may be folded at compile time.

- abs(x: int | num) -> int | num — returns the value's magnitude and preserves a `num` value's decimal scale.
  - Runtime lowering supports both `int` and `num` values; `value.abs()` is also supported through UFCS.

- min(a: int | num, b: int | num) -> int | num
  - Return the smaller value. Runtime lowering supports same-type `int` and `num` operands; `num` keeps the selected operand's scale. Equal values select the right operand.

- max(a: int | num, b: int | num) -> int | num
  - Return the larger value. Runtime lowering supports same-type `int` and `num` operands; `num` keeps the selected operand's scale. Equal values select the right operand.
  - UFCS forms `a.min(b)` and `a.max(b)` are supported for `int` and `num`.

- sqrt(x: int | num) -> num
  - Return the square root as `num`. Constant inputs are folded at compile time.

Set and map helpers

- map literal syntax: `{'a': 1, 'b': 2}` in a typed context such as `map<string, int> counts = {'a': 1};`
- empty map literal: `map<string, int> counts = {};` The declared map type supplies the key and value types for local and global declarations, including `const map<string, int> counts = {};`, and when resetting an existing mutable typed map with `counts = {};`.
- `map<K, V>` supports cache-stringifiable keys such as `int`, `string`, arrays, and records with cache-stringifiable fields.
- map.keys() -> `K[]`
- map.values() -> `V[]`
- contains(map<K, V>, key: K) -> bool
  - Return `true` when `key` exists in the map, including keys whose values are zero or empty strings. Also available as `map.contains(key)`, `key in map`, and the inverse `key not in map`, for mutable and const maps. Empty maps and missing keys return `false`. Queries borrow the key and leave keys, values, and length unchanged; the query key must match the map key type.
- Set literals support cache-stringifiable complex values such as arrays and records, for example `set<Row> rows = {Row(1, 2)};`

Hashing, misc

- hash(v) -> int
  - Compute integer hash for `int`, `num`, `string` and arrays; UFCS sugar `v.hash()`.

- range(n) -> int[]
  - `range(end)` yields integers `0`..`end-1`.

- range(start, end) -> int[]
  - Yields `start`..`end-1`.

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
