# Runtime Benchmarks

This directory contains small tb programs for measuring generated-code and runtime performance.

Run all benchmarks:

```bash
./benchmarks/run.sh
```

Run a subset or choose another compiler:

```bash
./benchmarks/run.sh --filter string
./benchmarks/run.sh --compiler bin/tb --runs 10
./benchmarks/run.sh --python /opt/homebrew/bin/python3.12
```

Python comparisons require Python 3.10 or newer. The runner uses `python3` from
`PATH` by default; use `--python PATH` to choose an interpreter explicitly.

The runner compiles each benchmark as setup, but reports only executable runtime. Build outputs are written to `.build/benchmarks/`.

The regex benchmarks use ASCII inputs and patterns supported by all three
implementations. `regex_compile` compiles 1,000 distinct patterns, avoiding
Python's reuse of a cached pattern. `regex_match` and `regex_contains` each
compile a pattern once, then count full-string or substring matches respectively,
including unsuccessful and longer inputs. The POSIX C full-match benchmark uses
an anchored pattern. All three print counts
checked against the same expected output. Timings include program startup and
the work inside each benchmark, including regex compilation. The engines have
different semantics and implementations, so these timings describe these
workloads rather than all regex use.

