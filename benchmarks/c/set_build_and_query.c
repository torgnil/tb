#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>

int main(void) {
    bool seen[8192] = {false};
    int64_t total = 0;
    int64_t count = 0;

    for (int i = 0; i < 25001; ++i) {
        int key = (i * 29 + 1) % 8192;
        if (!seen[key]) {
            seen[key] = true;
            count += 1;
        }
    }

    for (int i = 0; i < 12000; ++i) {
        if (seen[(i * 7) % 8192]) {
            total += i % 41;
        }
    }

    printf("%lld\n", (long long) (total + count));
    return 0;
}
