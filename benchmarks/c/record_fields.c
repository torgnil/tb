#include <stdint.h>
#include <stdio.h>

typedef struct {
    int64_t x;
    int64_t y;
    int64_t z;
} Point;

static Point next_point(Point point, int64_t index) {
    Point result = {
        point.x + index % 7,
        point.y + index % 11,
        point.z + index % 13,
    };
    return result;
}

static int64_t score(Point point) {
    return point.x * 3 + point.y * 5 + point.z * 7;
}

int main(void) {
    Point point = {1, 2, 3};
    int64_t total = 0;
    for (int64_t i = 0; i < 50000; ++i) {
        point = next_point(point, i);
        total += score(point) % 1009;
    }
    printf("%lld\n", (long long) total);
    return 0;
}
