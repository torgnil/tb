# tb 0.2.0 standalone bundle

This bundle contains the self-hosted tb compiler and the LLVM helper templates
and C runtime sources it needs. `tb` compiles a `.tb` source file to LLVM IR.
`tb-build` also compiles and links that IR with Clang, including the bundled
thread runtime when the program uses thread pools.

## Requirements

- The installed bundle requires macOS and Apple's command line developer tools,
  including `clang`. Python is not needed to use an extracted bundle.
- The current candidate compiler targets macOS 26.0 or newer and has been
  verified on macOS 26.6.2 arm64. Earlier macOS versions and other
  architectures have not been validated.
- The source build and release verifier require Python 3.10 or newer, Git,
  `clang`, `ditto`,
  and `shasum`; packaging also uses Apple's `lipo`.

The release packaging process verifies the host architecture before naming the
archive. macOS arm64 is the only configuration verified for this candidate;
an x86_64 archive is named for its architecture but has not been validated.
The bundle does not include foreign modules such as raylib or their external
dependencies.

## Thread pools and futures

Programs may create an explicit `thread_pool` and submit a top-level named
function with no arguments or one argument. The argument and result types are
independent: each may be `int`, `bool`, `string`, `int[]`, or `int[][]`.
`await()` returns a result and rethrows a task exception; `is_done()` checks
completion, and `wait_for(milliseconds)` waits for a bounded duration without
consuming the result.

Strings are immutable and may be shared between workers. `int[]` and `int[][]`
arguments are copied when submitted, and array results are copied on each
`await()`. Records, maps, sets, priority queues, files, pools, futures, and
closures cannot cross the task boundary. Worker code does not synchronize
access to user globals or mutable containers. The scoped runtime-state audit,
concurrent stress, and lifetime checks for supported task values are complete
on macOS arm64; they do not establish safety for arbitrary user code or foreign
libraries. Native memoization tables protect their internal accesses, though
simultaneous cache misses may evaluate a body more than once and a full table
returns an uncached result. There is no promise of cancellation or work
stealing. A fixed-size pool can deadlock if every worker waits for work queued
to the same pool, and `wait_for` uses the system wall clock. Initialize globals
before starting tasks; if workers can read them, start work from `main` rather
than a global initializer.

Allocation failures are not handled uniformly, including task submission. An
exception that jumps across function frames can skip cleanup in those frames
and leak managed values or other owned resources. Catch inside the function
that owns resources when cleanup matters; normal return paths perform cleanup.
File output helpers close opened handles but do not consistently report open,
write, or close failures. Some self-hosted compiler errors while resolving
foreign-module build metadata can leave generated LLVM in the requested output
path. The bundle does not include raylib or its dependencies; set
`TB_RAYLIB_ROOT` to a raylib installation when compiling a program that imports
it. See the bundled language reference and changelog for details.

## Verify a source release

From a source checkout on the verified macOS arm64 host, run:

```sh
python3 verify_release_bundle.py --revision HEAD --version 0.2.0 \
  --evidence-dir /tmp/tb-release-verification
```

The verifier uses the selected Git tree to build the compiler, run the native
fixture suite, Python fixtures through phase 76, const checks, and package and
smoke-test an extracted bundle. Each run gets a separate manifest and process
logs under the evidence directory. It does not use a prebuilt checkout compiler
or untracked workspace files.

## Extract and verify

```sh
shasum -a 256 -c tb-0.2.0-macos-arm64.zip.sha256
ditto -x -k tb-0.2.0-macos-arm64.zip .
cd tb-0.2.0-macos-arm64
```

## Compile to LLVM IR

```sh
./tb path/to/program.tb path/to/program.ll
```

The source, imports, and output paths are interpreted from the current working
directory. The launcher locates resources beside itself, regardless of the
current directory or an inherited `TB_RESOURCE_ROOT` value.

The `read_file` and `read_lines` helpers report the helper name and missing path
and exit with status 1 when an input file cannot be opened and the error is
uncaught. Nonlocal exception transfer does not provide general cleanup for
skipped frames; catch inside the function that owns resources when cleanup is
needed.

## Build and run a native program

```sh
./tb-build path/to/program.tb path/to/program -O2
./path/to/program
```

A thread-pool program can submit a worker and await its result:

```tb
int worker(int value):
    return value + 1

int main(string[] args):
    thread_pool pool = thread_pool(2)
    future<int> result = pool.submit(worker, args.length())
    print(result.await())
```

Pass additional Clang arguments after the output path. Source, imports, and
output paths stay relative to the caller's current working directory. The
launcher generates LLVM in a temporary directory, then gives Clang the LLVM
module and each required runtime C source in one invocation. It leaves no build
files in the extracted bundle. Thread programs include the bundled runtime and
its pthread flags. The bundled [language reference](docs/tb.md) describes
supported syntax and runtime behavior. See [LICENSE](LICENSE) for licensing.

To use either command through `PATH`, set it to the extracted bundle directory:

```sh
export PATH="$PWD:$PATH"
tb path/to/program.tb path/to/program.ll
tb-build path/to/program.tb path/to/program
```
