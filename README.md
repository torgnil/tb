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

## Build

Build the self-hosted compiler:

```bash
./build_tb.sh
```

Compile a tb program with the self-hosted compiler:

```bash
./tb.sh path/to/program.tb
```

`bin/tb` loads LLVM helper templates and thread runtime sources from the
checkout-relative paths under `compiler/tb`. Set `TB_RESOURCE_ROOT` when those
resources live elsewhere; the directory must contain the same `compiler/tb`
subdirectories. `tb.sh` sets this to the checkout by default and accepts an
override:

```bash
TB_RESOURCE_ROOT="/path/to/resource tree" ./tb.sh /path/to/program.tb
```

For direct `bin/tb` calls, the resource setting does not change compiler input,
import, or output path handling. When `TB_RESOURCE_ROOT` is unset or empty, the
self-hosted compiler keeps its historical relative-resource lookup behavior.

Bootstrap path using the Python compiler:

```bash
python3 compiler/python/tb.py input.tb output.ll
clang output.ll -o program
```

## Standalone release bundle

On macOS, build the self-hosted compiler and package a versioned bundle without
including files from the local untracked workspace:

```bash
./build_tb.sh
./bundle_release.sh 0.2.0
```

The archive is written to `.build/releases/`. The bundle contains the compiler,
its LLVM helpers and thread runtime sources, the language reference, and native
build launcher. See [release/README.md](release/README.md) for extraction,
checksum, and use instructions. Only macOS arm64 is currently verified.

To reproduce the build, test, and bundle checks from a source revision on a
verified macOS arm64 host, run:

```bash
python3 verify_release_bundle.py --revision HEAD --version 0.2.0 \
  --evidence-dir /tmp/tb-release-verification
```

The verifier archives the selected Git tree into a fresh directory, builds the
self-hosted compiler there, runs the native and Python fixture suites and const
checks, then builds and tests an extracted bundle. It writes a separate
manifest and process logs for each run under the evidence directory. It uses
tracked files from the selected revision; local binaries and untracked files do
not participate. The required tools and installed-bundle requirements are
listed in [release/README.md](release/README.md).

For the focused thread-pool queue, shutdown, future, and ownership audit, run
the checkout-only verifier:

```bash
python3 verify_thread_pool_lifecycle.py --compiler bin/tb --mode focused \
  --seed 7 --evidence-dir /tmp/tb-pool-lifecycle
```

Use `--mode all` for O0/O2, AddressSanitizer, ten ThreadSanitizer rounds, and
the known-bad controls. The source inventory and limits are documented in
[docs/thread_runtime_safety.md](docs/thread_runtime_safety.md).

## Documentation

- language reference: `docs/tb.md`
- sample programs: `examples/aoc`
- changelog: `CHANGELOG.md`

## Status

### Supported

- Compiling tb programs to LLVM IR with the Python compiler
- Building and using the self-hosted tb compiler
- Native numbered fixtures through `tests/fixtures/164.tb`
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
  worker tasks. Broader runtime-state audits, concurrent stress, and lifetime
  checks remain open; release readiness is not yet established.

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
