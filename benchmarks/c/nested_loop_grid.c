#include <stdint.h>
#include <stdio.h>

int main(void) {
    int64_t total = 0;
    const int size = 73;

    for (int r = 0; r < size; ++r) {
        for (int c = 0; c < size; ++c) {
            int64_t value = (r * 7 + c * 11) % 23;
            total += value * (r + 1) - c;
        }
    }

    printf("%lld\n", (long long) total);
    return 0;
}
