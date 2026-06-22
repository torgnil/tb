#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int64_t build_value(int64_t round, int64_t index) {
    return (round * 17 + index * 31 + index * index) % 257;
}

static int compare_up(const void *left_ptr, const void *right_ptr) {
    int64_t left = *(const int64_t *) left_ptr;
    int64_t right = *(const int64_t *) right_ptr;
    if (left < right) {
        return -1;
    }
    if (left > right) {
        return 1;
    }
    return 0;
}

int main(void) {
    int64_t total = 0;
    int64_t values[64];

    for (int64_t round = 0; round < 1500; ++round) {
        for (int64_t index = 0; index < 64; ++index) {
            values[index] = build_value(round + 1, index);
        }
        qsort(values, 64, sizeof(values[0]), compare_up);
        total += values[0] + values[31] + values[63];
    }

    printf("%lld\n", (long long) total);
    return 0;
}
