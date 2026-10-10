/* Lifecycle stress driver; the included runtime and composite C are instrumented below. */
#define _DARWIN_C_SOURCE
#include <pthread.h>
#include <setjmp.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TRACKED_CAPACITY 8192

typedef struct tracked_allocation {
    void* pointer;
    size_t requested;
} tracked_allocation;

static pthread_mutex_t tracker_mutex = PTHREAD_MUTEX_INITIALIZER;
static tracked_allocation tracked[TRACKED_CAPACITY];
static size_t live_blocks;
static size_t live_bytes;
static size_t peak_blocks;
static size_t peak_bytes;
static int tracker_failed;

static int tb_audit_runtime_join(pthread_t thread, void** result);

static size_t tracked_find(void* pointer) {
    for (size_t index = 0; index < TRACKED_CAPACITY; index += 1) {
        if (tracked[index].pointer == pointer) return index;
    }
    return TRACKED_CAPACITY;
}

static void tracked_add(void* pointer, size_t requested) {
    if (pointer == NULL) return;
    pthread_mutex_lock(&tracker_mutex);
    if (tracked_find(pointer) != TRACKED_CAPACITY) {
        tracker_failed = 1;
        pthread_mutex_unlock(&tracker_mutex);
        fprintf(stderr, "lifecycle accounting failed: duplicate allocation\n");
        return;
    }
    for (size_t index = 0; index < TRACKED_CAPACITY; index += 1) {
        if (tracked[index].pointer == NULL) {
            tracked[index].pointer = pointer;
            tracked[index].requested = requested;
            live_blocks += 1;
            live_bytes += requested;
            if (live_blocks > peak_blocks) peak_blocks = live_blocks;
            if (live_bytes > peak_bytes) peak_bytes = live_bytes;
            pthread_mutex_unlock(&tracker_mutex);
            return;
        }
    }
    tracker_failed = 1;
    pthread_mutex_unlock(&tracker_mutex);
    fprintf(stderr, "lifecycle accounting failed: tracking table full\n");
}

static size_t tracked_remove(void* pointer) {
    if (pointer == NULL) return 0;
    pthread_mutex_lock(&tracker_mutex);
    size_t index = tracked_find(pointer);
    if (index == TRACKED_CAPACITY) {
        tracker_failed = 1;
        pthread_mutex_unlock(&tracker_mutex);
        fprintf(stderr, "lifecycle accounting failed: invalid or duplicate free\n");
        return 0;
    }
    size_t requested = tracked[index].requested;
    tracked[index].pointer = NULL;
    tracked[index].requested = 0;
    live_blocks -= 1;
    live_bytes -= requested;
    pthread_mutex_unlock(&tracker_mutex);
    return requested;
}

void* tb_audit_malloc(size_t size) {
    void* pointer = malloc(size == 0 ? 1 : size);
    tracked_add(pointer, size);
    return pointer;
}

void* tb_audit_calloc(size_t count, size_t size) {
    if (size != 0 && count > SIZE_MAX / size) return NULL;
    size_t requested = count * size;
    void* pointer = calloc(requested == 0 ? 1 : count, requested == 0 ? 1 : size);
    tracked_add(pointer, requested);
    return pointer;
}

void* tb_audit_realloc(void* pointer, size_t size) {
    if (pointer == NULL) return tb_audit_malloc(size);
    pthread_mutex_lock(&tracker_mutex);
    size_t index = tracked_find(pointer);
    if (index == TRACKED_CAPACITY) {
        tracker_failed = 1;
        pthread_mutex_unlock(&tracker_mutex);
        fprintf(stderr, "lifecycle accounting failed: realloc of untracked pointer\n");
        return NULL;
    }
    size_t old_size = tracked[index].requested;
    void* replacement = realloc(pointer, size == 0 ? 1 : size);
    if (replacement == NULL) {
        pthread_mutex_unlock(&tracker_mutex);
        return NULL;
    }
    tracked[index].pointer = replacement;
    tracked[index].requested = size;
    live_bytes = live_bytes - old_size + size;
    if (live_bytes > peak_bytes) peak_bytes = live_bytes;
    pthread_mutex_unlock(&tracker_mutex);
    return replacement;
}

void tb_audit_free(void* pointer) {
    if (pointer == NULL) return;
    (void)tracked_remove(pointer);
    free(pointer);
}

#define malloc tb_audit_malloc
#define calloc tb_audit_calloc
#define realloc tb_audit_realloc
#define free tb_audit_free
#define pthread_join tb_audit_runtime_join
#include "../compiler/tb/runtime/thread_pool_runtime.c"
#include "../compiler/tb/runtime/thread_pool_composite_runtime.c"
#undef pthread_join
#undef free
#undef realloc
#undef calloc
#undef malloc

extern int64_t lifecycle_int(int64_t value);
extern bool lifecycle_bool(bool value);
extern char* lifecycle_string(char* value);
extern char* lifecycle_message(int64_t value);
extern void* lifecycle_array(void* values);
extern void* lifecycle_nested(void* values);
extern int64_t fail_lifecycle_int(char* message);
extern bool fail_lifecycle_bool(char* message);
extern char* fail_lifecycle_string(char* message);
extern void* fail_lifecycle_array(char* message);
extern void* fail_lifecycle_nested(char* message);
extern void tb_runtime_release(void* value);
extern void tb_runtime_longjmp(void* env, int value);

static pthread_mutex_t gate_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond = PTHREAD_COND_INITIALIZER;
static int gate_open;
static int gate_entered;
static int tasks_completed;
static int shutdown_join_started;
static tb_thread_pool* shutdown_pool;
static int64_t seed_value;
static char expected_message[96];
static size_t observed_checkpoint_bytes;

static _Noreturn void fail(const char* message) {
    fprintf(stderr, "thread-pool lifecycle test failed: %s\n", message);
    _Exit(91);
}

static void require(int condition, const char* message) {
    if (!condition) fail(message);
}

static void gate_wait(bool blocker) {
    pthread_mutex_lock(&gate_mutex);
    if (blocker) {
        gate_entered += 1;
        pthread_cond_broadcast(&gate_cond);
    }
    while (!gate_open) pthread_cond_wait(&gate_cond, &gate_mutex);
    tasks_completed += 1;
    pthread_mutex_unlock(&gate_mutex);
}

static int64_t blocker_worker(void) {
    gate_wait(true);
    return 0;
}

static int64_t gated_int(int64_t value) {
    gate_wait(false);
    return lifecycle_int(value);
}

static bool gated_bool(bool value) {
    gate_wait(false);
    return lifecycle_bool(value);
}

static char* gated_string(char* value) {
    gate_wait(false);
    return lifecycle_string(value);
}

static void* gated_array(void* value) {
    gate_wait(false);
    return lifecycle_array(value);
}

static void* gated_nested(void* value) {
    gate_wait(false);
    return lifecycle_nested(value);
}

static int64_t gated_fail_int(char* message) {
    gate_wait(false);
    return fail_lifecycle_int(message);
}

static bool gated_fail_bool(char* message) {
    gate_wait(false);
    return fail_lifecycle_bool(message);
}

static char* gated_fail_string(char* message) {
    gate_wait(false);
    return fail_lifecycle_string(message);
}

static void* gated_fail_array(char* message) {
    gate_wait(false);
    return fail_lifecycle_array(message);
}

static void* gated_fail_nested(char* message) {
    gate_wait(false);
    return fail_lifecycle_nested(message);
}

static int tb_audit_runtime_join(pthread_t thread, void** result) {
    if (shutdown_pool != NULL) {
        pthread_mutex_lock(&shutdown_pool->mutex);
        bool is_worker = false;
        for (int index = 0; index < shutdown_pool->worker_count; index += 1) {
            if (pthread_equal(thread, shutdown_pool->workers[index])) is_worker = true;
        }
        pthread_mutex_unlock(&shutdown_pool->mutex);
        if (is_worker) {
            pthread_mutex_lock(&gate_mutex);
            shutdown_join_started = 1;
            pthread_cond_broadcast(&gate_cond);
            pthread_mutex_unlock(&gate_mutex);
        }
    }
    return pthread_join(thread, result);
}

static void* release_pool_thread(void* value) {
    tb_thread_pool_release((tb_thread_pool*)value);
    return NULL;
}

static void wait_until(int* value, int expected) {
    pthread_mutex_lock(&gate_mutex);
    while (*value < expected) pthread_cond_wait(&gate_cond, &gate_mutex);
    pthread_mutex_unlock(&gate_mutex);
}

static void assert_queue_state(tb_thread_pool* pool, size_t expected) {
    pthread_mutex_lock(&pool->mutex);
    require(pool->stop, "pool stop flag was not set before join");
    size_t count = 0;
    for (tb_task* task = pool->head; task != NULL; task = task->next) count += 1;
    require(count == expected, "pending queue length changed while workers were gated");
    pthread_mutex_unlock(&pool->mutex);
}

static void check_error_message(char* message) {
    require(message != NULL && strcmp(message, expected_message) == 0,
            "await caught an incorrect exception message");
    tb_runtime_release(message);
    __tb_exception_message = NULL;
    __tb_exception_handler = NULL;
}

#define CHECK_FAILURE(await_expression) do { \
    jmp_buf env; \
    __tb_exception_handler = env; \
    int caught = setjmp(env); \
    if (caught == 0) { \
        (void)(await_expression); \
        fail("failed future unexpectedly returned"); \
    } \
    check_error_message(__tb_exception_message); \
} while (0)

static size_t expected_checkpoint_bytes(void) {
    size_t futures = 8 * (sizeof(tb_future_i64) + sizeof(tb_future_bool) +
                          sizeof(tb_future_string) + 2 * sizeof(tb_future_int_array));
    size_t message_length = strlen(expected_message);
    size_t strings = 6 * (24 + message_length + 1 + 1) +
                     10 * (24 + message_length + 1);
    size_t arrays = 6 * (sizeof(tb_thread_pool_int_array) + 4 * sizeof(int64_t));
    size_t nested = 6 * (sizeof(tb_thread_pool_int_array_array) +
                         2 * sizeof(void*) + 2 * sizeof(unsigned char) +
                         2 * (sizeof(tb_thread_pool_int_array) + 4 * sizeof(int64_t)));
    return futures + strings + arrays + nested;
}

static void require_balanced(void) {
    pthread_mutex_lock(&tracker_mutex);
    size_t blocks = live_blocks;
    size_t bytes = live_bytes;
    int failed = tracker_failed;
    pthread_mutex_unlock(&tracker_mutex);
    require(!failed, "allocation wrapper detected an invalid operation");
    require(blocks == 0 && bytes == 0, "tracked allocations remain after releasing futures");
}

static void run_round(int64_t seed) {
    seed_value = seed;
    int64_t row_values[2] = {seed, 9};
    tb_thread_pool_int_array row = {2, 2, row_values};
    int64_t nested_values[2] = {seed, 8};
    tb_thread_pool_int_array nested_row = {2, 2, nested_values};
    tb_thread_pool_int_array empty_row = {0, 0, NULL};
    void* nested_rows[2] = {&nested_row, &empty_row};
    unsigned char nested_owned[2] = {0, 0};
    tb_thread_pool_int_array_array nested = {2, nested_rows, nested_owned};

    tb_thread_pool* pool = tb_thread_pool_new(4);
    tb_future_i64* blockers[4];
    for (int index = 0; index < 4; index += 1) {
        blockers[index] = tb_thread_pool_submit_i64(pool, blocker_worker);
    }
    wait_until(&gate_entered, 4);

    char* shared_message = lifecycle_message(seed);
    require(shared_message != NULL && strcmp(shared_message, expected_message) == 0,
            "generated shared string setup failed");
    tb_future_i64* int_success[12];
    tb_future_bool* bool_success[12];
    tb_future_string* string_success[12];
    tb_future_int_array* array_success[12];
    tb_future_int_array_array* nested_success[12];
    tb_future_i64* int_failure[4];
    tb_future_bool* bool_failure[4];
    tb_future_string* string_failure[4];
    tb_future_int_array* array_failure[4];
    tb_future_int_array_array* nested_failure[4];
    for (int index = 0; index < 12; index += 1) {
        int64_t value = seed + index;
        int_success[index] = tb_thread_pool_submit_i64_i64(pool, gated_int, value);
        bool_success[index] = tb_thread_pool_submit_bool_bool(pool, gated_bool, (index & 1) != 0);
        string_success[index] = tb_thread_pool_submit_string_string(pool, gated_string, shared_message);
        array_success[index] = tb_thread_pool_submit_int_array_int_array(pool, gated_array, &row);
        nested_success[index] = tb_thread_pool_submit_int_array_array_int_array_array(
            pool, gated_nested, &nested);
    }
    for (int index = 0; index < 4; index += 1) {
        int_failure[index] = tb_thread_pool_submit_i64_string(pool, gated_fail_int, shared_message);
        bool_failure[index] = tb_thread_pool_submit_bool_string(pool, gated_fail_bool, shared_message);
        string_failure[index] = tb_thread_pool_submit_string_string(pool, gated_fail_string, shared_message);
        array_failure[index] = tb_thread_pool_submit_int_array_string(pool, gated_fail_array, shared_message);
        nested_failure[index] = tb_thread_pool_submit_int_array_array_string(pool, gated_fail_nested, shared_message);
    }
    for (int index = 6; index < 12; index += 1) {
        require(!tb_future_i64_is_done(int_success[index]) && !tb_future_i64_wait_for(int_success[index], 0),
                "integer future completed while workers were gated");
        require(!tb_future_bool_is_done(bool_success[index]) && !tb_future_bool_wait_for(bool_success[index], -1),
                "boolean future completed while workers were gated");
        require(!tb_future_string_is_done(string_success[index]) && !tb_future_string_wait_for(string_success[index], 0),
                "string future completed while workers were gated");
        require(!tb_future_int_array_is_done(array_success[index]) && !tb_future_int_array_wait_for(array_success[index], 0),
                "array future completed while workers were gated");
        require(!tb_future_int_array_array_is_done(nested_success[index]) &&
                !tb_future_int_array_array_wait_for(nested_success[index], 0),
                "nested future completed while workers were gated");
    }
    require(!tb_future_i64_wait_for(int_success[6], 1),
            "timed wait reported a task complete while workers were gated");
    require(live_blocks > 0, "selected allocations were not wrapped");
    row_values[0] = seed + 1000;
    nested_values[0] = seed + 2000;
    tb_runtime_release(shared_message);

    /* Drop half of every family while all workers remain behind the gate. */
    for (int index = 0; index < 6; index += 1) {
        tb_future_i64_release(int_success[index]);
        tb_future_bool_release(bool_success[index]);
        tb_future_string_release(string_success[index]);
        tb_future_int_array_release(array_success[index]);
        tb_future_int_array_array_release(nested_success[index]);
    }
    for (int index = 0; index < 2; index += 1) {
        tb_future_i64_release(int_failure[index]);
        tb_future_bool_release(bool_failure[index]);
        tb_future_string_release(string_failure[index]);
        tb_future_int_array_release(array_failure[index]);
        tb_future_int_array_array_release(nested_failure[index]);
    }
    shutdown_pool = pool;
    pthread_t shutdown_thread;
    require(pthread_create(&shutdown_thread, NULL, release_pool_thread, pool) == 0,
            "could not create shutdown thread");
    wait_until(&shutdown_join_started, 1);
    assert_queue_state(pool, 80);

    pthread_mutex_lock(&gate_mutex);
    gate_open = 1;
    pthread_cond_broadcast(&gate_cond);
    pthread_mutex_unlock(&gate_mutex);
    require(pthread_join(shutdown_thread, NULL) == 0, "shutdown thread join failed");
    shutdown_pool = NULL;
    require(tasks_completed == 84, "not all 84 queued tasks executed exactly once");

    for (int index = 0; index < 4; index += 1) {
        require(tb_future_i64_await(blockers[index]) == 0, "blocker result mismatch");
        tb_future_i64_release(blockers[index]);
    }

    for (int index = 6; index < 12; index += 1) {
        require(tb_future_i64_is_done(int_success[index]), "integer future not done");
        require(tb_future_i64_wait_for(int_success[index], 0), "integer wait_for missed completed future");
        int64_t value = tb_future_i64_await(int_success[index]);
        require(value == seed + index + 7, "integer result mismatch");
        require(tb_future_i64_await(int_success[index]) == value, "repeated integer await changed result");

        require(tb_future_bool_is_done(bool_success[index]), "boolean future not done");
        require(tb_future_bool_wait_for(bool_success[index], 0), "boolean wait_for missed completed future");
        bool boolean = tb_future_bool_await(bool_success[index]);
        require(boolean == ((index & 1) == 0), "boolean result mismatch");
        require(tb_future_bool_await(bool_success[index]) == boolean, "repeated boolean await changed result");

        require(tb_future_string_is_done(string_success[index]), "string future not done");
        require(tb_future_string_wait_for(string_success[index], 0), "string wait_for missed completed future");
        char* first_string = tb_future_string_await(string_success[index]);
        char* second_string = tb_future_string_await(string_success[index]);
        require(first_string == second_string && strcmp(first_string, expected_message) != 0,
                "repeated string await did not preserve value");
        char expected_result[112];
        snprintf(expected_result, sizeof(expected_result), "%s!", expected_message);
        require(strcmp(first_string, expected_result) == 0 && strcmp(second_string, expected_result) == 0,
                "string task result did not preserve its managed input");
        tb_runtime_release(first_string);
        tb_runtime_release(second_string);

        require(tb_future_int_array_is_done(array_success[index]), "array future not done");
        require(tb_future_int_array_wait_for(array_success[index], 0), "array wait_for missed completed future");
        tb_thread_pool_int_array* first_array = tb_future_int_array_await(array_success[index]);
        tb_thread_pool_int_array* second_array = tb_future_int_array_await(array_success[index]);
        require(first_array != second_array && first_array->data != second_array->data,
                "array awaits shared storage");
        require(first_array->data[0] == seed + 10 && first_array->data[1] == 9 &&
                second_array->data[0] == seed + 10 && second_array->data[1] == 9,
                "array snapshot did not preserve queued input");
        first_array->data[0] = -1;
        require(second_array->data[0] == seed + 10, "array await mutation reached later snapshot");
        tb_thread_pool_int_array_snapshot_free(first_array);
        tb_thread_pool_int_array_snapshot_free(second_array);

        require(tb_future_int_array_array_is_done(nested_success[index]), "nested future not done");
        require(tb_future_int_array_array_wait_for(nested_success[index], 0), "nested wait_for missed completed future");
        tb_thread_pool_int_array_array* first_nested = tb_future_int_array_array_await(nested_success[index]);
        tb_thread_pool_int_array_array* second_nested = tb_future_int_array_array_await(nested_success[index]);
        tb_thread_pool_int_array* first_row = first_nested->data[0];
        tb_thread_pool_int_array* second_row = second_nested->data[0];
        require(first_nested != second_nested && first_nested->data != second_nested->data &&
                first_row != second_row && first_row->data != second_row->data,
                "nested awaits shared storage");
        require(first_row->data[0] == seed + 10 && first_row->data[1] == 8 &&
                ((tb_thread_pool_int_array*)first_nested->data[1])->length == 0 &&
                second_row->data[0] == seed + 10 && second_row->data[1] == 8 &&
                ((tb_thread_pool_int_array*)second_nested->data[1])->length == 0,
                "nested snapshot lost populated or empty row");
        first_row->data[0] = -1;
        require(second_row->data[0] == seed + 10, "nested await mutation reached later snapshot");
        tb_thread_pool_int_array_array_snapshot_free(first_nested);
        tb_thread_pool_int_array_array_snapshot_free(second_nested);
    }

    char* retained_errors[10] = {
        int_failure[2]->error, int_failure[3]->error,
        bool_failure[2]->error, bool_failure[3]->error,
        string_failure[2]->error, string_failure[3]->error,
        array_failure[2]->error, array_failure[3]->error,
        nested_failure[2]->error, nested_failure[3]->error,
    };
    for (int left = 0; left < 10; left += 1) {
        require(retained_errors[left] != NULL && strcmp(retained_errors[left], expected_message) == 0,
                "retained future error does not own the expected message");
        for (int right = left + 1; right < 10; right += 1) {
            require(retained_errors[left] != retained_errors[right],
                    "separate failed futures unexpectedly share an owned error allocation");
        }
    }

    for (int index = 2; index < 4; index += 1) {
        require(tb_future_i64_is_done(int_failure[index]) && tb_future_i64_wait_for(int_failure[index], 0),
                "failed integer future was not marked done");
        require(tb_future_bool_is_done(bool_failure[index]) && tb_future_bool_wait_for(bool_failure[index], 0),
                "failed boolean future was not marked done");
        require(tb_future_string_is_done(string_failure[index]) && tb_future_string_wait_for(string_failure[index], 0),
                "failed string future was not marked done");
        require(tb_future_int_array_is_done(array_failure[index]) && tb_future_int_array_wait_for(array_failure[index], 0),
                "failed array future was not marked done");
        require(tb_future_int_array_array_is_done(nested_failure[index]) &&
                tb_future_int_array_array_wait_for(nested_failure[index], 0),
                "failed nested future was not marked done");
        CHECK_FAILURE(tb_future_i64_await(int_failure[index]));
        CHECK_FAILURE(tb_future_i64_await(int_failure[index]));
        CHECK_FAILURE(tb_future_bool_await(bool_failure[index]));
        CHECK_FAILURE(tb_future_bool_await(bool_failure[index]));
        CHECK_FAILURE(tb_future_string_await(string_failure[index]));
        CHECK_FAILURE(tb_future_string_await(string_failure[index]));
        CHECK_FAILURE(tb_future_int_array_await(array_failure[index]));
        CHECK_FAILURE(tb_future_int_array_await(array_failure[index]));
        CHECK_FAILURE(tb_future_int_array_array_await(nested_failure[index]));
        CHECK_FAILURE(tb_future_int_array_array_await(nested_failure[index]));
    }

    pthread_mutex_lock(&tracker_mutex);
    size_t checkpoint_blocks = live_blocks;
    size_t checkpoint_bytes = live_bytes;
    size_t expected_bytes = expected_checkpoint_bytes();
    pthread_mutex_unlock(&tracker_mutex);
    observed_checkpoint_bytes = checkpoint_bytes;
    require(checkpoint_blocks == 110, "live allocation checkpoint did not contain 110 selected blocks");
    require(checkpoint_bytes == expected_bytes, "live allocation checkpoint byte formula mismatch");
    for (int index = 6; index < 12; index += 1) {
        tb_future_i64_release(int_success[index]);
        tb_future_bool_release(bool_success[index]);
        tb_future_string_release(string_success[index]);
        tb_future_int_array_release(array_success[index]);
        tb_future_int_array_array_release(nested_success[index]);
    }
    for (int index = 2; index < 4; index += 1) {
        tb_future_i64_release(int_failure[index]);
        tb_future_bool_release(bool_failure[index]);
        tb_future_string_release(string_failure[index]);
        tb_future_int_array_release(array_failure[index]);
        tb_future_int_array_array_release(nested_failure[index]);
    }
    require_balanced();
}

int main(int argc, char** argv) {
    require(argc == 2, "one numeric seed argument is required");
    char* end = NULL;
    long long parsed = strtoll(argv[1], &end, 10);
    require(end != argv[1] && *end == '\0', "seed argument must be an integer");
    require(parsed >= -1000000 && parsed <= 1000000,
            "seed argument must be between -1000000 and 1000000");
    seed_value = (int64_t)parsed;
    snprintf(expected_message, sizeof(expected_message), "failure-%lld", parsed);
    run_round(seed_value);
    printf("lifecycle seed=%lld tasks=84 queue=80 checkpoint=110/%zu final=0/0\n",
           (long long)seed_value, observed_checkpoint_bytes);
    return 0;
}
