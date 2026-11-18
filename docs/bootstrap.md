# Bootstrap guide

## Build the current checkout

The compiler builds itself from a released native `tb` compiler. The current
seed is `tb 0.4.0`; the release provides macOS and Linux binaries. Python 3.8+
is used for build utilities only. The host also needs Bash and Clang.

On macOS, `build_tb.sh` uses the Homebrew compiler at
`$(brew --cellar)/tb/0.4.0/libexec/libexec/tb`. On Linux or with another
installation, point `TB_BOOTSTRAP_COMPILER` at the native LLVM compiler binary:

```sh
TB_BOOTSTRAP_COMPILER=/path/to/tb-0.4.0 \
TB_BOOTSTRAP_SHA256='<sha256-of-that-binary>' \
./build_tb.sh
```

The build checks the seed version and optional hash, copies it to
`.build/stage2/bootstrap_seed`, then:

1. The seed compiles `compiler/tb/tb.tb` to stage 1 LLVM IR.
2. Clang links stage 1; that compiler produces stage 2 LLVM IR.
3. Clang links stage 2 into `bin/tb`.

Release and seed changes should also verify that stage 2 and stage 3 LLVM are
identical. `TB_VERSION` controls the version reported by the new compiler; it
does not change the seed version.

## Rebuild v0.3.0 from earlier releases

The release chain is:

| Version built | Compiler used to start | Notes |
| --- | --- | --- |
| `v0.2.1` | Its Python compiler | Last release with the working Python compiler. It produces the first native seed. |
| `v0.2.2` | Native `tb 0.2.1` | The release build used the previous native release as its seed. |
| `v0.3.0` | Native `tb 0.2.2` | The Python compiler was removed. |

Linux memory-tuned source variants are available as tags
`v0.2.1-linux-bootstrap.1` and `v0.2.2-linux-bootstrap.1`. Use separate
worktrees so each generated seed stays available:

```sh
git worktree add ../tb-0.2.1-linux v0.2.1-linux-bootstrap.1
(
  cd ../tb-0.2.1-linux
  TB_VERSION=0.2.1 ./build_tb.sh
)

git worktree add ../tb-0.2.2-linux v0.2.2-linux-bootstrap.1
(
  cd ../tb-0.2.2-linux
  TB_BOOTSTRAP_COMPILER=/absolute/path/to/tb-0.2.1-linux/bin/tb \
  TB_VERSION=0.2.2 ./build_tb.sh
)

git worktree add ../tb-0.3.0-linux v0.3.0
(
  cd ../tb-0.3.0-linux
  TB_BOOTSTRAP_COMPILER=/absolute/path/to/tb-0.2.2-linux/bin/tb \
  TB_BOOTSTRAP_SHA256='<sha256-of-that-binary>' \
  TB_VERSION=0.3.0 ./build_tb.sh
)
```

## Windows x64 bootstrap for v0.5.0

The **tb 0.5.0 Windows seed** GitHub Actions workflow runs on pushes to the
`0.5.0-windows-seed` branch. Its Linux job builds the exact `v0.5.0` source
with the checksum-pinned Linux v0.4.0 seed and adapts the resulting LLVM IR
to the Windows x64 ABI. The IR artifact includes the C runtime shim,
generated compiler helpers, source commit, and SHA-256 checksums.

The Windows job links the IR with MSYS2 CLANG64, checks the compiler version,
and rebuilds the tagged source through two generations. It compares the
retargeted IR, then compiles and runs a smoke program. The workflow uploads
the resulting compiler and its checksum as a separate Actions artifact.

This bootstrap produces a Windows compiler executable. Its output still
requires the workflow's IR adapter and runtime shim for the Windows x64
ABI. Windows support for programs that use the POSIX runtime libraries
requires additional work.
