#include <stdint.h>
#include <stdio.h>

int main(void) {
    int64_t total = 0;

    for (int i = 0; i < 3001; ++i) {
        int64_t left = 1000 + i;
        int64_t right = 2000 + (i % 97);
        total += left - right;
    }

    printf("%lld\n", (long long) total);
    return 0;
}
