# Thread runtime safety

This page records the shipped runtime state that worker threads can reach, the
protections found in the source audit, and the limits of the current checks. It
does not make user program state thread-safe automatically.

## Runtime-owned shared state

- `compiler/tb/llvm_helpers/string_base.ll` has six mutable counters
  (`tb_rt_sc`, `tb_rt_sb`, `tb_rt_xc`, `tb_rt_xb`, `tb_rt_ic`, and `tb_rt_ib`)
  and a 256-entry character cache. `string_array.ll` has five mutable counters
  (`tb_rt_an`, `tb_rt_as`, `tb_rt_ap`, `tb_rt_ag`, and `tb_rt_ah`). Counter
  updates and string reference counts use LLVM atomic operations; character
  cache publication uses compare-and-swap.
- Each emitted `cached` function has a static lock and a fixed-size key/value
  table. Lookup and publication use that lock; the cached function body runs
  outside it. Concurrent misses may run the body more than once.
- Each thread has its own exception handler and exception-message slots. A
  worker catches a task exception, stores its owned message in the future, and
  restores that thread's previous exception slots before taking another task.
- A pool's mutex protects its reference count, stop flag, queue links, and
  enqueue/dequeue operations. The worker count and array storage are initialized
  before creation starts; each worker ID is stored as that worker is created.
  After successful construction, the worker array is fixed and is used to join
  every worker before pool storage is released.
- A future's mutex protects its reference count, completion and failure flags,
  error pointer, and result value, whether scalar or pointer. Its result-release
  function is immutable after construction. A task's function, argument, kind,
  and future pointer are filled before enqueue; the pool lock publishes the
  task to a worker. After dequeue, that worker owns the task node and its private
  argument snapshot.
- Array snapshots, records, maps, and sets created as task-local values are
  private to that task unless the program separately shares them. The
  thread-pool boundary deep-copies the supported `int[]` and `int[][]` values.
  Immutable managed strings can be shared through their synchronized reference
  counts.
- Generated global initialization is called by the generated `main` wrapper.
  Its flag is a main-wrapper guard, not a general once primitive. A user global
  initializer can itself create a pool or submit work; doing so can let a
  worker read globals while initialization is still in progress. Create pools
  and submit work from `main` after global initialization has completed.
- The compiler's `LLVM_*` caches belong to the compiler process. The self-hosted
  compiler uses them while compiling sequentially; ordinary compiled programs
  do not inherit those compiler caches as runtime state.

## State that remains the program's responsibility

Read-only initialized user state can be shared by tasks. Concurrent access that
includes mutation needs external coordination. Mutable containers, file handles,
and foreign-library state are not automatically synchronized. Cached function
bodies have the same rule even though the cache table itself is protected. The
runtime does not wrap arbitrary foreign calls with locks.

A fixed-size pool can deadlock if every worker blocks waiting for work that is
still queued to that same pool. The runtime provides no work stealing; leave a
worker available to run dependent tasks or use another execution path.

The audited runtime uses allocator calls, local buffers, memory copies, and
sorting routines that are reentrant on the verified macOS host. The audited
helpers do not use process-global `rand` or `strtok` scratch state. This source
review does not establish behavior for every foreign library or other platform.

## Evidence and limits

The manual source inventory for this revision covered all 20 templates in
`compiler/tb/llvm_helpers/`: `bool_array.ll`, `int_array_array.ll`,
`int_array_base.ll`, `int_array_map_ops.ll`, `int_set.ll`,
`integer_shifts.ll`, `main_args.ll`, `map_base.ll`, `map_int_int.ll`,
`map_string_key.ll`, `num.ll`, `record_array_base.ll`,
`record_array_edge.ll`, `record_array_node.ll`, `record_helpers_base.ll`,
`record_set_base.ll`, `string_array.ll`, `string_array_array.ll`,
`string_base.ll`, and `string_num_to_string.ll`, plus the emitted cached-table
globals, exception TLS, and thread-pool/composite C sources. That inventory is
manual source review. The fixture and sanitizer cases below are dynamic checks
of the specific worker and value families they execute, not an exhaustive run
of every template or every user program.

Maintainer lifecycle checks used generated fixture LLVM and a fixed,
mutex-protected pointer tracker for its explicit allocation calls and the
included thread-pool and composite C calls. They exercised a blocked four-worker
pool with 80 queued tasks, all five supported result families, five
failure families, dropped caller references, queue draining, repeated awaits,
array snapshots, ten distinct owned error-message copies held by failed futures,
and the exact 110-block selected live-allocation checkpoint. ASan
and TSan runs verified actual memory hooks in generated worker functions and the
included C runtime, ran known-bad memory/race controls, and repeated the TSan case.
The tracker covers explicit allocations from those target translation units;
it excludes allocations inside libc, pthreads, and the sanitizers themselves.

Separate maintainer checks exercised pool startup failures, including
allocation, synchronization initialization, and partial worker creation.
Submission-time allocation failure remains unchecked. The lifecycle tests do not establish general out-of-memory safety or generic
nonlocal-unwind leak freedom. The runtime's timed waits use `CLOCK_REALTIME`;
changes to the wall clock can affect elapsed timeout duration.
