#include <stdint.h>
#include <stdio.h>

static int64_t step_a(int64_t value) {
    return (value * 3 + 7) % 1000003;
}

static int64_t step_b(int64_t value, int64_t index) {
    return step_a(value + index) ^ (index & 255);
}

static int64_t step_c(int64_t value, int64_t index) {
    return step_b(value, index) + step_a(index);
}

int main(void) {
    int64_t result = 1;
    for (int64_t i = 0; i < 120000; ++i) {
        result = step_c(result, i) % 1000003;
    }
    printf("%lld\n", (long long) result);
    return 0;
}
