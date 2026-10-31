#include <regex.h>
#include <stdio.h>

int main(void) {
    regex_t search_pattern;
    const char *samples[] = {"alpha", "12345", "ab!cd", "---", "----------------------------------------"};
    int contains = 0;

    if (regcomp(&search_pattern, "([a-z]+|[0-9]+)", REG_EXTENDED | REG_NOSUB) != 0) {
        return 1;
    }
    for (int i = 0; i < 1000; ++i) {
        for (unsigned int j = 0; j < sizeof(samples) / sizeof(samples[0]); ++j) {
            contains += regexec(&search_pattern, samples[j], 0, NULL, 0) == 0;
        }
    }
    regfree(&search_pattern);
    printf("%d\n", contains);
    return 0;
}
