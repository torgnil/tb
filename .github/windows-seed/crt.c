#include <errno.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

_Static_assert(sizeof(jmp_buf) == 256, "Unexpected Windows x64 jmp_buf size");
_Static_assert(_Alignof(jmp_buf) == 16, "Unexpected Windows x64 jmp_buf alignment");

struct tb_timeval {
    int64_t seconds;
    int64_t microseconds;
};

int tb_windows_gettimeofday(struct tb_timeval *result, void *timezone) {
    (void)timezone;
    struct timespec now;
    if (timespec_get(&now, TIME_UTC) != TIME_UTC) {
        return -1;
    }
    result->seconds = now.tv_sec;
    result->microseconds = now.tv_nsec / 1000;
    return 0;
}

int64_t tb_windows_getline(char **buffer, size_t *capacity, FILE *stream) {
    size_t length = 0;
    int next;

    while ((next = fgetc(stream)) != EOF) {
        if (*buffer == NULL || length + 1 >= *capacity) {
            if (length >= SIZE_MAX / 2) {
                errno = ENOMEM;
                return -1;
            }
            size_t new_capacity = length < 64 ? 128 : (length + 1) * 2;
            char *grown = realloc(*buffer, new_capacity);
            if (grown == NULL) {
                return -1;
            }
            *buffer = grown;
            *capacity = new_capacity;
        }
        (*buffer)[length++] = (char)next;
        if (next == '\n') {
            break;
        }
    }

    if (length == 0 || ferror(stream)) {
        return -1;
    }
    (*buffer)[length] = '\0';
    return (int64_t)length;
}
