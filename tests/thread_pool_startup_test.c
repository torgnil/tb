/* Fault injection is local to this translation unit; the runtime has no test ABI. */
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <errno.h>

static pthread_mutex_t audit_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t audit_cond = PTHREAD_COND_INITIALIZER;
static void* allocations[64];
static void* mutexes[64];
static void* conditions[64];
static pthread_t workers[4];
static int malloc_calls, allocated, freed, mutex_inits, mutex_destroys;
static int cond_inits, cond_destroys, create_calls, started, entered, joined;
static int fail_malloc, fail_mutex, fail_cond, fail_create = -1;
static int requested = 4;
static _Atomic int jobs;
static _Thread_local int worker_entered;
static int expect_failure;
static pthread_cond_t* pool_condition;

static void require(int condition, const char* message) {
    if (!condition) {
        fprintf(stderr, "startup test failed: %s\n", message);
        _Exit(90);
    }
}

static void remember(void** entries, void* value) {
    for (int i = 0; i < 64; i++) {
        if (entries[i] == NULL) {
            entries[i] = value;
            return;
        }
    }
    require(0, "tracking table full");
}

static void forget(void** entries, void* value) {
    for (int i = 0; i < 64; i++) {
        if (entries[i] == value) {
            entries[i] = NULL;
            return;
        }
    }
    require(0, "invalid or duplicate cleanup");
}

static void* checked_malloc(size_t size) {
    pthread_mutex_lock(&audit_mutex);
    malloc_calls++;
    void* value = malloc_calls == fail_malloc ? NULL : malloc(size);
    if (value != NULL) {
        remember(allocations, value);
        allocated++;
    }
    pthread_mutex_unlock(&audit_mutex);
    return value;
}

static void checked_free(void* value) {
    if (value == NULL) {
        return;
    }
    pthread_mutex_lock(&audit_mutex);
    forget(allocations, value);
    freed++;
    free(value);
    pthread_mutex_unlock(&audit_mutex);
}

static int checked_mutex_init(pthread_mutex_t* value, const pthread_mutexattr_t* attr) {
    pthread_mutex_lock(&audit_mutex);
    int result = fail_mutex ? EAGAIN : pthread_mutex_init(value, attr);
    if (result == 0) {
        remember(mutexes, value);
        mutex_inits++;
    }
    pthread_mutex_unlock(&audit_mutex);
    return result;
}

static int checked_mutex_destroy(pthread_mutex_t* value) {
    pthread_mutex_lock(&audit_mutex);
    forget(mutexes, value);
    int result = pthread_mutex_destroy(value);
    require(result == 0, "mutex destroy failed");
    mutex_destroys++;
    pthread_mutex_unlock(&audit_mutex);
    return result;
}

static int checked_cond_init(pthread_cond_t* value, const pthread_condattr_t* attr) {
    pthread_mutex_lock(&audit_mutex);
    int result = fail_cond ? EAGAIN : pthread_cond_init(value, attr);
    if (result == 0) {
        remember(conditions, value);
        cond_inits++;
        if (pool_condition == NULL) pool_condition = value;
    }
    pthread_mutex_unlock(&audit_mutex);
    return result;
}

static int checked_cond_destroy(pthread_cond_t* value) {
    pthread_mutex_lock(&audit_mutex);
    forget(conditions, value);
    int result = pthread_cond_destroy(value);
    require(result == 0, "condition destroy failed");
    cond_destroys++;
    pthread_mutex_unlock(&audit_mutex);
    return result;
}

static int checked_cond_wait(pthread_cond_t* cond, pthread_mutex_t* mutex) {
    if (cond == pool_condition && !worker_entered) {
        pthread_mutex_lock(&audit_mutex);
        worker_entered = 1;
        entered++;
        pthread_cond_broadcast(&audit_cond);
        pthread_mutex_unlock(&audit_mutex);
    }
    return pthread_cond_wait(cond, mutex);
}

static int checked_create(pthread_t* thread, const pthread_attr_t* attr,
                          void* (*function)(void*), void* value) {
    int index = create_calls++;
    if (index == fail_create) {
        require(entered == started, "failure preceded worker entry");
        return EAGAIN;
    }
    require(index < 4, "unexpected worker count");
    int result = pthread_create(thread, attr, function, value);
    require(result == 0, "host pthread_create failed");
    pthread_mutex_lock(&audit_mutex);
    workers[started++] = *thread;
    /* Deterministic: every prior worker has reached the runtime wait path. */
    while (entered < started) {
        pthread_cond_wait(&audit_cond, &audit_mutex);
    }
    pthread_mutex_unlock(&audit_mutex);
    return result;
}

static int checked_join(pthread_t thread, void** result) {
    int found = 0;
    for (int i = 0; i < started; i++) {
        if (pthread_equal(thread, workers[i])) {
            require(i == joined, "duplicate or unordered worker join");
            found = 1;
        }
    }
    require(found, "join of unstarted worker");
    int status = pthread_join(thread, result);
    require(status == 0, "pthread_join failed");
    joined++;
    return status;
}

static void check_balance(void) {
    require(allocated == freed, "allocation leak");
    require(mutex_inits == mutex_destroys, "mutex leak");
    require(cond_inits == cond_destroys, "condition leak");
    require(started == joined, "unjoined worker");
    require(entered == started, "worker did not enter");
    require(atomic_load(&jobs) == (expect_failure ? 0 : 1), "unexpected task execution");
    printf("allocated=%d freed=%d mutex=%d/%d cond=%d/%d started=%d entered=%d joined=%d jobs=%d\n",
           allocated, freed, mutex_inits, mutex_destroys, cond_inits, cond_destroys,
           started, entered, joined, atomic_load(&jobs));
    fflush(stdout);
}

static _Noreturn void checked_exit(int status) {
    require(expect_failure && status == 1, "unexpected runtime exit");
    check_balance();
    exit(status);
}

#define malloc checked_malloc
#define free checked_free
#define pthread_mutex_init checked_mutex_init
#define pthread_mutex_destroy checked_mutex_destroy
#define pthread_cond_init checked_cond_init
#define pthread_cond_destroy checked_cond_destroy
#define pthread_cond_wait checked_cond_wait
#define pthread_create checked_create
#define pthread_join checked_join
#define exit checked_exit
#include "thread_pool_runtime.c"
#undef malloc
#undef free
#undef pthread_mutex_init
#undef pthread_mutex_destroy
#undef pthread_cond_init
#undef pthread_cond_destroy
#undef pthread_cond_wait
#undef pthread_create
#undef pthread_join
#undef exit

_Thread_local void* __tb_exception_handler;
_Thread_local char* __tb_exception_message;
void* tb_runtime_retain(void* value) { return value; }
void tb_runtime_release(void* value) { (void)value; }
void tb_runtime_longjmp(void* env, int value) { longjmp(env, value); }

static int64_t job(void) {
    atomic_fetch_add(&jobs, 1);
    return 37;
}

int main(int argc, char** argv) {
    require(argc == 2, "one case argument required");
    const char* mode = argv[1];
    int64_t count = requested;
    expect_failure = 1;
    if (strcmp(mode, "malloc1") == 0) fail_malloc = 1;
    else if (strcmp(mode, "malloc2") == 0) fail_malloc = 2;
    else if (strcmp(mode, "mutex") == 0) fail_mutex = 1;
    else if (strcmp(mode, "cond") == 0) fail_cond = 1;
    else if (strcmp(mode, "create0") == 0) fail_create = 0;
    else if (strcmp(mode, "create1") == 0) fail_create = 1;
    else if (strcmp(mode, "create2") == 0) fail_create = 2;
    else if (strcmp(mode, "create3") == 0) fail_create = 3;
    else if (strcmp(mode, "zero") == 0) count = 0;
    else if (strcmp(mode, "negative") == 0) count = -1;
    else if (strcmp(mode, "overflow") == 0) count = (int64_t)INT_MAX + 1;
    else if (strcmp(mode, "success1") == 0) count = 1, expect_failure = 0;
    else if (strcmp(mode, "success2") == 0) count = 2, expect_failure = 0;
    else if (strcmp(mode, "success4") == 0) count = 4, expect_failure = 0;
    else require(0, "unknown case");
    if (!expect_failure) requested = (int)count;
    tb_thread_pool* pool = tb_thread_pool_new(count);
    require(!expect_failure, "constructor published a partial pool");
    tb_future_i64* future = tb_thread_pool_submit_i64(pool, job);
    require(tb_future_i64_await(future) == 37, "incorrect task result");
    tb_future_i64_release(future);
    tb_thread_pool_release(pool);
    check_balance();
    return 0;
}
