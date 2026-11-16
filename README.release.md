# tb

tb is a small compiled programming language with an LLVM-based toolchain.

Release bundles contain the self-hosted compiler, native build launcher, LLVM
IR launcher, language reference (`tb.md`), changelog, license, and version. The
compiler reports its embedded version with `tb --version`. Python is not
required to use a bundle. Clang is required to build native programs.

The release provides macOS arm64 and Linux x86_64 bundles. The macOS bundle
targets macOS 26.0 or newer. Linux builds target x86_64.

## Download and Install

Replace `@VERSION@` in the commands with the release version. Verify the
archive checksum, then extract it.

On macOS arm64:

```sh
shasum -a 256 -c tb-@VERSION@-macos-arm64.zip.sha256
unzip tb-@VERSION@-macos-arm64.zip
cd tb-@VERSION@-macos-arm64
```

On Linux x86_64:

```sh
sha256sum -c tb-@VERSION@-linux-x86_64.tar.gz.sha256
tar -xzf tb-@VERSION@-linux-x86_64.tar.gz
cd tb-@VERSION@-linux-x86_64
```

## Quick Start

Compile and run a native program:

```sh
./tb path/to/program.tb -O2
path/to/program
```

By default, `tb` writes the executable beside the source, without `.tb`. Use
`-o` to choose another output path:

```sh
./tb path/to/program.tb -o ./program -O2
./program
./tb --version
```

To generate LLVM IR only:

```sh
./tb-ir path/to/program.tb output.ll
```

Threaded programs produce C runtime sources and linker metadata beside the LLVM
output. The `tb` launcher compiles and links these automatically. No
`TB_RESOURCE_ROOT` setting is needed. Input, import, and output paths are
interpreted from the current working directory.

External libraries such as raylib are not included. Set `TB_RAYLIB_ROOT` when
compiling a program that imports raylib. See `tb.md` for language details and
`CHANGELOG.md` for release notes.

## License

Apache License 2.0. See `LICENSE`.

Repository: https://github.com/torgnil/tb
