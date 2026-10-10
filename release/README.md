# tb 0.2.0 standalone bundle

This bundle contains the self-hosted tb compiler and the LLVM helper templates
and C runtime sources it needs. `tb` compiles a `.tb` source file to LLVM IR.
`tb-build` also compiles and links that IR with Clang, including the bundled
thread runtime when the program uses thread pools.

## Requirements

- macOS and Apple's command line developer tools, including `clang`

The release packaging process verifies the host architecture before naming the
archive. macOS arm64 is the only configuration verified for this candidate;
an x86_64 archive is named for its architecture but has not been validated.
The bundle does not include foreign modules such as raylib or their external
dependencies.

The packager additionally uses `lipo`, `ditto`, and `shasum`; these are only
needed when creating an archive from the source checkout.

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
