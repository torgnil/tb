#include "thread_pool_composite_runtime.h"
#include <stdlib.h>
#include <string.h>

extern void* tb_runtime_retain(void* value);
extern void tb_runtime_release(void* value);

void* tb_thread_pool_int_array_snapshot(void* raw_array) {
    tb_thread_pool_int_array* source = (tb_thread_pool_int_array*)raw_array;
    if (source == NULL || source->length < 0) {
        return NULL;
    }
    tb_thread_pool_int_array* snapshot = (tb_thread_pool_int_array*)tb_thread_pool_checked_malloc(sizeof(tb_thread_pool_int_array));
    snapshot->length = source->length;
    snapshot->capacity = source->length;
    snapshot->data = source->length > 0
        ? (int64_t*)tb_thread_pool_checked_malloc((size_t)source->length * sizeof(int64_t))
        : NULL;
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

void* tb_thread_pool_bool_array_snapshot(void* raw_array) {
    tb_thread_pool_bool_array* source = (tb_thread_pool_bool_array*)raw_array;
    if (source == NULL || source->length < 0) {
        return NULL;
    }
    tb_thread_pool_bool_array* snapshot = (tb_thread_pool_bool_array*)tb_thread_pool_checked_malloc(sizeof(tb_thread_pool_bool_array));
    snapshot->length = source->length;
    snapshot->data = source->length > 0
        ? (bool*)tb_thread_pool_checked_malloc((size_t)source->length * sizeof(bool))
        : NULL;
    if (source->length > 0) {
        memcpy(snapshot->data, source->data, (size_t)source->length * sizeof(bool));
    }
    return snapshot;
}

void tb_thread_pool_bool_array_snapshot_free(void* raw_array) {
    tb_thread_pool_bool_array* array = (tb_thread_pool_bool_array*)raw_array;
    if (array == NULL) {
        return;
    }
    free(array->data);
    free(array);
}

void* tb_thread_pool_string_array_snapshot(void* raw_array) {
    tb_thread_pool_string_array* source = (tb_thread_pool_string_array*)raw_array;
    if (source == NULL || source->length < 0) {
        return NULL;
    }
    tb_thread_pool_string_array* snapshot = (tb_thread_pool_string_array*)tb_thread_pool_checked_malloc(sizeof(tb_thread_pool_string_array));
    snapshot->length = source->length;
    snapshot->capacity = source->length;
    size_t storage_length = source->length > 0 ? (size_t)source->length : 1;
    snapshot->data = (char**)tb_thread_pool_checked_calloc(storage_length, sizeof(char*));
    snapshot->owned = (unsigned char*)tb_thread_pool_checked_calloc(storage_length, sizeof(unsigned char));
    for (int32_t index = 0; index < source->length; index += 1) {
        if (source->data[index] != NULL) {
            snapshot->data[index] = (char*)tb_runtime_retain(source->data[index]);
            snapshot->owned[index] = 1;
        }
    }
    return snapshot;
}

void tb_thread_pool_string_array_snapshot_free(void* raw_array) {
    tb_thread_pool_string_array* array = (tb_thread_pool_string_array*)raw_array;
    if (array == NULL) {
        return;
    }
    for (int32_t index = 0; index < array->length; index += 1) {
        if (array->owned[index] != 0) {
            tb_runtime_release(array->data[index]);
        }
    }
    free(array->data);
    free(array->owned);
    free(array);
}

void* tb_thread_pool_int_array_array_snapshot(void* raw_array) {
    tb_thread_pool_int_array_array* source = (tb_thread_pool_int_array_array*)raw_array;
    if (source == NULL || source->length < 0) {
        return NULL;
    }
    tb_thread_pool_int_array_array* snapshot = (tb_thread_pool_int_array_array*)tb_thread_pool_checked_malloc(sizeof(tb_thread_pool_int_array_array));
    snapshot->length = source->length;
    snapshot->data = source->length > 0
        ? (void**)tb_thread_pool_checked_calloc((size_t)source->length, sizeof(void*))
        : NULL;
    snapshot->owned = source->length > 0
        ? (unsigned char*)tb_thread_pool_checked_calloc((size_t)source->length, sizeof(unsigned char))
        : NULL;
    for (int32_t index = 0; index < source->length; index += 1) {
        if (source->data[index] != NULL) {
            snapshot->data[index] = tb_thread_pool_int_array_snapshot(source->data[index]);
            if (snapshot->data[index] == NULL) {
                tb_thread_pool_int_array_array_snapshot_free(snapshot);
                return NULL;
            }
            snapshot->owned[index] = 1;
        }
    }
    return snapshot;
}

void tb_thread_pool_int_array_array_snapshot_free(void* raw_array) {
    tb_thread_pool_int_array_array* array = (tb_thread_pool_int_array_array*)raw_array;
    if (array == NULL) {
        return;
    }
    for (int32_t index = 0; index < array->length; index += 1) {
        if (array->owned[index] != 0) {
            tb_thread_pool_int_array_snapshot_free(array->data[index]);
        }
    }
    free(array->data);
    free(array->owned);
    free(array);
}
