#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int is_name_char(char ch) {
    return isalnum((unsigned char) ch) || ch == '_';
}

static char *make_source(int repeats) {
    const char *part1 = "record Point(int x, int y);\n";
    const char *part2 = "int add(int left, int right) { return left + right; }\n";
    const char *format = "if (value_%d >= 10) { print(value_%d); }\n";
    size_t part1_len = strlen(part1);
    size_t part2_len = strlen(part2);
    size_t total = 1;

    for (int i = 0; i < repeats; ++i) {
        total += part1_len + part2_len + (size_t) snprintf(NULL, 0, format, i, i);
    }

    char *source = malloc(total);
    char *cursor = source;
    if (source == NULL) {
        return NULL;
    }

    for (int i = 0; i < repeats; ++i) {
        memcpy(cursor, part1, part1_len);
        cursor += part1_len;
        memcpy(cursor, part2, part2_len);
        cursor += part2_len;
        cursor += sprintf(cursor, format, i, i);
    }
    *cursor = '\0';
    return source;
}

int main(void) {
    char *source = make_source(81);
    int64_t tokens = 0;
    int64_t numbers = 0;
    size_t index = 0;
    size_t length;

    if (source == NULL) {
        return 1;
    }

    length = strlen(source);
    while (index < length) {
        char ch = source[index];
        if (isdigit((unsigned char) ch)) {
            numbers += 1;
            while (index < length && isdigit((unsigned char) source[index])) {
                index += 1;
            }
            tokens += 1;
        } else if (is_name_char(ch)) {
            while (index < length && is_name_char(source[index])) {
                index += 1;
            }
            tokens += 1;
        } else {
            if (!isspace((unsigned char) ch)) {
                tokens += 1;
            }
            index += 1;
        }
    }

    free(source);
    printf("%lld\n", (long long) (tokens * 1000 + numbers));
    return 0;
}
