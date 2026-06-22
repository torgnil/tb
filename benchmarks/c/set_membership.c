#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SET_CAPACITY 8192

typedef struct {
    int32_t used[SET_CAPACITY];
    int64_t values[SET_CAPACITY];
    int32_t length;
} IntSet;

static uint32_t hash_int(int64_t value) {
    uint64_t x = (uint64_t) value;
    x ^= x >> 33;
    x *= 0xff51afd7ed558ccdULL;
    x ^= x >> 33;
    x *= 0xc4ceb9fe1a85ec53ULL;
    x ^= x >> 33;
    return (uint32_t) x;
}

static void set_init(IntSet *set) {
    memset(set, 0, sizeof(*set));
}

static void set_add(IntSet *set, int64_t value) {
    uint32_t index = hash_int(value) & (SET_CAPACITY - 1);
    while (set->used[index]) {
        if (set->values[index] == value) {
            return;
        }
        index = (index + 1) & (SET_CAPACITY - 1);
    }
    set->used[index] = 1;
    set->values[index] = value;
    set->length += 1;
}

static int set_contains(const IntSet *set, int64_t value) {
    uint32_t index = hash_int(value) & (SET_CAPACITY - 1);
    while (set->used[index]) {
        if (set->values[index] == value) {
            return 1;
        }
        index = (index + 1) & (SET_CAPACITY - 1);
    }
    return 0;
}

int main(void) {
    IntSet seen;
    int64_t seed = 1;
    int64_t total = 0;

    set_init(&seen);
    for (int64_t i = 0; i < 20000; ++i) {
        set_add(&seen, (i * 37 + seed) % 4096);
    }

    for (int64_t i = 0; i < 4096; ++i) {
        if (set_contains(&seen, i)) {
            total += i % 97;
        }
    }

    printf("%lld\n", (long long) (total + seen.length));
    return 0;
}
