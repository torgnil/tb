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

## Windows x64 bootstrap

The release workflow calls **tb Windows x64 bootstrap** for published
releases and manual builds. You can also run the Windows workflow directly
from the Actions tab. Its Linux job builds the exact `v0.5.0` source
with the checksum-pinned Linux v0.4.0 seed and adapts the resulting LLVM IR to
the Windows x64 ABI. It also generates the embedded compiler helpers from the
selected source at the requested build version. The IR artifact records both
source commits and checksums.

The Windows job links the v0.5.0 IR with MSYS2 CLANG64 and uses that seed to
build stage 2 from the current branch. Stage 2 builds stage 3, the first
executable built by the candidate compiler. CI checks that stage 3 and stage
4 produce identical retargeted IR, then compiles and runs a smoke program
with the stage 3 compiler. It uploads that executable and its checksum as an
Actions artifact.

The bootstrap job runs the numbered fixtures and uploads a per-fixture
report. It checks compiler rejections, compiles any C sources listed by the
compiler, then links and runs accepted fixtures. The report distinguishes C
compilation, linking, execution, and output failures. Any fixture failure
fails the job, and CI still uploads the report.

After the fixture suite and process smoke test pass, CI packages the Windows
candidate as a ZIP. A fresh Windows runner checks the archive SHA-256, runs
the extracted compiler with a system-only `PATH`, and uses the bundled
PowerShell launcher with the CLANG64 toolchain to compile and run a threaded
program. The verified ZIP and checksum are available as an Actions artifact.
The ZIP bundles the native IR adapter. CI uses the Python adapter for the
initial bootstrap and checks that the two adapters produce identical IR for
the compiler and the numbered runtime fixtures.
For a published release, CI waits for the Linux, macOS, and Windows jobs and
checks all three archive checksums before attaching the assets.
