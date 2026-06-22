#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int64_t *values = malloc(30000 * sizeof(*values));
    int64_t seed = 1;
    int64_t total = 0;

    if (values == NULL) {
        return 1;
    }

    for (int64_t i = 0; i < 30000; ++i) {
        values[i] = (i * 31 + seed) % 997;
    }

    for (int64_t i = 0; i < 30000; ++i) {
        total += values[i] * (i % 13);
    }

    free(values);
    printf("%lld\n", (long long) total);
    return 0;
}
