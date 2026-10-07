#include <stdint.h>
#include <stdio.h>

static int64_t build_value(int64_t round, int64_t index) {
    return (round * 17 + index * 31 + index * index) % 997;
}

static void push_max(int64_t values[], int64_t *length, int64_t value) {
    int64_t index = *length;
    *length += 1;

    while (index > 0) {
        int64_t parent = (index - 1) / 2;
        if (values[parent] >= value) {
            break;
        }
        values[index] = values[parent];
        index = parent;
    }
    values[index] = value;
}

static int64_t pop_max(int64_t values[], int64_t *length) {
    int64_t result = values[0];
    int64_t value = values[*length - 1];
    int64_t index = 0;
    *length -= 1;

    while (1) {
        int64_t left = index * 2 + 1;
        int64_t right = left + 1;
        int64_t child;
        if (left >= *length) {
            break;
        }
        child = left;
        if (right < *length && values[right] > values[left]) {
            child = right;
        }
        if (values[child] <= value) {
            break;
        }
        values[index] = values[child];
        index = child;
    }
    if (*length > 0) {
        values[index] = value;
    }
    return result;
}

int main(void) {
    int64_t total = 0;

    for (int64_t round = 0; round < 1200; ++round) {
        int64_t values[72];
        int64_t length = 0;

        for (int64_t index = 0; index < 64; ++index) {
            push_max(values, &length, build_value(round + 1, index));
        }
        for (int64_t index = 0; index < 8; ++index) {
            push_max(values, &length, build_value(round + 53, index + 71));
        }
        for (int64_t position = 1; length > 0; ++position) {
            total += pop_max(values, &length) * position;
        }
    }

    printf("%lld\n", (long long) total);
    return 0;
}
