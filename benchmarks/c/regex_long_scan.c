#include <regex.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    regex_t full_pattern;
    regex_t search_pattern;
    char* full_text = (char*)malloc(8194);
    char* search_text = (char*)malloc(8194);
    if (full_text == NULL || search_text == NULL) {
        free(search_text);
        free(full_text);
        return 1;
    }
    memset(full_text, 'a', 8192);
    full_text[8192] = '\0';
    memset(search_text, 'b', 4096);
    for (int i = 0; i < 2048; ++i) {
        search_text[4096 + i * 2] = 'a';
        search_text[4096 + i * 2 + 1] = 'b';
    }
    search_text[8192] = 'z';
    search_text[8193] = '\0';

    if (regcomp(&full_pattern, "^(ab|ac|ad|ae|af|ag|ah|a)+z$", REG_EXTENDED | REG_NOSUB) != 0) {
        free(search_text);
        free(full_text);
        return 1;
    }
    if (regcomp(&search_pattern, "(ab|ac|ad|ae|af|ag|ah|a)+z", REG_EXTENDED | REG_NOSUB) != 0) {
        regfree(&full_pattern);
        free(search_text);
        free(full_text);
        return 1;
    }

    int full_matches = 0;
    int search_matches = 0;
    for (int iteration = 0; iteration < 1000; ++iteration) {
        full_matches += regexec(&full_pattern, full_text, 0, NULL, 0) == 0;
        search_matches += regexec(&search_pattern, search_text, 0, NULL, 0) == 0;
    }

    printf("%d\n%d\n", full_matches, search_matches);
    regfree(&search_pattern);
    regfree(&full_pattern);
    free(search_text);
    free(full_text);
    return 0;
}
