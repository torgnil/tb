#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *make_chunk(int64_t index) {
    if (index % 5 == 0) {
        return "alpha";
    }
    if (index % 5 == 1) {
        return "beta";
    }
    if (index % 5 == 2) {
        return "gamma";
    }
    if (index % 5 == 3) {
        return "delta";
    }
    return "omega";
}

int main(void) {
    size_t capacity = 900 * 6 + 1;
    char *text = malloc(capacity);
    char *cursor = text;
    int64_t score = 0;

    if (text == NULL) {
        return 1;
    }

    for (int64_t i = 0; i < 900; ++i) {
        const char *chunk = make_chunk(i + 1);
        size_t len = strlen(chunk);
        memcpy(cursor, chunk, len);
        cursor += len;
        *cursor = ',';
        cursor += 1;
    }
    *cursor = '\0';

    for (int64_t i = 0; text[i] != '\0'; ++i) {
        if (text[i] == 'a') {
            score += i % 17;
        }
        if (text[i] == ',') {
            score += 1;
        }
    }

    free(text);
    printf("%lld\n", (long long) score);
    return 0;
}
