#include <errno.h>
#include <dirent.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <sys/stat.h>

static int tb_directory_name_compare(const void *left, const void *right) {
    const char *const *left_name = (const char *const *)left;
    const char *const *right_name = (const char *const *)right;
    return strcmp(*left_name, *right_name);
}

void tb_directory_list_free(char **names, int64_t count) {
    if (names == NULL) {
        return;
    }
    for (int64_t index = 0; index < count; index += 1) {
        free(names[index]);
    }
    free(names);
}

int tb_directory_list(const char *path, char ***names_out, int64_t *count_out) {
    if (path == NULL || names_out == NULL || count_out == NULL) {
        errno = EINVAL;
        return -1;
    }
    *names_out = NULL;
    *count_out = 0;

    DIR *directory = opendir(path);
    if (directory == NULL) {
        return -1;
    }

    char **names = NULL;
    size_t count = 0;
    size_t capacity = 0;
    int failure = 0;
    int failure_errno = 0;

    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (entry == NULL) {
            if (errno != 0) {
                failure = 1;
                failure_errno = errno;
            }
            break;
        }
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }

        if (count >= (size_t)INT32_MAX) {
            failure = 1;
            failure_errno = EOVERFLOW;
            break;
        }

        size_t name_length = strlen(entry->d_name);
        if (name_length == SIZE_MAX) {
            failure = 1;
            failure_errno = EOVERFLOW;
            break;
        }
        char *name_copy = (char *)malloc(name_length + 1);
        if (name_copy == NULL) {
            failure = 1;
            failure_errno = ENOMEM;
            break;
        }
        memcpy(name_copy, entry->d_name, name_length + 1);

        if (count == capacity) {
            size_t new_capacity = capacity == 0 ? 8 : capacity * 2;
            if (new_capacity < capacity || new_capacity > SIZE_MAX / sizeof(*names)) {
                free(name_copy);
                failure = 1;
                failure_errno = EOVERFLOW;
                break;
            }
            char **grown_names = (char **)realloc(names, new_capacity * sizeof(*names));
            if (grown_names == NULL) {
                free(name_copy);
                failure = 1;
                failure_errno = ENOMEM;
                break;
            }
            names = grown_names;
            capacity = new_capacity;
        }
        names[count] = name_copy;
        count += 1;
    }

    if (closedir(directory) != 0 && !failure) {
        failure = 1;
        failure_errno = errno;
    }
    if (failure) {
        tb_directory_list_free(names, (int64_t)count);
        errno = failure_errno;
        return -1;
    }

    if (count > 1) {
        qsort(names, count, sizeof(*names), tb_directory_name_compare);
    }
    *names_out = names;
    *count_out = (int64_t)count;
    return 0;
}

/* kind: 0 = any existing target, 1 = regular file, 2 = directory. */
int tb_path_test(const char *path, int32_t kind, int32_t *matches_out) {
    if (path == NULL || matches_out == NULL || kind < 0 || kind > 2) {
        errno = EINVAL;
        return -1;
    }
    *matches_out = 0;

    struct stat metadata;
    if (stat(path, &metadata) != 0) {
        if (errno == ENOENT || errno == ENOTDIR) {
            return 0;
        }
        return -1;
    }

    if (kind == 0 ||
        (kind == 1 && S_ISREG(metadata.st_mode)) ||
        (kind == 2 && S_ISDIR(metadata.st_mode))) {
        *matches_out = 1;
    }
    return 0;
}

static int tb_directory_ensure_component(const char *path) {
    if (mkdir(path, 0777) == 0) {
        return 0;
    }
    if (errno != EEXIST) {
        return -1;
    }

    struct stat metadata;
    if (stat(path, &metadata) != 0) {
        return -1;
    }
    if (!S_ISDIR(metadata.st_mode)) {
        errno = ENOTDIR;
        return -1;
    }
    return 0;
}

int tb_directory_ensure(const char *path) {
    if (path == NULL || path[0] == '\0') {
        errno = EINVAL;
        return -1;
    }

    size_t path_length = strlen(path);
    if (path_length == SIZE_MAX) {
        errno = EOVERFLOW;
        return -1;
    }
    char *path_copy = (char *)malloc(path_length + 1);
    if (path_copy == NULL) {
        errno = ENOMEM;
        return -1;
    }
    memcpy(path_copy, path, path_length + 1);

    int result = 0;
    int failure_errno = 0;
    for (size_t index = 0; index <= path_length; index += 1) {
        if (path_copy[index] != '/' && path_copy[index] != '\0') {
            continue;
        }

        char separator = path_copy[index];
        path_copy[index] = '\0';
        if (path_copy[0] != '\0' && tb_directory_ensure_component(path_copy) != 0) {
            failure_errno = errno;
            result = -1;
            path_copy[index] = separator;
            break;
        }
        path_copy[index] = separator;
    }

    if (result == 0) {
        failure_errno = errno;
    }
    free(path_copy);
    errno = failure_errno;
    return result;
}
