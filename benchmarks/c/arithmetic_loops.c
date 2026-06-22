#include <stdint.h>
#include <stdio.h>

static int64_t mix(int64_t value, int64_t index) {
    value = value + index * 17;
    value = value ^ (index << 2);
    value = value - (index % 11);
    return value & 1048575;
}

int main(void) {
    int64_t result = 1;
    for (int64_t i = 0; i < 200000; ++i) {
        result = mix(result, i);
    }
    printf("%lld\n", (long long) result);
    return 0;
}
