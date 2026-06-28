#include <stdint.h>
#include <stdio.h>

typedef struct {
    int64_t count;
    int64_t total;
} Stat;

int main(void) {
    Stat stats[9] = {{0, 0}};
    int64_t total = 0;

    for (int i = 0; i < 5001; ++i) {
        int key = i % 9;
        int value = 10 + (i % 23);
        stats[key].count += 1;
        stats[key].total += value;
    }

    for (int i = 0; i < 9; ++i) {
        total += stats[i].count * stats[i].total;
    }

    printf("%lld\n", (long long) total);
    return 0;
}
