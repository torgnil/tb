#ifndef TB_THREAD_POOL_COMPOSITE_RUNTIME_H
#define TB_THREAD_POOL_COMPOSITE_RUNTIME_H

#include <stdint.h>

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

void* tb_thread_pool_int_array_snapshot(void* raw_array);
void tb_thread_pool_int_array_snapshot_free(void* raw_array);
void* tb_thread_pool_int_array_array_snapshot(void* raw_array);
void tb_thread_pool_int_array_array_snapshot_free(void* raw_array);

#endif
