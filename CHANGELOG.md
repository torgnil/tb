# Changelog

All notable changes to tb will be documented in this file.

## [0.2.0] - Unreleased

### Added
- Explicit thread pools and futures for top-level named worker functions.
- Worker functions may take zero arguments or one argument of type `int`,
  `bool`, `string`, `int[]`, or `int[][]`. Results may independently use any of
  those five types.
- Futures provide `await()`, `is_done()`, and `wait_for(milliseconds)`.
- Worker exceptions are rethrown by `await()`. Managed string arguments and
  results are shared as immutable values, while `int[]` and `int[][]` cross the
  task boundary as snapshots; each array result await returns a fresh snapshot.
- Native cached functions synchronize memo-table access for the supported key
  types. Simultaneous misses may evaluate the function more than once; a full
  table returns an uncached result.
- A standalone macOS arm64 compiler bundle and source-tree release verifier.

### Limitations
- Records, maps, sets, priority queues, files, pools, futures, and closures are
  not supported as task arguments or results. Only top-level named functions
  with the signatures above can be submitted.
- Worker threads do not synchronize user globals or mutable containers shared
  by task code. Broader runtime-state audit, stress, and lifetime verification
  remains open; this candidate is not declared ready to release.
- The standalone bundle has been verified on macOS arm64. macOS x86_64 has not
  been validated, and external `raylib` dependencies are not included.

See [README.md](README.md) for bundle requirements and use, and
[docs/tb.md](docs/tb.md) for the detailed thread-pool language reference.

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
