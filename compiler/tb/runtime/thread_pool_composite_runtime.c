#include "thread_pool_composite_runtime.h"
#include <stdlib.h>
#include <string.h>

void* tb_thread_pool_int_array_snapshot(void* raw_array) {
    tb_thread_pool_int_array* source = (tb_thread_pool_int_array*)raw_array;
    if (source == NULL || source->length < 0) {
        return NULL;
    }
    tb_thread_pool_int_array* snapshot = (tb_thread_pool_int_array*)malloc(sizeof(tb_thread_pool_int_array));
    if (snapshot == NULL) {
        return NULL;
    }
    snapshot->length = source->length;
    snapshot->capacity = source->length;
    snapshot->data = (int64_t*)malloc((size_t)source->length * sizeof(int64_t));
    if (snapshot->data == NULL && source->length > 0) {
        free(snapshot);
        return NULL;
    }
    if (source->length > 0) {
        memcpy(snapshot->data, source->data, (size_t)source->length * sizeof(int64_t));
    }
    return snapshot;
}

void tb_thread_pool_int_array_snapshot_free(void* raw_array) {
    tb_thread_pool_int_array* array = (tb_thread_pool_int_array*)raw_array;
    if (array == NULL) {
        return;
    }
    free(array->data);
    free(array);
}
