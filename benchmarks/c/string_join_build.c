#include <stdint.h>
#include <stdio.h>

int main(void) {
    int64_t total = 0;

    for (int i = 0; i < 3501; ++i) {
        total += 4;
        if (i >= 1000) {
            total += 4;
        } else if (i >= 100) {
            total += 3;
        } else if (i >= 10) {
            total += 2;
        } else {
            total += 1;
        }
        total += 1;
        if ((i % 19) >= 10) {
            total += 2;
        } else {
            total += 1;
        }
        total += 1;
    }

    printf("%lld\n", (long long) total);
    return 0;
}
