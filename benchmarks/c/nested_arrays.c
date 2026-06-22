#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static int64_t *make_row(int64_t row, int64_t width) {
    int64_t *result = malloc((size_t) width * sizeof(*result));
    if (result == NULL) {
        return NULL;
    }
    for (int64_t col = 0; col < width; ++col) {
        result[col] = (row * 17 + col * 31) % 101;
    }
    return result;
}

int main(void) {
    int64_t height = 121;
    int64_t width = 80;
    int64_t total = 0;
    int64_t **grid = malloc((size_t) height * sizeof(*grid));

    if (grid == NULL) {
        return 1;
    }

    for (int64_t row = 0; row < height; ++row) {
        grid[row] = make_row(row, width);
        if (grid[row] == NULL) {
            while (row > 0) {
                row -= 1;
                free(grid[row]);
            }
            free(grid);
            return 1;
        }
    }

    for (int64_t row = 0; row < height; ++row) {
        for (int64_t col = 0; col < width; ++col) {
            total += grid[row][col] * ((row + col) % 9);
        }
    }

    for (int64_t row = 0; row < height; ++row) {
        free(grid[row]);
    }
    free(grid);

    printf("%lld\n", (long long) total);
    return 0;
}
