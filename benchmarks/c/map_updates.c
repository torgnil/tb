#include <stdint.h>
#include <stdio.h>

int main(void) {
    int64_t counts[257] = {0};
    int64_t total = 0;

    for (int i = 0; i < 20001; ++i) {
        int key = (i * 17 + 1) % 257;
        counts[key] += 1;
    }

    for (int i = 0; i < 257; ++i) {
        total += counts[i] * (i % 13);
    }

    printf("%lld\n", (long long) total);
    return 0;
}
