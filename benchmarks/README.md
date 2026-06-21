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
```

The runner compiles each benchmark as setup, but reports only executable runtime. Build outputs are written to `.build/benchmarks/`.

