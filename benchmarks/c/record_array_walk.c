#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int64_t x;
    int64_t y;
} Point;

int main(void) {
    Point *points = malloc(sizeof(Point) * 5000);
    int64_t total = 0;

    if (points == NULL) {
        return 1;
    }

    for (int i = 0; i < 5000; ++i) {
        points[i].x = i + 1;
        points[i].y = (i * 3) % 31;
    }

    for (int i = 0; i < 5000; ++i) {
        total += points[i].x + points[i].y * 2;
    }

    free(points);
    printf("%lld\n", (long long) total);
    return 0;
}
