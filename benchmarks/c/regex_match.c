#include <regex.h>
#include <stdio.h>

int main(void) {
    regex_t full_pattern;
    const char *samples[] = {"alpha", "12345", "ab!cd", "---", "----------------------------------------"};
    int full = 0;

    if (regcomp(&full_pattern, "^([a-z]+|[0-9]+)$", REG_EXTENDED | REG_NOSUB) != 0) {
        return 1;
    }
    for (int i = 0; i < 1000; ++i) {
        for (unsigned int j = 0; j < sizeof(samples) / sizeof(samples[0]); ++j) {
            full += regexec(&full_pattern, samples[j], 0, NULL, 0) == 0;
        }
    }
    regfree(&full_pattern);
    printf("%d\n", full);
    return 0;
}
