#include <regex.h>
#include <stdio.h>

int main(void) {
    int compiled = 0;
    for (int i = 0; i < 1000; ++i) {
        char pattern[64];
        regex_t regex;
        snprintf(pattern, sizeof(pattern), "[a-z]+[0-9]+x%d", i);
        if (regcomp(&regex, pattern, REG_EXTENDED | REG_NOSUB) != 0) {
            return 1;
        }
        ++compiled;
        regfree(&regex);
    }
    printf("%d\n", compiled);
    return 0;
}
