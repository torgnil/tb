#ifndef TB_THREAD_POOL_COMPOSITE_RUNTIME_H
#define TB_THREAD_POOL_COMPOSITE_RUNTIME_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

static inline void* tb_thread_pool_checked_malloc(size_t size) {
    void* allocation = malloc(size);
    if (allocation == NULL) {
        fputs("thread_pool submission failed\n", stderr);
        exit(1);
    }
    return allocation;
}

static inline void* tb_thread_pool_checked_calloc(size_t count, size_t size) {
    void* allocation = calloc(count, size);
    if (allocation == NULL) {
        fputs("thread_pool submission failed\n", stderr);
        exit(1);
    }
    return allocation;
}

typedef struct tb_thread_pool_int_array {
    int32_t length;
    int32_t capacity;
    int64_t* data;
} tb_thread_pool_int_array;

typedef struct tb_thread_pool_int_array_array {
    int32_t length;
    void** data;
    unsigned char* owned;
} tb_thread_pool_int_array_array;

typedef struct tb_thread_pool_bool_array {
    int32_t length;
    bool* data;
} tb_thread_pool_bool_array;

typedef struct tb_thread_pool_bool_array_array {
    int32_t length;
    void** data;
    unsigned char* owned;
} tb_thread_pool_bool_array_array;

typedef struct tb_thread_pool_string_array {
    int32_t length;
    int32_t capacity;
    char** data;
    unsigned char* owned;
} tb_thread_pool_string_array;

void* tb_thread_pool_int_array_snapshot(void* raw_array);
void tb_thread_pool_int_array_snapshot_free(void* raw_array);
void* tb_thread_pool_int_array_array_snapshot(void* raw_array);
void tb_thread_pool_int_array_array_snapshot_free(void* raw_array);
void* tb_thread_pool_bool_array_snapshot(void* raw_array);
void tb_thread_pool_bool_array_snapshot_free(void* raw_array);
void* tb_thread_pool_bool_array_array_snapshot(void* raw_array);
void tb_thread_pool_bool_array_array_snapshot_free(void* raw_array);
void* tb_thread_pool_string_array_snapshot(void* raw_array);
void tb_thread_pool_string_array_snapshot_free(void* raw_array);

#endif
