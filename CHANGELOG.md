# Changelog

All notable changes to tb will be documented in this file.

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
