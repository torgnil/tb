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
- map<K, V> — use `{}` or `{'key': value}` in a typed context such as `map<string, int> counts = {};`.
  - The native backend supports `int` and `string` keys. Map subscript reads and writes require the key expression to match `K`; assignments require the stored expression to match `V`. A bare empty `[]` assigned to an `int[]` or `string[]` map value, and a bare empty `{}` assigned to a map value, receive that value type from the target. A bare empty row inside a map literal also receives `int[]` or `string[]` when the literal initializes or reassigns a typed map, initializes or replaces a matching record map field, or is returned directly from a function declared to return one of `map<int, int[]>`, `map<string, int[]>`, `map<int, string[]>`, or `map<string, string[]>`. This applies to local and global declarations, including const maps. Const string and integer keys and const stored values use their underlying types for matching. Const maps support reads but cannot be mutated.
  - Native maps copy string keys on insertion, so keys remain valid if their source strings change or leave scope. A string used as both a key and a value keeps an independent map-owned reference for each role.
  - Owned string temporaries used as subscript keys are released after reads and writes. Compound updates keep an owned key alive through the read and final write, then release it once.
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
  A record constructor may share a name with a mutating builtin, such as `record pop(bool[] flags);`; passing a const array to that constructor is accepted and the record receives its normal array snapshot. The collision does not affect UFCS dispatch: `flags.pop()` and `words.pop()` still remove and return the last boolean or string, while `pop(flags)` constructs the record. A user-defined function named `pop` keeps its normal precedence.
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
- `pool.submit(work)` or `pool.submit(work, value)` queues a top-level named function and returns `future<T>` immediately. When a value is supplied, its type must match the worker's single parameter type. Passing a `const` binding uses its underlying value type.
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
- When an array, set, or map literal infers its type, const and mutable members with the same underlying type share one inferred type. For example, `[n, fixed]` infers `int[]` when `fixed` is `const int`, and `{key: fixed}` infers `map<string, int>` when `key` is `const string` and `fixed` is `const int`.
- Const still prevents writes through the source binding. A newly constructed container has its normal mutability and ownership behavior.
- Empty array literals are allowed in a typed context, for example `int[] nums = [];`, `string[] words = [];`, or `box.values = [];` when `values` is an array-valued record field. The field's declared array type determines the empty array's element type. In `int[][]` and `string[][]`, indexed row assignment also supplies that context, so `rows[0] = [];` creates an empty row of the matching element type.
- Empty rows in a typed nested array literal use the row element type, for example `int[][] rows = [[1], []];` creates an empty `int[]` row.
- Indexing: `arr[0]`, with negative indexing like `arr[-1]` (last element) supported for arrays and strings. Array and string subscript indices must have type `int`; const integer indices are accepted. Const strings support the same indexed reads as mutable strings; the selected character remains valid after the source binding leaves scope. For arrays, negative indices count from the end for both reads and writes: `arr[-length(arr)]` refers to the first element. A recognized owned `int[]` or `bool[]` temporary used only for a scalar indexed read is released after index normalization and the element read; named or otherwise reused receivers remain available. This cleanup currently covers scalar `int` and `bool` results, not indexed strings, rows, or records.
- Indexed assignment to `int[]`, `bool[]`, `string[]`, or an array of any declared record type, including a zero-field record, requires a value of the array's element type. Const values of the matching type are accepted.
- Slice notation with `[]` is supported for both arrays and strings. For example, `nums[1:3]` gives a subarray, and `text[2:5]` gives a substring. Open-ended, omitted-start, and negative-end slices are supported, e.g. `arr[1:]`, `text[:3]`, `text[:-1]`.
  - Every explicit slice bound must have type `int`. Const integers are accepted; values of other types produce a compiler diagnostic before LLVM generation.
  - Runtime slices of `int[][]` and `string[][]` copy the selected outer range and each row into an independent mutable result. This also works with const sources, so changing a selected row does not change the source. String values in copied rows may be shared because strings are immutable.
  - Negative start and end bounds count from the end before being clamped, following Python-style exclusive semantics. For example, `nums[-3:-1]` selects the middle two elements, and `nums[:-1]` drops the last element.
  - Example (array): `int[] nums = [1, 2, 3, 4]; int[] mid = nums[-3:-1];  // [2, 3]`
  - Runtime slices of `bool[]` also return independent mutable arrays, including when the source is const; changing either array leaves the other unchanged.
  - Runtime slices of `int[]` and `string[]` are owned independent arrays. Discarded slices release their storage, while returning a slice or storing it in a record transfers ownership without an extra snapshot. String elements retain their normal shared immutable values.
  - When an owned `int[]`, `bool[]`, `string[]`, `int[][]`, or `string[][]` temporary is used only as the source of a slice, the source is released after the slice has been created. The slice remains independently owned; named, borrowed, global, field, and otherwise reused sources remain available to their owners.
  - Example (string): `string s = 'hello'; string sub = s[1:4];  // 'ell'`
- Function-local `int[]` declarations and reassignment copy borrowed arrays, including const arrays, parameters, globals, indexed rows, and record fields. Mutating the copy leaves its source unchanged. Owned array literals and call results transfer into the local binding. Record construction and field replacement snapshot borrowed `int[]` arrays, and record cloning copies owned `int[]` fields; owned array temporaries transfer into the field. Returning an `int[]` field from a local record snapshots it before the record is released, while returning an owned local array transfers it directly to the caller.
- A named-comparator `int[]` sort result borrows its receiver. Assigning it back to that same local or parameter is redundant because `sort()` already mutates the receiver in place; the compiler keeps the receiver's current owner. Record-field replacement uses the normal array snapshot path. Indexed row replacement in `int[][]` and `string[][]` also snapshots a borrowed row before releasing the old slot, so forms such as `rows[i] = rows[i]` and `rows[i] = rows[i].sort(compare)` keep valid independent rows. The replacement row must have the matching `int[]` or `string[]` type; a bare empty literal such as `rows[i] = [];` receives that type from the target. Owned row literals and call results transfer into the slot.
- Function-local `bool[]` declarations and reassignment also copy borrowed arrays, including const arrays, parameters, globals, and record fields. Mutating the copy leaves its source unchanged. Owned array literals and call results transfer into the local binding.
- Native record-field replacement for `string`, `int[]`, `bool[]`, `string[]`, `int[][]`, `string[][]`, maps, and declared records with fields prepares a borrowed value according to its type-specific copy or retain behavior before releasing the old owned field. Managed strings are retained and unmanaged strings are copied; owned literals and call results transfer into the field. This keeps direct self-assignment valid. String elements inside copied arrays may share their immutable values.
- Function-local `string[][]` declarations and reassignment copy borrowed arrays by cloning the outer array and its child `string[]` arrays. Strings remain shared immutable values. Owned literals and call results transfer into the local binding.
- Function-local `int[][]` declarations and reassignment copy borrowed arrays by cloning the outer array and its child `int[]` arrays. Owned literals and call results transfer into the local binding.
- After an ordinary tb function call returns normally, the caller releases recognized owned `string`, `record`, `int[]`, `bool[]`, `string[]`, `int[][]`, or `string[][]` temporaries passed as arguments. String producers include concatenations and supported direct tb call or UFCS method results; recognized record producers are direct constructors, direct tb function calls, and ordinary user-defined UFCS methods returning a declared record; array producers include literals, supported slices, and existing supported tb call and method results. Cleanup applies to direct calls and UFCS calls that resolve to tb functions, including void calls and calls that return a scalar, record, string, or array. Borrowed locals, parameters, globals, and fields remain available to their owners. Record cleanup releases the record's owned fields. Returned values remain valid after argument cleanup, including a returned string that aliases its string argument and record or array results containing that argument. Record arrays are not included. A constructor call itself is outside this ordinary-call cleanup path. Recognized array method-result producers include `string.split()`, `split_lines()`, and supported array results from ordinary user-defined UFCS methods, in addition to existing map `keys()`/`values()` handling. Built-in `int[]` and record-array `sort()` results alias their receiver. A named-comparator built-in `int[] sort()` result is typed as borrowed even when a user function shares its name; binding or returning that result follows the normal `int[]` snapshot rules. Builtin and foreign calls and exceptional unwinding remain outside this cleanup path. Other inline temporaries used by builtins still need separate cleanup support.
- For native `int[]`, `bool[]`, and `string[]`, a recognized owned array temporary used only as the receiver of a scalar `contains(...)`, `index_of(...)`, `in`, or `not in` query is released after the query has read it. The boolean or index result remains available, and a managed string needle remains valid for later use. Named, borrowed, global, field, and otherwise reused arrays remain with their owners.
- Returning `int[][]` or `string[][]` snapshots a borrowed parameter, global, or record field before local cleanup. Returning an owned local transfers it to the caller; nested array structure is independent while immutable strings are shared.
- `copy(array)` and `array.copy()` return an independent mutable snapshot for `int[]`, `bool[]`, `string[]`, `int[][]`, and `string[][]`. Nested copies clone both array structure levels; immutable strings remain shared. Const sources are accepted, and the result can be mutated independently.
- A copied array can be queried or copied again in the same expression. For example, `make_values(seed).copy().sum()` sums a snapshot of an `int[]` result, and `flags.copy().sum()` counts the `true` values in a `bool[]` snapshot.
- Runtime arrays are heap-backed when mutation or runtime flow requires it. Helpers: `push`, `pop`, `insert`, `remove_at`, `clear`, `sort`, `map_to`, `filter`, and `flat_map`.
- `array.push(value)` requires exactly one value whose type matches the array element type. This is supported for `int[]`, `bool[]`, `string[]`, `int[][]`, `string[][]`, and arrays of any declared record type, including zero-field records; const values of the matching type are accepted. Array `push` resolves to the built-in method even when a user function has the same name; scalar and record-field UFCS calls can still resolve to a same-named user function.
- `filter` keeps the elements whose predicate returns `true` and returns a new array of the same item type.
- `prio_q<T>` is supported for runtime element types such as `int`, `bool`, `string`, enums, records, and arrays. Create one with `create_prio_q(values, comparator)` or UFCS form `values.create_prio_q(comparator)`, mutate it with `pq.push(value)`, test with `is_empty(pq)` or `pq.is_empty()`, and remove the highest-priority item with `pop(pq)` or `pq.pop()`. For native `int[]` and record-array queue methods, a named comparator must be an `int`-returning function with exactly two parameters matching the array element type, for example `int compare(int left, int right)`. Inline comparator lambdas remain supported. Invalid named comparators for those methods produce a compiler diagnostic before LLVM is passed to clang. The queue copies the source array, so later mutations of the original array do not affect the queue.
- `fill(array, value)` and `array.fill(value)` replace every element in a mutable `int[]`, `bool[]`, or `string[]`, preserve the array length, and return `void`. For mutable `int[][]` and `string[][]`, the value is an `int[]` or `string[]` copied independently into every row; later row or source changes do not affect the others. Empty outer arrays are unchanged, and typed empty rows are supported. Const scalar and row values are accepted, while const array receivers cannot be mutated. String values retain their immutable text safely, including when the value aliases an array element being replaced. A user-defined function named `fill` takes precedence.
- There is currently no stdlib disjoint-set / union-find helper.
- `sort` is in-place and mutates the target array. It accepts either a named comparator function `int compare(T a, T b)` or an inline comparator lambda `(T a, T b) -> ...`, where negative means left-first, zero means equal, and positive means right-first.
- `map_to` transforms each element with a single-parameter lambda and returns a new array of the lambda result type. Prefer it over hand-written “create result, loop, push” helpers when one array maps directly to another.
- `flat_map` transforms each element into an array and flattens one level, so `T[]` can become `U[]` through a `T -> U[]` lambda.

9. Records and fields

- Access: `r.field`.
- Field writes and reads lower to runtime heap-backed record values when needed.
- Assignments to fields declared as `int`, `bool`, `num`, `string`, `int[]`, `bool[]`, `string[]`, `int[][]`, `string[][]`, maps, or any declared record type require a matching value type; const-qualified values are accepted. A bare empty array assigned to an array field receives the field's declared type.
- Declared record fields support `int[]`, `bool[]`, `string[]`, `int[][]`, and `string[][]`; declaring a record emits the runtime helpers needed by those fields even when no instance is constructed.
- Global record initializers support `int[]`, `bool[]`, `string[]`, `int[][]`, and `string[][]` fields, including nested record fields. Their runtime initializers run before `main`; globals keep process lifetime.
- Record construction, cloning, and field replacement snapshot borrowed `int[][]` and `string[][]` values, including when a field is assigned to itself. Nested array structure is independent; immutable strings remain shared. Owned array temporaries transfer into fields.
- Const record bindings allow field reads, including nested record fields and array-valued fields; the binding remains protected from direct field writes.
- Record names follow normal identifier rules, including lowercase and underscore-prefixed names.

10. Compile-time vs runtime evaluation

- Many helpers and expressions are folded at compile time when inputs are compile-time constants:
  - `to_int(...)`, `to_num(...)` resolve at compile time for constant string inputs.
  - `substring(...)`, `split(...)`, `trim()` may fold at compile time for constant strings.
  - Record string fields that depend on runtime values are evaluated at runtime, including repeated reconstruction such as `box = Box(box.text);`.
  - Nested record fields that depend on runtime values remain runtime values when their containing records are repeatedly reconstructed, including field reads through function parameters.
  - Integer and boolean record fields that depend on their own prior runtime values, including repeated reconstruction, remain runtime values. Acyclic scalar expressions continue to fold after such values are evaluated.
- File IO is always runtime:
  - `read_lines(path)` always reads `path` when the compiled program runs.
  - `read_file(path)` always reads `path` when the compiled program runs.
  - `write_all(path, text)` always opens `path` with mode `w` and writes `text` without adding a newline.
  - The compiler emits the file path string, not the file contents, into the generated LLVM.
  - Missing `read_file` and `read_lines` inputs report the helper name and path and exit with status 1 when uncaught; inside a `try` block they can be caught as an exception. `write_all` raises the path when opening, writing, or closing fails, and an uncaught failure prints `write_all: <path>` and exits with status 1. After a successful open it closes the file once, including when writing fails.
  - `open(path)` opens a file for writing and raises the path if opening fails; an uncaught failure prints `open: <path>` and exits with status 1. Use `read_file` and `read_lines` to read files. Call `close(file)` when finished. The `write_line`, `write_lines`, and `close` helpers do not consistently report write or close failures.
- Const enforcement is compile-time and applies to the binding:
  - reassigning a `const` variable and direct writes through its array, map, set, or record target are rejected during compilation
  - known mutating array, set, and priority-queue operations through a `const` binding are rejected, including UFCS and free-function forms
  - const maps support the same read operations as mutable maps, including indexed value reads, key membership, and `keys()` / `values()`
  - passing a const value to an arbitrary user function does not make that function's parameters const
- When values are not known at compile time, corresponding operations lower to runtime helpers and library calls.
- Local declarations and reassignment transfer owned `int[]`, `bool[]`, `string[]`, `int[][]`, `string[][]`, map, and record temporaries. Assigning a managed local directly to itself preserves its existing value and ownership. Borrowed values keep their existing copy behavior, and reassignment to a different value releases the previous owned local value. Record fields of type `bool[]`, `int[][]`, and `string[][]` are independent snapshots when constructed, replaced, or cloned. Returning a `bool[]`, `int[][]`, or `string[][]` field from a local record also returns an independent snapshot. Returning an owned local array or slice transfers it to the caller, including a const local.
- Results from `string.split()` and `split_lines()` and array values returned by ordinary user-defined UFCS methods are owned. They transfer when stored, returned, or inserted into nested arrays, and release when dropped or borrowed by a normal user function call. Built-in `int[]` and record-array `sort()` operations mutate and return their receiver.

11. Built-in calling and printing

- `print(...)` is provided by the standard library (resolved via `compiler/python/stdlib.py`), not a keyword.
- Integer printing uses `printf` with `%lld\n` via an emitted LLVM format string.
- Runtime string concatenation with `int` and `num` values is supported; the compiler automatically converts numeric values to strings when concatenating or printing. Explicit `to_string()` is also available for supported types.
- A runtime string concatenation produces an owned string value. The compiler releases owned string operands after copying their text into the independent result; borrowed operands remain available to their owners. Returning the result transfers it to the caller, while an unused result is released when its expression is dropped.

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
  - Open a file handle for writing at runtime. If opening fails, raise `path`; an uncaught failure prints `open: <path>` and exits with status 1. Use `read_file` or `read_lines` for reads.

- write_line(f: file, line: string) -> void
  - Append `line` with a newline to the file handle.

- close(f: file) -> void
  - Close a file handle after writing. Failures from writing with `write_line` or `write_lines`, and failures from closing, are not consistently reported.

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
  - Return the last byte-character as a single-character string, or `''` for the empty string. Both `last(s)` and `s.last()` are supported for runtime and const strings; Unicode codepoint handling is not provided.

- replace(s: string, old: string, new: string) -> string
  - Replace occurrences of `old` with `new`.

- join(arr: string[], sep: string) -> string
  - Join array elements with `sep`.

Array helpers

- length(x: T[] | string | map) -> int
  - Return length of array, string, set, or `map<string, int>`.

- push(arr: T[], value: T) -> void
  - Append `value` to `arr` (may cause runtime heap-backed array representation).
  - Works for nested `int[][]` and `string[][]` arrays, for example `int[][] rows = []; rows.push([1, 2]);` or `string[][] rows = []; string[] row = []; rows.push(row);`. Typed empty rows are supported. Pushing a borrowed row stores an independent row snapshot; an owned row literal or call result transfers into the outer array.

- pop(arr: T[]) -> T
  - Remove and return the last element. For `bool[]`, `pop(flags)` and `flags.pop()` return the last boolean and reduce the array length by one. Popping an empty `bool[]` returns `false` and leaves it empty. For `string[]`, both forms return the last string; popping an empty array returns an empty string. The popped value remains valid after the array is cleared or reused. A sole-use owned inline `bool[]` or `string[]` receiver is released after `pop()` returns; named and reused receivers remain available to their owners. A user-defined function named `pop` takes precedence for direct and UFCS calls. A lowercase `pop` record constructor takes precedence for `pop(words)` while `words.pop()` still invokes the builtin.
  - For `int[]`, popping an empty array returns `0` and leaves it empty. An owned inline receiver used only by `pop()` is released after the integer result is read; named and reused receivers remain available to their owners. A direct call continues to resolve to a matching user function or lowercase `pop` record; use `values.pop()` to invoke the array method.
  - For `int[][]` and `string[][]`, `pop(rows)` and `rows.pop()` remove and return the last mutable row. An owned row transfers to the caller; a borrowed row is copied before removal. Popping an empty outer array returns a new typed empty row and leaves the outer array empty. The returned row remains usable after the array is destroyed. A lowercase `pop` record remains a direct-call constructor, while `rows.pop()` invokes the array method. Results from nested-array `pop()` are owned: storing, returning, inserting, or passing them to a normal tb function transfers or releases the row through the usual array ownership rules. A popped row used only by a scalar query such as `rows.pop().sum()`, `rows.pop().length()`, or `rows.pop().is_empty()` is released after that query. An inline owned `bool[]`, `string[]`, `int[]`, `int[][]`, or `string[][]` receiver used only by `pop()` is released after the element has been detached; named and reused receivers remain available to their owners.

- last(arr: T[]) -> T
  - For native `int[]` and `bool[]`, return the last element without changing the array. For `string[]`, return an independent string copy of the last element without changing the array; the copy remains valid after the source slot is popped or the array is cleared or destroyed. Also available as `arr.last()`, including for const arrays. Calling either form on an empty array aborts before reading an element.
  - For `int[][]` and `string[][]`, return an independent mutable copy of the last row. The outer array is unchanged, and an empty selected row is valid. Calling either form on an empty outer array aborts before reading an element; immutable strings in a copied `string[]` row may be shared.
  - A recognized owned native-array temporary used only as the direct or UFCS receiver is released after `last` has produced its result. Named or reused arrays remain available, and string receivers keep their existing lifetime behavior.

- insert(arr: T[], index: int, value: T) -> int for `int[]`; `void` for `bool[]` and `string[]`
  - For native `int[]`, `bool[]`, and `string[]` method calls such as `arr.insert(index, value)`, insertion shifts the selected element and later values right. The full signed 64-bit index is used: negative indices clamp to the start, and indices past the end append. Inserting at the last occupied index preserves that element in the new final slot. For `int[]`, `values.insert(index, value)` requires an `int` index and `int` value and returns the new array length. For `bool[]`, the value must be `bool`; for `string[]`, `words.insert(index, value)` accepts an `int` index and `string` value. Those methods return `void` and follow the same clamping and shifting rules. Borrowed strings are retained before mutation; owned string temporaries transfer into the array. The `int[]` method call uses the builtin even when a same-named user function exists; `bool[]` and `string[]` user-defined `insert` functions retain precedence for UFCS calls. A record named `insert` remains a direct-call constructor.

- remove_at(arr: T[], index: int) -> T
  - For native `int[]` and `bool[]` method calls, the full signed 64-bit index is used. Remove the selected value, shift later values left, and return the removed value. Negative and past-end indices return `0` for `int[]` or `false` for `bool[]` without changing the array.
  - A recognized owned `int[]` or `bool[]` temporary used only as the method receiver is released after the scalar result is read; named, borrowed, global, record-field, or reused arrays remain with their owners. Empty arrays and invalid indices keep their existing default results.
  - The `int[]` builtin requires one `int` index and takes precedence over a same-named user function for method calls.
  - For `string[]`, `words.remove_at(index)` removes and returns the selected string, shifting later values left. The index must be an `int`; negative and out-of-range indices, including on an empty array, return an owned empty string without changing the array. The returned string remains valid after the source is cleared or reused. Owned slots transfer their string; borrowed slots return an independent copy. A recognized owned array temporary used only as the receiver is released after the string has been detached, including on invalid or empty calls. Named, borrowed, global, record-field, or reused arrays remain with their owners. A user-defined `remove_at` function takes precedence for `bool[]` and `string[]` UFCS calls; the `int[]` builtin keeps its native method precedence, while a record named `remove_at` remains a direct-call constructor and does not replace an array method.

- fill(arr, value) -> void for matching pairs: `int[]`/`int`, `bool[]`/`bool`, `string[]`/`string`, `int[][]`/`int[]`, or `string[][]`/`string[]`.
  - Replace every existing element with `value`, preserving length. The value type must match the array element type. Also available as `arr.fill(value)`.

- copy(arr: int[] | bool[] | string[] | int[][] | string[][]) -> same array type
  - Return an independent mutable snapshot. Also available as `arr.copy()`.
  - Nested arrays copy their rows as well as the outer array; immutable strings may be shared.

- clear(arr: T[]) -> void
  - For `string[]`, clear releases owned strings in live slots and keeps the array storage available for reuse. For `bool[]`, it sets the live length to zero and keeps the array available for reuse. Also available as `arr.clear()`.
  - For `int[][]` and `string[][]`, clear releases owned live rows, preserves borrowed rows, clears the outer slots, and sets the outer length to zero while keeping its storage available for reuse. Also available as `rows.clear()`. A user-defined `clear` function takes precedence for direct and UFCS calls; a lowercase `clear` record remains a direct-call constructor while `rows.clear()` uses the builtin.

- contains(arr: T[], value: T) -> bool
  - For `int[]`, `bool[]`, and `string[]`, return `true` when the array contains `value`. Also available via UFCS (`arr.contains(value)`) and membership syntax (`value in arr`). Queries borrow the array and item, preserve the array contents and length, and require the item type to match the array element type.

- index_of(arr: T[], value: T) -> int
  - For `int[]`, `bool[]`, and `string[]`, return the first matching zero-based index or `-1` when no item matches. Also available via UFCS (`arr.index_of(value)`). String items compare by content. Queries borrow the array and item, preserve the array contents and length, and require the item type to match the array element type.

- is_empty(x: string | T[] | set<T> | map<K, V> | prio_q<T>) -> bool
  - Return `true` when the value has no items. UFCS sugar such as `arr.is_empty()` and `scores.is_empty()` is supported.
  - For native `int[]`, `bool[]`, `string[]`, `int[][]`, and `string[][]`, array `length` and `is_empty` queries borrow their receiver. A recognized owned array expression used only for the query is released after the result is computed; a named array remains available for later use.

- sort(arr: T[], compare: (T, T) -> int) -> void
  - Sort the array in place using the provided comparator.
  - Native `int[]` and record-array sort methods require one comparator. A named comparator must resolve to a function returning `int` with exactly two parameters matching the array element type, such as `int compare(int a, int b)`. An inline lambda such as `(int a, int b) -> a - b` is also supported.
  - Invalid named comparators for those native array sort methods produce a compiler diagnostic. Scalar functions named `sort` keep normal method-call dispatch, for example `value.sort()` can call `int sort(int value)`.

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
  - Aggregate helper for integer and boolean arrays. `true` contributes 1 and `false` contributes 0; empty arrays sum to 0. Runtime calls borrow the array and do not modify it. Constant arrays may be folded at compile time. A recognized owned array temporary used only by a direct or UFCS sum query is released after the scalar result is computed; named or reused arrays remain available.
  - When a lowercase record named `sum` is declared, direct `sum(value)` calls construct that record, including when `value` is an `int[]` or `bool[]`. UFCS calls such as `values.sum()` and `flags.sum()` remain native array aggregation. Without a `sum` record, direct `sum(array)` keeps native builtin precedence over a same-named user function.

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
- In a typed map literal, the declared map value type also supplies the full type of a bare empty map entry. For example, `map<int, map<string, int>> groups = {1: {}, 2: {'leaf': 3}};` creates an empty `map<string, int>` at key `1`; it can be populated after insertion. This works in typed local and global declarations, reassignment, record construction and field replacement, and direct map-literal returns. Populated entry maps still need to match the declared value type.
- For native `map<int, int[]>`, `map<string, int[]>`, `map<int, string[]>`, and `map<string, string[]>` returns, the declared return type supplies the row type for bare empty array values in a direct map literal. For example, a function returning `map<int, string[]>` may return `{seed: [], seed + 1: ['row']}` with both empty and populated rows.
- empty map literal: `map<string, int> counts = {};` The declared map type supplies the key and value types for local and global declarations, including `const map<string, int> counts = {};`, and when resetting an existing mutable typed map with `counts = {};`. A record field declaration also supplies the type for a bare empty map passed directly to that record's constructor or assigned to an existing mutable map field, such as `Box box = Box({});` and `box.counts = {};`. A direct `return {};` in a function returning a native map also uses its declared return type. This includes maps with `int` or `string` keys and scalar, array, nested-map, or record values supported by the native backend.
- When assigning through a map subscript, the declared map value type supplies the type of a bare empty `[]` for `int[]` and `string[]` values, or a bare empty `{}` for map values. For example, `rows['row'] = [];` works for `map<string, int[]> rows`, and `groups[key] = {};` works when the map value is itself a map. The empty literal must be the direct assignment value; populated literals and other expressions still need a matching type.
- `map<K, V>` supports cache-stringifiable keys such as `int`, `string`, arrays, and records with cache-stringifiable fields; the native backend currently supports `int` and `string` subscript keys.
- Native maps with `int[]` values snapshot borrowed arrays when values are inserted by literal or subscript assignment, and transfer owned literals and call results into the map. Map copies clone those arrays, and replacing a stored value releases its previous owned array after preparing the replacement. For native `map<int, int[]>` and `map<string, int[]>`, `values()` returns an owned `int[][]` snapshot in map insertion order. Each row is an independent mutable copy, including for const maps; updating a key keeps its existing position. Empty typed maps return a valid empty `int[][]`. Native `map<int, string[]>` and `map<string, string[]>` return an owned, independent mutable `string[][]` snapshot in insertion order. Each row is copied and its immutable managed strings remain valid independently of the map. Empty and const maps work, and updating a key keeps its original position. Native `map<int, bool>` and `map<string, bool>` return an owned, independent mutable `bool[]` snapshot in insertion order, including for const and empty maps. Updating a key keeps its original position. For an `int[][]` or `string[][]` result, bind it before indexing a row, for example `int[][] rows = counts.values(); print(rows[0][0]);`; a `bool[]` result can be indexed directly.
- For `map<int, bool>`, `map<int, string>`, `map<int, int[]>`, `map<int, string[]>`, and maps whose values are maps, a repeated integer key replaces its value with the last value while keeping the key's first insertion position. This applies to mutable, const, and global literals. Each value expression is still evaluated. Map-valued maps support duplicate replacement and normal map ownership, but do not gain `values()` enumeration for their nested maps.
- map.keys() -> `K[]`
- map.values() -> `V[]`
  - For the native `map<int, int[]>` and `map<string, int[]>` forms, this returns owned `int[][]` snapshots in insertion order. For native `map<int, string[]>` and `map<string, string[]>`, this returns owned `string[][]` snapshots; each mutable row is copied, while its immutable managed strings remain valid independently of the map. For native `map<int, bool>` and `map<string, bool>`, it returns an owned `bool[]` snapshot in insertion order. These forms support const and empty maps, and later map or snapshot mutations do not affect the other. Other map value families keep their existing behavior.
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
