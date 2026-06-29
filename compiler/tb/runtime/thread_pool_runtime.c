#include <pthread.h>
#include <stdbool.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdlib.h>

typedef int64_t (*tb_i64_from_i64_task_fn)(int64_t);
typedef int64_t (*tb_i64_from_bool_task_fn)(bool);
typedef bool (*tb_bool_from_i64_task_fn)(int64_t);
typedef bool (*tb_bool_from_bool_task_fn)(bool);
typedef char* (*tb_string_from_i64_task_fn)(int64_t);
typedef char* (*tb_string_from_bool_task_fn)(bool);
typedef int64_t (*tb_i64_from_string_task_fn)(char*);
typedef bool (*tb_bool_from_string_task_fn)(char*);
typedef char* (*tb_string_from_string_task_fn)(char*);

extern void* tb_runtime_retain(void* value);
extern void tb_runtime_release(void* value);
extern void tb_runtime_longjmp(void* env, int value);
extern _Thread_local void* __tb_exception_handler;
extern _Thread_local char* __tb_exception_message;

typedef struct tb_future_i64 {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int refcount;
    bool done;
    bool failed;
    char* error;
    int64_t result;
} tb_future_i64;

typedef struct tb_future_bool {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int refcount;
    bool done;
    bool failed;
    char* error;
    bool result;
} tb_future_bool;

typedef struct tb_future_string {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int refcount;
    bool done;
    bool failed;
    char* error;
    char* result;
} tb_future_string;

typedef enum tb_task_kind {
    TB_TASK_KIND_I64_FROM_I64 = 1,
    TB_TASK_KIND_I64_FROM_BOOL = 2,
    TB_TASK_KIND_BOOL_FROM_I64 = 3,
    TB_TASK_KIND_BOOL_FROM_BOOL = 4,
    TB_TASK_KIND_STRING_FROM_I64 = 5,
    TB_TASK_KIND_STRING_FROM_BOOL = 6,
    TB_TASK_KIND_I64_FROM_STRING = 7,
    TB_TASK_KIND_BOOL_FROM_STRING = 8,
    TB_TASK_KIND_STRING_FROM_STRING = 9
} tb_task_kind;

typedef struct tb_task {
    tb_task_kind kind;
    union {
        int64_t i64_arg;
        bool bool_arg;
        char* string_arg;
    } arg;
    union {
        tb_i64_from_i64_task_fn i64_from_i64_fn;
        tb_i64_from_bool_task_fn i64_from_bool_fn;
        tb_bool_from_i64_task_fn bool_from_i64_fn;
        tb_bool_from_bool_task_fn bool_from_bool_fn;
        tb_string_from_i64_task_fn string_from_i64_fn;
        tb_string_from_bool_task_fn string_from_bool_fn;
        tb_i64_from_string_task_fn i64_from_string_fn;
        tb_bool_from_string_task_fn bool_from_string_fn;
        tb_string_from_string_task_fn string_from_string_fn;
    } function;
    union {
        tb_future_i64* i64_future;
        tb_future_bool* bool_future;
        tb_future_string* string_future;
    } future;
    struct tb_task* next;
} tb_task;

typedef struct tb_thread_pool {
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    int refcount;
    int worker_count;
    bool stop;
    pthread_t* workers;
    tb_task* head;
    tb_task* tail;
} tb_thread_pool;

static void tb_future_i64_release_internal(tb_future_i64* future) {
    bool should_free = false;
    char* error = NULL;
    pthread_mutex_lock(&future->mutex);
    future->refcount -= 1;
    should_free = future->refcount == 0;
    error = future->error;
    pthread_mutex_unlock(&future->mutex);
    if (!should_free) {
        return;
    }
    if (error != NULL) {
        tb_runtime_release(error);
    }
    pthread_cond_destroy(&future->cond);
    pthread_mutex_destroy(&future->mutex);
    free(future);
}

static void tb_future_bool_release_internal(tb_future_bool* future) {
    bool should_free = false;
    char* error = NULL;
    pthread_mutex_lock(&future->mutex);
    future->refcount -= 1;
    should_free = future->refcount == 0;
    error = future->error;
    pthread_mutex_unlock(&future->mutex);
    if (!should_free) {
        return;
    }
    if (error != NULL) {
        tb_runtime_release(error);
    }
    pthread_cond_destroy(&future->cond);
    pthread_mutex_destroy(&future->mutex);
    free(future);
}

static void tb_future_string_release_internal(tb_future_string* future) {
    bool should_free = false;
    char* error = NULL;
    char* result = NULL;
    pthread_mutex_lock(&future->mutex);
    future->refcount -= 1;
    should_free = future->refcount == 0;
    error = future->error;
    result = future->result;
    pthread_mutex_unlock(&future->mutex);
    if (!should_free) {
        return;
    }
    if (error != NULL) {
        tb_runtime_release(error);
    }
    if (result != NULL) {
        tb_runtime_release(result);
    }
    pthread_cond_destroy(&future->cond);
    pthread_mutex_destroy(&future->mutex);
    free(future);
}

static void tb_rethrow_async_error(char* error) {
    void* handler = __tb_exception_handler;
    if (error != NULL) {
        __tb_exception_message = (char*)tb_runtime_retain(error);
    } else {
        __tb_exception_message = NULL;
    }
    tb_runtime_longjmp(handler, 1);
}

static void* tb_thread_pool_worker(void* raw_pool) {
    tb_thread_pool* pool = (tb_thread_pool*)raw_pool;
    for (;;) {
        pthread_mutex_lock(&pool->mutex);
        while (pool->head == NULL && !pool->stop) {
            pthread_cond_wait(&pool->cond, &pool->mutex);
        }
        if (pool->head == NULL && pool->stop) {
            pthread_mutex_unlock(&pool->mutex);
            return NULL;
        }
        tb_task* task = pool->head;
        pool->head = task->next;
        if (pool->head == NULL) {
            pool->tail = NULL;
        }
        pthread_mutex_unlock(&pool->mutex);

        void* previous_handler = __tb_exception_handler;
        char* previous_message = __tb_exception_message;
        jmp_buf env;
        int caught = setjmp(env);
        if (caught == 0) {
            __tb_exception_handler = (void*)env;
            __tb_exception_message = NULL;
        }

        if (task->kind == TB_TASK_KIND_I64_FROM_I64 && caught == 0) {
            int64_t result = task->function.i64_from_i64_fn(task->arg.i64_arg);
            pthread_mutex_lock(&task->future.i64_future->mutex);
            task->future.i64_future->result = result;
            task->future.i64_future->failed = false;
            task->future.i64_future->done = true;
            pthread_cond_broadcast(&task->future.i64_future->cond);
            pthread_mutex_unlock(&task->future.i64_future->mutex);
            tb_future_i64_release_internal(task->future.i64_future);
        } else if (task->kind == TB_TASK_KIND_I64_FROM_BOOL && caught == 0) {
            int64_t result = task->function.i64_from_bool_fn(task->arg.bool_arg);
            pthread_mutex_lock(&task->future.i64_future->mutex);
            task->future.i64_future->result = result;
            task->future.i64_future->failed = false;
            task->future.i64_future->done = true;
            pthread_cond_broadcast(&task->future.i64_future->cond);
            pthread_mutex_unlock(&task->future.i64_future->mutex);
            tb_future_i64_release_internal(task->future.i64_future);
        } else if (task->kind == TB_TASK_KIND_BOOL_FROM_I64 && caught == 0) {
            bool result = task->function.bool_from_i64_fn(task->arg.i64_arg);
            pthread_mutex_lock(&task->future.bool_future->mutex);
            task->future.bool_future->result = result;
            task->future.bool_future->failed = false;
            task->future.bool_future->done = true;
            pthread_cond_broadcast(&task->future.bool_future->cond);
            pthread_mutex_unlock(&task->future.bool_future->mutex);
            tb_future_bool_release_internal(task->future.bool_future);
        } else if (task->kind == TB_TASK_KIND_BOOL_FROM_BOOL && caught == 0) {
            bool result = task->function.bool_from_bool_fn(task->arg.bool_arg);
            pthread_mutex_lock(&task->future.bool_future->mutex);
            task->future.bool_future->result = result;
            task->future.bool_future->failed = false;
            task->future.bool_future->done = true;
            pthread_cond_broadcast(&task->future.bool_future->cond);
            pthread_mutex_unlock(&task->future.bool_future->mutex);
            tb_future_bool_release_internal(task->future.bool_future);
        } else if (task->kind == TB_TASK_KIND_STRING_FROM_I64 && caught == 0) {
            char* result = task->function.string_from_i64_fn(task->arg.i64_arg);
            pthread_mutex_lock(&task->future.string_future->mutex);
            task->future.string_future->result = result;
            task->future.string_future->failed = false;
            task->future.string_future->done = true;
            pthread_cond_broadcast(&task->future.string_future->cond);
            pthread_mutex_unlock(&task->future.string_future->mutex);
            tb_future_string_release_internal(task->future.string_future);
        } else if (task->kind == TB_TASK_KIND_STRING_FROM_BOOL && caught == 0) {
            char* result = task->function.string_from_bool_fn(task->arg.bool_arg);
            pthread_mutex_lock(&task->future.string_future->mutex);
            task->future.string_future->result = result;
            task->future.string_future->failed = false;
            task->future.string_future->done = true;
            pthread_cond_broadcast(&task->future.string_future->cond);
            pthread_mutex_unlock(&task->future.string_future->mutex);
            tb_future_string_release_internal(task->future.string_future);
        } else if (task->kind == TB_TASK_KIND_I64_FROM_STRING && caught == 0) {
            int64_t result = task->function.i64_from_string_fn(task->arg.string_arg);
            tb_runtime_release(task->arg.string_arg);
            pthread_mutex_lock(&task->future.i64_future->mutex);
            task->future.i64_future->result = result;
            task->future.i64_future->failed = false;
            task->future.i64_future->done = true;
            pthread_cond_broadcast(&task->future.i64_future->cond);
            pthread_mutex_unlock(&task->future.i64_future->mutex);
            tb_future_i64_release_internal(task->future.i64_future);
        } else if (task->kind == TB_TASK_KIND_BOOL_FROM_STRING && caught == 0) {
            bool result = task->function.bool_from_string_fn(task->arg.string_arg);
            tb_runtime_release(task->arg.string_arg);
            pthread_mutex_lock(&task->future.bool_future->mutex);
            task->future.bool_future->result = result;
            task->future.bool_future->failed = false;
            task->future.bool_future->done = true;
            pthread_cond_broadcast(&task->future.bool_future->cond);
            pthread_mutex_unlock(&task->future.bool_future->mutex);
            tb_future_bool_release_internal(task->future.bool_future);
        } else if (task->kind == TB_TASK_KIND_STRING_FROM_STRING && caught == 0) {
            char* result = task->function.string_from_string_fn(task->arg.string_arg);
            tb_runtime_release(task->arg.string_arg);
            pthread_mutex_lock(&task->future.string_future->mutex);
            task->future.string_future->result = result;
            task->future.string_future->failed = false;
            task->future.string_future->done = true;
            pthread_cond_broadcast(&task->future.string_future->cond);
            pthread_mutex_unlock(&task->future.string_future->mutex);
            tb_future_string_release_internal(task->future.string_future);
        } else if (caught != 0) {
            char* error = __tb_exception_message;
            __tb_exception_message = NULL;
            if (task->kind == TB_TASK_KIND_I64_FROM_I64 || task->kind == TB_TASK_KIND_I64_FROM_BOOL || task->kind == TB_TASK_KIND_I64_FROM_STRING) {
                if (task->kind == TB_TASK_KIND_I64_FROM_STRING) {
                    tb_runtime_release(task->arg.string_arg);
                }
                pthread_mutex_lock(&task->future.i64_future->mutex);
                task->future.i64_future->failed = true;
                task->future.i64_future->error = error;
                task->future.i64_future->done = true;
                pthread_cond_broadcast(&task->future.i64_future->cond);
                pthread_mutex_unlock(&task->future.i64_future->mutex);
                tb_future_i64_release_internal(task->future.i64_future);
            } else if (task->kind == TB_TASK_KIND_BOOL_FROM_I64 || task->kind == TB_TASK_KIND_BOOL_FROM_BOOL || task->kind == TB_TASK_KIND_BOOL_FROM_STRING) {
                if (task->kind == TB_TASK_KIND_BOOL_FROM_STRING) {
                    tb_runtime_release(task->arg.string_arg);
                }
                pthread_mutex_lock(&task->future.bool_future->mutex);
                task->future.bool_future->failed = true;
                task->future.bool_future->error = error;
                task->future.bool_future->done = true;
                pthread_cond_broadcast(&task->future.bool_future->cond);
                pthread_mutex_unlock(&task->future.bool_future->mutex);
                tb_future_bool_release_internal(task->future.bool_future);
            } else {
                if (task->kind == TB_TASK_KIND_STRING_FROM_STRING) {
                    tb_runtime_release(task->arg.string_arg);
                }
                pthread_mutex_lock(&task->future.string_future->mutex);
                task->future.string_future->failed = true;
                task->future.string_future->error = error;
                task->future.string_future->done = true;
                pthread_cond_broadcast(&task->future.string_future->cond);
                pthread_mutex_unlock(&task->future.string_future->mutex);
                tb_future_string_release_internal(task->future.string_future);
            }
        }
        __tb_exception_handler = previous_handler;
        __tb_exception_message = previous_message;
        free(task);
    }
}

tb_thread_pool* tb_thread_pool_new(int64_t thread_count) {
    if (thread_count < 1) {
        thread_count = 1;
    }
    tb_thread_pool* pool = (tb_thread_pool*)malloc(sizeof(tb_thread_pool));
    pthread_mutex_init(&pool->mutex, NULL);
    pthread_cond_init(&pool->cond, NULL);
    pool->refcount = 1;
    pool->worker_count = (int)thread_count;
    pool->stop = false;
    pool->head = NULL;
    pool->tail = NULL;
    pool->workers = (pthread_t*)malloc(sizeof(pthread_t) * (size_t)pool->worker_count);
    for (int index = 0; index < pool->worker_count; index += 1) {
        pthread_create(&pool->workers[index], NULL, tb_thread_pool_worker, pool);
    }
    return pool;
}

tb_thread_pool* tb_thread_pool_retain(tb_thread_pool* pool) {
    if (pool == NULL) {
        return NULL;
    }
    pthread_mutex_lock(&pool->mutex);
    pool->refcount += 1;
    pthread_mutex_unlock(&pool->mutex);
    return pool;
}

void tb_thread_pool_release(tb_thread_pool* pool) {
    bool should_destroy = false;
    if (pool == NULL) {
        return;
    }
    pthread_mutex_lock(&pool->mutex);
    pool->refcount -= 1;
    should_destroy = pool->refcount == 0;
    if (should_destroy) {
        pool->stop = true;
        pthread_cond_broadcast(&pool->cond);
    }
    pthread_mutex_unlock(&pool->mutex);
    if (!should_destroy) {
        return;
    }
    for (int index = 0; index < pool->worker_count; index += 1) {
        pthread_join(pool->workers[index], NULL);
    }
    pthread_cond_destroy(&pool->cond);
    pthread_mutex_destroy(&pool->mutex);
    free(pool->workers);
    free(pool);
}

tb_future_i64* tb_thread_pool_submit_i64_i64(tb_thread_pool* pool, tb_i64_from_i64_task_fn function, int64_t arg) {
    tb_future_i64* future = (tb_future_i64*)malloc(sizeof(tb_future_i64));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = 0;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_I64_FROM_I64;
    task->arg.i64_arg = arg;
    task->function.i64_from_i64_fn = function;
    task->future.i64_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_i64* tb_thread_pool_submit_i64_bool(tb_thread_pool* pool, tb_i64_from_bool_task_fn function, bool arg) {
    tb_future_i64* future = (tb_future_i64*)malloc(sizeof(tb_future_i64));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = 0;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_I64_FROM_BOOL;
    task->arg.bool_arg = arg;
    task->function.i64_from_bool_fn = function;
    task->future.i64_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_bool* tb_thread_pool_submit_bool_i64(tb_thread_pool* pool, tb_bool_from_i64_task_fn function, int64_t arg) {
    tb_future_bool* future = (tb_future_bool*)malloc(sizeof(tb_future_bool));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = false;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_BOOL_FROM_I64;
    task->arg.i64_arg = arg;
    task->function.bool_from_i64_fn = function;
    task->future.bool_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_bool* tb_thread_pool_submit_bool_bool(tb_thread_pool* pool, tb_bool_from_bool_task_fn function, bool arg) {
    tb_future_bool* future = (tb_future_bool*)malloc(sizeof(tb_future_bool));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = false;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_BOOL_FROM_BOOL;
    task->arg.bool_arg = arg;
    task->function.bool_from_bool_fn = function;
    task->future.bool_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_string* tb_thread_pool_submit_string_i64(tb_thread_pool* pool, tb_string_from_i64_task_fn function, int64_t arg) {
    tb_future_string* future = (tb_future_string*)malloc(sizeof(tb_future_string));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = NULL;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_STRING_FROM_I64;
    task->arg.i64_arg = arg;
    task->function.string_from_i64_fn = function;
    task->future.string_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_string* tb_thread_pool_submit_string_bool(tb_thread_pool* pool, tb_string_from_bool_task_fn function, bool arg) {
    tb_future_string* future = (tb_future_string*)malloc(sizeof(tb_future_string));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = NULL;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_STRING_FROM_BOOL;
    task->arg.bool_arg = arg;
    task->function.string_from_bool_fn = function;
    task->future.string_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_i64* tb_thread_pool_submit_i64_string(tb_thread_pool* pool, tb_i64_from_string_task_fn function, char* arg) {
    tb_future_i64* future = (tb_future_i64*)malloc(sizeof(tb_future_i64));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = 0;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_I64_FROM_STRING;
    task->arg.string_arg = (char*)tb_runtime_retain(arg);
    task->function.i64_from_string_fn = function;
    task->future.i64_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_bool* tb_thread_pool_submit_bool_string(tb_thread_pool* pool, tb_bool_from_string_task_fn function, char* arg) {
    tb_future_bool* future = (tb_future_bool*)malloc(sizeof(tb_future_bool));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = false;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_BOOL_FROM_STRING;
    task->arg.string_arg = (char*)tb_runtime_retain(arg);
    task->function.bool_from_string_fn = function;
    task->future.bool_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_string* tb_thread_pool_submit_string_string(tb_thread_pool* pool, tb_string_from_string_task_fn function, char* arg) {
    tb_future_string* future = (tb_future_string*)malloc(sizeof(tb_future_string));
    pthread_mutex_init(&future->mutex, NULL);
    pthread_cond_init(&future->cond, NULL);
    future->refcount = 2;
    future->done = false;
    future->failed = false;
    future->error = NULL;
    future->result = NULL;

    tb_task* task = (tb_task*)malloc(sizeof(tb_task));
    task->kind = TB_TASK_KIND_STRING_FROM_STRING;
    task->arg.string_arg = (char*)tb_runtime_retain(arg);
    task->function.string_from_string_fn = function;
    task->future.string_future = future;
    task->next = NULL;

    pthread_mutex_lock(&pool->mutex);
    if (pool->tail == NULL) {
        pool->head = task;
        pool->tail = task;
    } else {
        pool->tail->next = task;
        pool->tail = task;
    }
    pthread_cond_signal(&pool->cond);
    pthread_mutex_unlock(&pool->mutex);
    return future;
}

tb_future_i64* tb_future_i64_retain(tb_future_i64* future) {
    if (future == NULL) {
        return NULL;
    }
    pthread_mutex_lock(&future->mutex);
    future->refcount += 1;
    pthread_mutex_unlock(&future->mutex);
    return future;
}

void tb_future_i64_release(tb_future_i64* future) {
    if (future == NULL) {
        return;
    }
    tb_future_i64_release_internal(future);
}

int64_t tb_future_i64_await(tb_future_i64* future) {
    int64_t result = 0;
    bool failed = false;
    char* error = NULL;
    pthread_mutex_lock(&future->mutex);
    while (!future->done) {
        pthread_cond_wait(&future->cond, &future->mutex);
    }
    failed = future->failed;
    error = future->error;
    result = future->result;
    pthread_mutex_unlock(&future->mutex);
    if (failed) {
        tb_rethrow_async_error(error);
    }
    return result;
}

tb_future_bool* tb_future_bool_retain(tb_future_bool* future) {
    if (future == NULL) {
        return NULL;
    }
    pthread_mutex_lock(&future->mutex);
    future->refcount += 1;
    pthread_mutex_unlock(&future->mutex);
    return future;
}

void tb_future_bool_release(tb_future_bool* future) {
    if (future == NULL) {
        return;
    }
    tb_future_bool_release_internal(future);
}

bool tb_future_bool_await(tb_future_bool* future) {
    bool result = false;
    bool failed = false;
    char* error = NULL;
    pthread_mutex_lock(&future->mutex);
    while (!future->done) {
        pthread_cond_wait(&future->cond, &future->mutex);
    }
    failed = future->failed;
    error = future->error;
    result = future->result;
    pthread_mutex_unlock(&future->mutex);
    if (failed) {
        tb_rethrow_async_error(error);
    }
    return result;
}

tb_future_string* tb_future_string_retain(tb_future_string* future) {
    if (future == NULL) {
        return NULL;
    }
    pthread_mutex_lock(&future->mutex);
    future->refcount += 1;
    pthread_mutex_unlock(&future->mutex);
    return future;
}

void tb_future_string_release(tb_future_string* future) {
    if (future == NULL) {
        return;
    }
    tb_future_string_release_internal(future);
}

char* tb_future_string_await(tb_future_string* future) {
    char* result = NULL;
    bool failed = false;
    char* error = NULL;
    pthread_mutex_lock(&future->mutex);
    while (!future->done) {
        pthread_cond_wait(&future->cond, &future->mutex);
    }
    failed = future->failed;
    error = future->error;
    result = future->result;
    if (!failed && result != NULL) {
        result = (char*)tb_runtime_retain(result);
    }
    pthread_mutex_unlock(&future->mutex);
    if (failed) {
        tb_rethrow_async_error(error);
    }
    return result;
}
