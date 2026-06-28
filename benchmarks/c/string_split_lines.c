#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *make_text(int repeats) {
    size_t total = 1;
    for (int i = 0; i < repeats; ++i) {
        total += (size_t) snprintf(NULL, 0, "line-%d-value-%d\n", i, i % 17);
    }

    char *text = malloc(total);
    char *cursor = text;
    if (text == NULL) {
        return NULL;
    }

    for (int i = 0; i < repeats; ++i) {
        cursor += sprintf(cursor, "line-%d-value-%d\n", i, i % 17);
    }
    *cursor = '\0';
    return text;
}

int main(void) {
    char *text = make_text(4001);
    int64_t total = 0;
    char *line;
    char *saveptr = NULL;

    if (text == NULL) {
        return 1;
    }

    line = strtok_r(text, "\n", &saveptr);
    while (line != NULL) {
        total += (int64_t) strlen(line);
        total += 4;
        total += 1;
        line = strtok_r(NULL, "\n", &saveptr);
    }

    free(text);
    printf("%lld\n", (long long) total);
    return 0;
}
