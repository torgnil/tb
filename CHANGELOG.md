# Changelog

All notable changes to tb will be documented in this file.

## [0.2.1] - 2026-10-11

### Added
- Independent array copies with `copy(array)` and `array.copy()` for `int[]`,
  `bool[]`, `string[]`, `int[][]`, and `string[][]`.
- In-place `fill` for those array types, including safe string replacement and
  independent copies of nested rows.
- Runtime `bool[]` slices, `pop`, `insert`, `remove_at`, and `clear`.
- Pushing rows into `string[][]`, including typed empty rows.
- Global record initializers with array-valued fields, including nested arrays
  and nested records.
- Checked runtime `write_all(path, text)` and its UFCS form.
- A TextMate syntax-highlighting bundle for IntelliJ and other compatible editors.
- Compiler version reporting with `--version` and Homebrew installation
  instructions (`brew install torgnil/tap/tb`).

### Changed
- Release `tb` builds a native executable, matching the repository's `tb.sh`
  workflow. `tb-ir` emits LLVM IR; it replaces the former release `tb` command,
  and the separate `tb-build` launcher has been removed.
- LLVM helpers and thread runtime sources are embedded in the compiler.
- `TB_VERSION` sets the embedded version at build time; unspecified builds
  report `dev`. Bundle names and version metadata use the embedded version.

### Fixed
- Negative array slice bounds now count from the end before clamping.
- Array insertion preserves the previous final element. Integer and boolean
  positional edits validate the full signed 64-bit index before narrowing it.
- Lowercase and underscore-prefixed record constructors infer their types
  correctly. Record names that collide with `pop` preserve constructor and
  builtin method dispatch, including const-array constructor arguments.
- Unused record declarations with array fields include their required helpers.
- Line comments ignore embedded quote and block-comment delimiters.
- Managed locals are released when `main` falls through. Owned array slices
  and intermediate string-concatenation operands are released on the supported
  normal cleanup paths.

See [docs/tb.md](docs/tb.md) for supported behavior and remaining limitations.

## [0.2.0]

### Added
- Explicit thread pools and futures for top-level named worker functions.
- Worker functions may take zero arguments or one argument of type `int`,
  `bool`, `string`, `int[]`, or `int[][]`. Results may independently use any of
  those five types.
- Futures provide `await()`, `is_done()`, and `wait_for(milliseconds)`.
- Worker exceptions are rethrown by `await()`. Managed string arguments and
  results are shared as immutable values, while `int[]` and `int[][]` cross the
  task boundary as snapshots; each array result await returns a fresh snapshot.
- Missing runtime input files passed to `read_file` or `read_lines` report the
  helper name and path, then exit non-zero when uncaught.
- Native cached functions synchronize memo-table access for the supported key
  types. Simultaneous misses may evaluate the function more than once; a full
  table returns an uncached result.
- A standalone macOS arm64 compiler bundle.

### Limitations
- Records, maps, sets, priority queues, files, pools, futures, and closures are
  not supported as task arguments or results. Only top-level named functions
  with the signatures above can be submitted.
- Worker threads do not synchronize user globals or mutable containers shared
  by task code. The scoped runtime-state audit, concurrency stress, and lifetime
  checks for supported task values are complete on macOS arm64; they do not
  cover arbitrary user code or foreign libraries. Initialize globals before
  starting tasks, and start work from `main` rather than a global initializer
  if workers can read those globals.
- Allocation failures are not handled uniformly, including task submission.
  Exceptions that jump across function frames can skip cleanup in those frames
  and leak managed values or other owned resources. Catch inside the function
  that owns resources when cleanup matters; normal return paths perform cleanup.
- A fixed-size pool can deadlock if every worker waits for work queued to the
  same pool. `wait_for` uses the system wall clock, so clock adjustments can
  affect its elapsed duration.
- File output helpers close opened handles, but do not consistently report
  failures from opening, writing, or closing files. Some self-hosted compiler
  errors while resolving foreign-module build metadata can leave generated LLVM
  in the output path.
- The current candidate compiler targets macOS 26.0 or newer and has been
  verified on macOS 26.6.2 arm64. Other macOS versions and architectures have
  not been validated. External `raylib` dependencies are not included; set
  `TB_RAYLIB_ROOT` to a raylib installation when compiling a program that
  imports it.

See [docs/tb.md](docs/tb.md) for the detailed thread-pool language reference.

## [0.1.0] - 2026-06-20

### Added
- Initial public release of the tb language and compiler.
- Python compiler pipeline for compiling tb source to LLVM IR.
- Self-hosted tb compiler build path.
- Core language support for:
  - `int`, `bool`, `string`
  - arrays, records, enums, sets, and maps
  - functions, control flow, exceptions, and slices
- End-to-end numbered fixture suite.
- Built-in foreign module support for `raylib`.
- Sample Advent of Code programs.


### Notes
- Compiler performance work is still ongoing, especially in backend throughput and string-allocation churn.
