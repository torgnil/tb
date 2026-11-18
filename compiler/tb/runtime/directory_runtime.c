#include <errno.h>
#include <dirent.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef _WIN32
#include <direct.h>
#include <windows.h>
#endif

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

static char *tb_directory_join_path(const char *directory, const char *name) {
    size_t directory_length = strlen(directory);
    size_t name_length = strlen(name);
    while (directory_length > 1 && directory[directory_length - 1] == '/') {
        directory_length -= 1;
    }

    int needs_separator = !(directory_length == 1 && directory[0] == '/');
    size_t separator_length = needs_separator ? 1 : 0;
    if (directory_length > SIZE_MAX - separator_length ||
        directory_length + separator_length > SIZE_MAX - name_length - 1) {
        errno = EOVERFLOW;
        return NULL;
    }

    size_t path_length = directory_length + separator_length + name_length;
    char *joined_path = (char *)malloc(path_length + 1);
    if (joined_path == NULL) {
        errno = ENOMEM;
        return NULL;
    }
    memcpy(joined_path, directory, directory_length);
    if (needs_separator) {
        joined_path[directory_length] = '/';
    }
    memcpy(joined_path + directory_length + separator_length, name, name_length + 1);
    return joined_path;
}

static int tb_directory_append_path(char ***paths, size_t *count, size_t *capacity,
                                    char *path) {
    if (*count >= (size_t)INT32_MAX) {
        errno = EOVERFLOW;
        return -1;
    }
    if (*count == *capacity) {
        size_t new_capacity = *capacity == 0 ? 8 : *capacity * 2;
        if (new_capacity < *capacity || new_capacity > (size_t)INT32_MAX) {
            new_capacity = (size_t)INT32_MAX;
        }
        if (new_capacity <= *capacity || new_capacity > SIZE_MAX / sizeof(**paths)) {
            errno = EOVERFLOW;
            return -1;
        }
        char **grown_paths = (char **)realloc(*paths, new_capacity * sizeof(**paths));
        if (grown_paths == NULL) {
            errno = ENOMEM;
            return -1;
        }
        *paths = grown_paths;
        *capacity = new_capacity;
    }
    (*paths)[*count] = path;
    *count += 1;
    return 0;
}

static int tb_directory_push_pending(char ***directories, size_t *count,
                                     size_t *capacity, char *directory) {
    if (*count >= (size_t)INT32_MAX) {
        errno = EOVERFLOW;
        return -1;
    }
    if (*count == *capacity) {
        size_t new_capacity = *capacity == 0 ? 8 : *capacity * 2;
        if (new_capacity < *capacity || new_capacity > (size_t)INT32_MAX) {
            new_capacity = (size_t)INT32_MAX;
        }
        if (new_capacity <= *capacity || new_capacity > SIZE_MAX / sizeof(**directories)) {
            errno = EOVERFLOW;
            return -1;
        }
        char **grown_directories = (char **)realloc(*directories,
                                                   new_capacity * sizeof(**directories));
        if (grown_directories == NULL) {
            errno = ENOMEM;
            return -1;
        }
        *directories = grown_directories;
        *capacity = new_capacity;
    }
    (*directories)[*count] = directory;
    *count += 1;
    return 0;
}

int tb_directory_walk(const char *path, char ***paths_out, int64_t *count_out) {
    if (path == NULL || paths_out == NULL || count_out == NULL) {
        errno = EINVAL;
        return -1;
    }
    *paths_out = NULL;
    *count_out = 0;

    char **paths = NULL;
    size_t path_count = 0;
    size_t path_capacity = 0;
    /* Pending entries borrow path strings owned by paths; string addresses stay stable on realloc. */
    char **pending_directories = NULL;
    size_t pending_count = 0;
    size_t pending_capacity = 0;
    char **names = NULL;
    int64_t name_count = 0;
    const char *current_directory = path;
    int failure_errno = 0;

    for (;;) {
        if (current_directory == NULL) {
            if (pending_count == 0) {
                break;
            }
            current_directory = pending_directories[--pending_count];
        }

        if (tb_directory_list(current_directory, &names, &name_count) != 0) {
            failure_errno = errno;
            goto failure;
        }

        for (int64_t index = 0; index < name_count; index += 1) {
            char *child_path = tb_directory_join_path(current_directory, names[index]);
            if (child_path == NULL) {
                failure_errno = errno;
                goto failure;
            }

#ifdef _WIN32
            DWORD attributes = GetFileAttributesA(child_path);
            if (attributes == INVALID_FILE_ATTRIBUTES) {
                failure_errno = EIO;
                free(child_path);
                goto failure;
            }
            int descend = (attributes & FILE_ATTRIBUTE_DIRECTORY) &&
                          !(attributes & FILE_ATTRIBUTE_REPARSE_POINT);
#else
            struct stat metadata;
            if (lstat(child_path, &metadata) != 0) {
                failure_errno = errno;
                free(child_path);
                goto failure;
            }
            int descend = S_ISDIR(metadata.st_mode);
#endif

            if (tb_directory_append_path(&paths, &path_count, &path_capacity,
                                         child_path) != 0) {
                failure_errno = errno;
                free(child_path);
                goto failure;
            }
            if (descend &&
                tb_directory_push_pending(&pending_directories, &pending_count,
                                          &pending_capacity, child_path) != 0) {
                failure_errno = errno;
                goto failure;
            }
        }

        tb_directory_list_free(names, name_count);
        names = NULL;
        name_count = 0;
        current_directory = NULL;
    }

    free(pending_directories);
    if (path_count > 1) {
        qsort(paths, path_count, sizeof(*paths), tb_directory_name_compare);
    }
    *paths_out = paths;
    *count_out = (int64_t)path_count;
    return 0;

failure:
    tb_directory_list_free(names, name_count);
    tb_directory_list_free(paths, (int64_t)path_count);
    free(pending_directories);
    errno = failure_errno;
    return -1;
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
#ifdef _WIN32
    int status = _mkdir(path);
#else
    int status = mkdir(path, 0777);
#endif
    if (status == 0) {
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

int tb_directory_remove_path(const char *path) {
    if (path == NULL) {
        errno = EINVAL;
        return -1;
    }
    return unlink(path);
}

int tb_directory_rename_path(const char *source, const char *destination) {
    if (source == NULL || destination == NULL) {
        errno = EINVAL;
        return -1;
    }
    return rename(source, destination);
}
