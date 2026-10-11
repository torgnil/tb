# tb

tb is a small compiled programming language with an LLVM-based toolchain.

This repository contains:
- the Python compiler
- the self-hosted tb compiler
- the language reference
- fixtures and sample programs

Current highlights:
- native code generation through LLVM IR
- working self-hosted compiler build path
- core language support for strings, arrays, records, enums, maps, sets, slices, and exceptions
- explicit thread pools and futures for the task types described in the
  [language reference](docs/tb.md)
- built-in foreign module support for `raylib`

## Installation

Install on macOS with [Homebrew](https://brew.sh):

```bash
brew install torgnil/tap/tb
```

Build and run a native executable:

```bash
tb path/to/program.tb -O2
path/to/program
```

`tb` writes the executable beside the source, without the `.tb` extension.
Use `-o` to choose an output path, for example
`tb path/to/program.tb -o ./program -O2`. Native builds require `clang` and
platform headers from Apple's command line developer tools. Required tb thread
runtime sources are compiled and linked automatically.

To generate LLVM IR without linking:

```bash
tb-ir path/to/program.tb output.ll
```

## Build from source

Build the self-hosted compiler:

```bash
./build_tb.sh
```

Check the compiler version with `bin/tb --version`. Builds embed the version
and default to `dev`. For a release or Homebrew source build, specify the
version once at build time, for example `TB_VERSION=0.2.1 ./build_tb.sh`.

Compile a tb program with the self-hosted compiler:

```bash
./tb.sh path/to/program.tb
```

`build_tb.sh` embeds the LLVM helper templates and C thread runtime into `bin/tb`.
The editable sources remain under `compiler/tb/llvm_helpers` and
`compiler/tb/runtime`; rebuild the compiler after changing them. The generated
`compiler/tb/llvm_helpers_generated.tb` module is an ignored build artifact.
The resulting compiler needs no external tb runtime source files or
`TB_RESOURCE_ROOT` setting when compiling other tb programs.

When a threaded program is compiled to `output.ll`, the compiler also writes
`output.ll.thread_pool_runtime.c` and `output.ll.thread_pool_composite_runtime.c`.
These generated files include their required header declarations. The `.csources`,
`.cflags`, and `.linkflags` metadata describe how to compile and link them;
`tb.sh` handles this automatically. Clang and platform headers are still required.
Use an explicit LLVM output path when compiling threaded programs so these files
and the metadata are generated.

Bootstrap path using the Python compiler:

```bash
python3 compiler/python/tb.py input.tb output.ll
clang output.ll -o program
```

## Documentation

- language reference: `docs/tb.md`
- sample programs: `examples/aoc`
- changelog: `CHANGELOG.md`
- editor syntax highlighting: [TextMate bundle and grammar](editors/README.md)

## Status

### Supported

- Compiling tb programs to LLVM IR with the Python compiler
- Building and using the self-hosted tb compiler
- Native numbered fixtures through `tests/fixtures/165.tb`
- Python compiler fixtures through phase 76; this is a separate suite from the
  native numbered fixtures
- The current AoC sample set in `examples/aoc`
- Stage 2 and stage 3 self-hosting on the current verified path
- The bundled `raylib` demo path when its external raylib dependencies are
  installed; those dependencies are not part of the standalone bundle

### Experimental

- Broader foreign-module architecture beyond the current bundled `raylib` slice
- Exact stage-2 vs stage-3 LLVM text equivalence policy
- Performance tuning beyond the current measured self-hosting path

### Known Limitations

- Stage-2 self-compile memory usage is still higher than we want
- Stage-3 self-compile throughput is still slower than we want
- Backend string allocation churn is still high even after the major memory improvements
- User globals and mutable containers are not synchronized when accessed by
  worker tasks. Use explicit coordination for shared mutable state.
- Only top-level named workers with the documented argument and result types
  may cross a task boundary. Submission and general allocation failures are
  not handled uniformly. A nonlocal exception can skip cleanup in intervening
  function frames and leak managed values or other owned resources; catch inside
  the function that owns resources when cleanup matters.
- Do not start tasks from global initializers when they may read globals that
  have not finished initializing. Initialize shared state and start work from
  `main`.
- Fixed-size pools can deadlock when every worker waits for more work queued to
  the same pool. `wait_for` uses the system wall clock, which can change.
- The self-hosted compiler does not make output generation transactional. Some
  failures while resolving foreign-module build metadata can leave generated
  LLVM in the requested output path. `open`, `write_line`, and `close` also do
  not consistently report file output failures.
- Foreign modules such as raylib require their external dependencies; set
  `TB_RAYLIB_ROOT` to a raylib installation when compiling programs that import
  it.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
