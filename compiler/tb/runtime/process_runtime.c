#ifndef _WIN32
#if defined(__linux__)
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#endif
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

#define TB_PROCESS_TIMED_DRAIN_BUDGET (256U * 1024U)

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
} tb_process_buffer;

static int tb_process_move_fd_above_stdio(int *fd) {
    if (*fd > STDERR_FILENO) {
        return 0;
    }
    int moved = fcntl(*fd, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
    if (moved < 0) {
        return -1;
    }
    close(*fd);
    *fd = moved;
    return 0;
}

static void tb_process_close_fd(int *fd) {
    if (*fd >= 0) {
        close(*fd);
        *fd = -1;
    }
}

static int tb_process_set_cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
}

static int tb_process_set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int tb_process_add_chdir(posix_spawn_file_actions_t *actions,
                                const char *working_directory) {
#if defined(__APPLE__)
    return posix_spawn_file_actions_addchdir(actions, working_directory);
#elif defined(__GLIBC__)
    return posix_spawn_file_actions_addchdir_np(actions, working_directory);
#else
    (void)actions;
    (void)working_directory;
    return ENOTSUP;
#endif
}

static int tb_process_buffer_append(tb_process_buffer *buffer,
                                    const char *data, size_t length) {
    if (buffer->length == SIZE_MAX ||
        length > SIZE_MAX - buffer->length - 1) {
        errno = EOVERFLOW;
        return -1;
    }
    size_t needed = buffer->length + length + 1;
    if (needed > buffer->capacity) {
        size_t capacity = buffer->capacity == 0 ? 4096 : buffer->capacity;
        while (capacity < needed) {
            if (capacity > SIZE_MAX / 2) {
                capacity = needed;
                break;
            }
            capacity *= 2;
        }
        char *grown = (char *)realloc(buffer->data, capacity);
        if (grown == NULL) {
            errno = ENOMEM;
            return -1;
        }
        buffer->data = grown;
        buffer->capacity = capacity;
    }
    memcpy(buffer->data + buffer->length, data, length);
    buffer->length += length;
    buffer->data[buffer->length] = '\0';
    return 0;
}

/* Drain until would-block/EOF; timed calls yield after a bounded byte batch. */
static int tb_process_drain(int *fd, tb_process_buffer *buffer,
                            size_t yield_after_bytes) {
    char chunk[8192];
    size_t bytes_drained = 0;
    for (;;) {
        ssize_t read_count = read(*fd, chunk, sizeof(chunk));
        if (read_count > 0) {
            if (tb_process_buffer_append(buffer, chunk,
                                         (size_t)read_count) != 0) {
                return -1;
            }
            bytes_drained += (size_t)read_count;
            if (yield_after_bytes > 0 &&
                bytes_drained >= yield_after_bytes) {
                return 0;
            }
            continue;
        }
        if (read_count == 0) {
            tb_process_close_fd(fd);
            return 1;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return 0;
        }
        return -1;
    }
}

static void tb_process_reap_after_error(pid_t child, int *stdout_fd,
                                        int *stderr_fd, int process_group) {
    tb_process_close_fd(stdout_fd);
    tb_process_close_fd(stderr_fd);
    if (child <= 0) {
        return;
    }
    pid_t target = process_group ? -child : child;
    if (kill(target, SIGKILL) != 0 && errno != ESRCH && process_group) {
        kill(child, SIGKILL);
    }
    int status;
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {
    }
}

static int tb_process_deadline_after(int64_t timeout_ms,
                                     struct timespec *deadline) {
    if (clock_gettime(CLOCK_MONOTONIC, deadline) != 0) {
        return -1;
    }
    int64_t now_seconds = (int64_t)deadline->tv_sec;
    int64_t extra_seconds = timeout_ms / 1000;
    long extra_nanoseconds = (long)(timeout_ms % 1000) * 1000000L;
    if (extra_seconds > INT64_MAX - now_seconds) {
        deadline->tv_sec = (time_t)INT64_MAX;
        deadline->tv_nsec = 999999999L;
        return 0;
    }
    int64_t end_seconds = now_seconds + extra_seconds;
    long end_nanoseconds = deadline->tv_nsec + extra_nanoseconds;
    if (end_nanoseconds >= 1000000000L) {
        if (end_seconds == INT64_MAX) {
            deadline->tv_sec = (time_t)INT64_MAX;
            deadline->tv_nsec = 999999999L;
            return 0;
        }
        end_seconds += 1;
        end_nanoseconds -= 1000000000L;
    }
    deadline->tv_sec = (time_t)end_seconds;
    deadline->tv_nsec = end_nanoseconds;
    return 0;
}

static int tb_process_remaining_ms(const struct timespec *deadline,
                                   int *remaining_ms) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        return -1;
    }
    int64_t seconds = (int64_t)deadline->tv_sec - (int64_t)now.tv_sec;
    int64_t nanoseconds = (int64_t)deadline->tv_nsec - (int64_t)now.tv_nsec;
    if (nanoseconds < 0) {
        seconds -= 1;
        nanoseconds += 1000000000;
    }
    if (seconds < 0 || (seconds == 0 && nanoseconds <= 0)) {
        *remaining_ms = 0;
        return 0;
    }
    if (seconds > INT32_MAX / 1000) {
        *remaining_ms = INT32_MAX;
        return 0;
    }
    int64_t milliseconds = seconds * 1000 + (nanoseconds + 999999) / 1000000;
    *remaining_ms = milliseconds > INT32_MAX ? INT32_MAX : (int)milliseconds;
    return 0;
}

static int tb_process_kill_group(pid_t child) {
    if (kill(-child, SIGKILL) == 0 || errno == ESRCH) {
        return 0;
    }
    return -1;
}

static int tb_process_child_exited(pid_t child, int *child_exited) {
    siginfo_t status = {0};
    int result;
    do {
        result = waitid(P_PID, (id_t)child, &status,
                        WEXITED | WNOHANG | WNOWAIT);
    } while (result != 0 && errno == EINTR);
    if (result != 0) {
        return -1;
    }
    *child_exited = status.si_pid == child;
    return 0;
}

static int tb_process_finish_buffer(tb_process_buffer *buffer) {
    if (buffer->data != NULL) {
        return 0;
    }
    buffer->data = (char *)malloc(1);
    if (buffer->data == NULL) {
        errno = ENOMEM;
        return -1;
    }
    buffer->data[0] = '\0';
    buffer->capacity = 1;
    return 0;
}

/*
 * `arguments` points at an array of NUL-terminated strings. It is not
 * modified or retained. A non-NULL `input` is a borrowed NUL-terminated string
 * supplied to child stdin; NULL preserves inherited stdin. A non-NULL
 * `working_directory` is a borrowed NUL-terminated path used for the child
 * cwd; NULL inherits the parent cwd. `environment_count` is -1 to inherit the
 * parent environment, otherwise it gives the length of the supplied borrowed
 * environment entries. `timeout_ms` is -1 for an untimed call, otherwise a
 * nonnegative deadline in milliseconds. Timed calls return whether that
 * deadline expired through `timed_out_out`. On success, the caller owns both
 * output buffers. The return value is zero on success and a nonzero error
 * number on failure.
 */
int tb_process_run(const char *const *arguments, int32_t argument_count,
                   const char *input, const char *working_directory,
                   int64_t timeout_ms,
                   const char *const *environment, int32_t environment_count,
                   int64_t *exit_code_out,
                   int32_t *timed_out_out,
                   char **stdout_out, char **stderr_out) {
    if (arguments == NULL || argument_count <= 0 || timeout_ms < -1 ||
        environment_count < -1 ||
        (environment_count > 0 && environment == NULL) ||
        exit_code_out == NULL || timed_out_out == NULL || stdout_out == NULL ||
        stderr_out == NULL || arguments[0] == NULL || arguments[0][0] == '\0') {
        return EINVAL;
    }
    *stdout_out = NULL;
    *stderr_out = NULL;
    *timed_out_out = 0;

    size_t argv_count = (size_t)argument_count;
    if (argv_count > SIZE_MAX / sizeof(char *) - 1) {
        return EOVERFLOW;
    }
    char **argv = (char **)malloc((argv_count + 1) * sizeof(char *));
    if (argv == NULL) {
        return ENOMEM;
    }
    for (size_t index = 0; index < argv_count; index += 1) {
        if (arguments[index] == NULL) {
            free(argv);
            return EINVAL;
        }
        argv[index] = (char *)arguments[index];
    }
    argv[argv_count] = NULL;

    char **environment_copy = NULL;
    if (environment_count >= 0) {
        size_t supplied_environment_count = (size_t)environment_count;
        if (supplied_environment_count > SIZE_MAX / sizeof(char *) - 1) {
            free(argv);
            return EOVERFLOW;
        }
        environment_copy = (char **)malloc(
            (supplied_environment_count + 1) * sizeof(char *));
        if (environment_copy == NULL) {
            free(argv);
            return ENOMEM;
        }
        for (size_t index = 0; index < supplied_environment_count; index += 1) {
            if (environment[index] == NULL) {
                free(environment_copy);
                free(argv);
                return EINVAL;
            }
            environment_copy[index] = (char *)environment[index];
        }
        environment_copy[supplied_environment_count] = NULL;
    }

    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    FILE *input_file = NULL;
    int input_fd = -1;
    tb_process_buffer stdout_buffer = {NULL, 0, 0};
    tb_process_buffer stderr_buffer = {NULL, 0, 0};
    pid_t child = -1;
    int use_process_group = timeout_ms >= 0;
    int timed_out = 0;
    int child_exited = 0;
    int wait_status = 0;
    int failed = 0;
    int failure_errno = 0;
    char *const *child_environment = environment_count < 0
                                         ? environ
                                         : environment_copy;

    if (input != NULL) {
        input_file = tmpfile();
        if (input_file == NULL) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
        size_t input_length = strlen(input);
        if ((input_length > 0 &&
             fwrite(input, 1, input_length, input_file) != input_length) ||
            fflush(input_file) != 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
        int file_descriptor = fileno(input_file);
        if (file_descriptor < 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
        if (tb_process_set_cloexec(file_descriptor) != 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
        input_fd = fcntl(file_descriptor, F_DUPFD_CLOEXEC,
                         STDERR_FILENO + 1);
        if (input_fd < 0 || lseek(input_fd, 0, SEEK_SET) < 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
        FILE *completed_input_file = input_file;
        input_file = NULL;
        if (fclose(completed_input_file) != 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
    }

    if (pipe(stdout_pipe) != 0 || pipe(stderr_pipe) != 0) {
        failed = 1;
        failure_errno = errno;
        goto done;
    }
    for (int index = 0; index < 2; index += 1) {
        if (tb_process_move_fd_above_stdio(&stdout_pipe[index]) != 0 ||
            tb_process_move_fd_above_stdio(&stderr_pipe[index]) != 0 ||
            tb_process_set_cloexec(stdout_pipe[index]) != 0 ||
            tb_process_set_cloexec(stderr_pipe[index]) != 0) {
            failed = 1;
            failure_errno = errno;
            goto done;
        }
    }
    if (tb_process_set_nonblocking(stdout_pipe[0]) != 0 ||
        tb_process_set_nonblocking(stderr_pipe[0]) != 0) {
        failed = 1;
        failure_errno = errno;
        goto done;
    }

    posix_spawn_file_actions_t actions;
    int spawn_error = posix_spawn_file_actions_init(&actions);
    if (spawn_error != 0) {
        failed = 1;
        failure_errno = spawn_error;
        goto done;
    }
    if (working_directory != NULL) {
        spawn_error = tb_process_add_chdir(&actions, working_directory);
    }
    if (spawn_error == 0) {
        spawn_error = posix_spawn_file_actions_adddup2(
            &actions, stdout_pipe[1], STDOUT_FILENO);
    }
    if (spawn_error == 0) {
        spawn_error = posix_spawn_file_actions_adddup2(
            &actions, stderr_pipe[1], STDERR_FILENO);
    }
    if (spawn_error == 0 && input_fd >= 0) {
        spawn_error = posix_spawn_file_actions_adddup2(
            &actions, input_fd, STDIN_FILENO);
    }
    int pipe_fds[] = {stdout_pipe[0], stdout_pipe[1],
                      stderr_pipe[0], stderr_pipe[1]};
    for (size_t index = 0; spawn_error == 0 && index < 4; index += 1) {
        spawn_error = posix_spawn_file_actions_addclose(&actions,
                                                        pipe_fds[index]);
    }
    if (spawn_error == 0 && input_fd >= 0) {
        spawn_error = posix_spawn_file_actions_addclose(&actions, input_fd);
    }
    posix_spawnattr_t attributes;
    int attributes_initialized = 0;
    posix_spawnattr_t *spawn_attributes = NULL;
    if (spawn_error == 0 && use_process_group) {
        spawn_error = posix_spawnattr_init(&attributes);
        if (spawn_error == 0) {
            attributes_initialized = 1;
            spawn_attributes = &attributes;
            spawn_error = posix_spawnattr_setpgroup(&attributes, 0);
        }
        if (spawn_error == 0) {
            spawn_error = posix_spawnattr_setflags(
                &attributes, POSIX_SPAWN_SETPGROUP);
        }
    }
    if (spawn_error == 0) {
        spawn_error = posix_spawnp(&child, argv[0], &actions,
                                   spawn_attributes, argv,
                                   child_environment);
    }
    if (attributes_initialized) {
        posix_spawnattr_destroy(&attributes);
    }
    posix_spawn_file_actions_destroy(&actions);
    tb_process_close_fd(&input_fd);
    if (spawn_error != 0) {
        failed = 1;
        failure_errno = spawn_error;
        goto done;
    }

    tb_process_close_fd(&stdout_pipe[1]);
    tb_process_close_fd(&stderr_pipe[1]);
    struct timespec deadline;
    if (timeout_ms >= 0 &&
        tb_process_deadline_after(timeout_ms, &deadline) != 0) {
        failed = 1;
        failure_errno = errno;
    }
    if (!failed && timeout_ms == 0) {
        timed_out = 1;
        if (tb_process_kill_group(child) != 0) {
            failed = 1;
            failure_errno = errno;
        }
    }
    while (!failed && !timed_out &&
           (stdout_pipe[0] >= 0 || stderr_pipe[0] >= 0 ||
            (timeout_ms >= 0 && !child_exited))) {
        if (timeout_ms >= 0 && !child_exited) {
            if (tb_process_child_exited(child, &child_exited) != 0) {
                failed = 1;
                failure_errno = errno;
                break;
            }
        }
        if (child_exited && stdout_pipe[0] < 0 && stderr_pipe[0] < 0) {
            break;
        }
        struct pollfd pipes[2];
        pipes[0].fd = stdout_pipe[0];
        pipes[0].events = POLLIN | POLLHUP;
        pipes[0].revents = 0;
        pipes[1].fd = stderr_pipe[0];
        pipes[1].events = POLLIN | POLLHUP;
        pipes[1].revents = 0;
        int wait_ms = -1;
        if (timeout_ms >= 0 &&
            tb_process_remaining_ms(&deadline, &wait_ms) != 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
        if (timeout_ms >= 0 && wait_ms == 0) {
            timed_out = 1;
            if (tb_process_kill_group(child) != 0) {
                failed = 1;
                failure_errno = errno;
            }
            break;
        }
        if (timeout_ms >= 0 && stdout_pipe[0] < 0 && stderr_pipe[0] < 0 &&
            wait_ms > 10) {
            wait_ms = 10;
        }
        int poll_result = poll(pipes, 2, wait_ms);
        if (poll_result < 0 && errno == EINTR) {
            continue;
        }
        if (poll_result < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
        if (poll_result == 0) {
            continue;
        }
        if (stdout_pipe[0] >= 0 && pipes[0].revents != 0 &&
            tb_process_drain(&stdout_pipe[0], &stdout_buffer,
                             timeout_ms >= 0
                                 ? TB_PROCESS_TIMED_DRAIN_BUDGET : 0) < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
        if (stderr_pipe[0] >= 0 && pipes[1].revents != 0 &&
            tb_process_drain(&stderr_pipe[0], &stderr_buffer,
                             timeout_ms >= 0
                                 ? TB_PROCESS_TIMED_DRAIN_BUDGET : 0) < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
    }

    if (timed_out && !failed) {
        if ((stdout_pipe[0] >= 0 &&
             tb_process_drain(&stdout_pipe[0], &stdout_buffer,
                              TB_PROCESS_TIMED_DRAIN_BUDGET) < 0) ||
            (stderr_pipe[0] >= 0 &&
             tb_process_drain(&stderr_pipe[0], &stderr_buffer,
                              TB_PROCESS_TIMED_DRAIN_BUDGET) < 0)) {
            failed = 1;
            failure_errno = errno;
        }
        tb_process_close_fd(&stdout_pipe[0]);
        tb_process_close_fd(&stderr_pipe[0]);
    }

    if (failed) {
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0],
                                    use_process_group);
        child = -1;
        goto done;
    }

    pid_t waited;
    do {
        waited = waitpid(child, &wait_status, 0);
    } while (waited < 0 && errno == EINTR);
    if (waited < 0) {
        failed = 1;
        failure_errno = errno;
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0],
                                    use_process_group);
        child = -1;
        goto done;
    }
    child = -1;
    *timed_out_out = timed_out;
    if (WIFEXITED(wait_status)) {
        *exit_code_out = (int64_t)WEXITSTATUS(wait_status);
    } else if (WIFSIGNALED(wait_status)) {
        *exit_code_out = -(int64_t)WTERMSIG(wait_status);
    } else {
        failed = 1;
        failure_errno = ECHILD;
        goto done;
    }
    if (tb_process_finish_buffer(&stdout_buffer) != 0 ||
        tb_process_finish_buffer(&stderr_buffer) != 0) {
        failed = 1;
        failure_errno = errno;
        goto done;
    }

    *stdout_out = stdout_buffer.data;
    *stderr_out = stderr_buffer.data;
    stdout_buffer.data = NULL;
    stderr_buffer.data = NULL;

done:
    if (failed && child > 0) {
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0],
                                    use_process_group);
    }
    tb_process_close_fd(&input_fd);
    if (input_file != NULL) {
        fclose(input_file);
    }
    tb_process_close_fd(&stdout_pipe[0]);
    tb_process_close_fd(&stdout_pipe[1]);
    tb_process_close_fd(&stderr_pipe[0]);
    tb_process_close_fd(&stderr_pipe[1]);
    free(stdout_buffer.data);
    free(stderr_buffer.data);
    free(environment_copy);
    free(argv);
    if (failed) {
        return failure_errno == 0 ? EIO : failure_errno;
    }
    return 0;
}

#else

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

typedef struct {
    char *data;
    size_t length;
    size_t capacity;
    HANDLE read_end;
    HANDLE write_end;
    int eof;
} tb_windows_capture;

static wchar_t *tb_process_widen(const char *text) {
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, NULL, 0);
    if (!size) {
        errno = EINVAL;
        return NULL;
    }
    wchar_t *wide = malloc((size_t)size * sizeof(*wide));
    if (wide == NULL) {
        return NULL;
    }
    if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text, -1, wide, size)) {
        free(wide);
        errno = EINVAL;
        return NULL;
    }
    return wide;
}

static wchar_t *tb_process_directory(const char *path) {
    wchar_t *relative = tb_process_widen(path);
    if (!relative) {
        return NULL;
    }
    DWORD size = GetFullPathNameW(relative, 0, NULL, NULL);
    wchar_t *full = size ? malloc((size_t)size * sizeof(*full)) : NULL;
    if (full) {
        DWORD length = GetFullPathNameW(relative, size, full, NULL);
        if (!length || length >= size) {
            free(full);
            full = NULL;
        }
    }
    free(relative);
    return full;
}

/* Quote each argument according to the Windows C runtime argv rules. */
static wchar_t *tb_process_command(const char *const *arguments, int32_t count) {
    const size_t capacity = 32767;
    wchar_t *command = malloc(capacity * sizeof(*command));
    if (!command) {
        return NULL;
    }
    size_t used = 0;
    for (int32_t i = 0; i < count; ++i) {
        wchar_t *arg = tb_process_widen(arguments[i]);
        if (!arg) {
            free(command);
            return NULL;
        }
        size_t length = wcslen(arg);
        if (capacity - used < 4 || length > (capacity - used - 4) / 2) {
            free(arg);
            free(command);
            errno = E2BIG;
            return NULL;
        }
        if (i) {
            command[used++] = L' ';
        }
        command[used++] = L'"';
        size_t slashes = 0;
        for (size_t j = 0; j <= length; ++j) {
            wchar_t ch = arg[j];
            if (ch == L'\\') {
                ++slashes;
                continue;
            }
            size_t escaped = (ch == L'"' || ch == L'\0') ? slashes * 2 : slashes;
            for (size_t k = 0; k < escaped; ++k) {
                command[used++] = L'\\';
            }
            slashes = 0;
            if (ch == L'"') {
                command[used++] = L'\\';
            }
            if (ch) {
                command[used++] = ch;
            }
        }
        command[used++] = L'"';
        free(arg);
    }
    command[used] = 0;
    return command;
}

static int tb_process_env_order(const void *a, const void *b) {
    const wchar_t *left = *(const wchar_t *const *)a;
    const wchar_t *right = *(const wchar_t *const *)b;
    return CompareStringOrdinal(left, -1, right, -1, TRUE) - CSTR_EQUAL;
}

static wchar_t *tb_process_environment(const char *const *entries, int32_t count) {
    wchar_t **values = calloc(count ? (size_t)count : 1, sizeof(*values));
    if (!values) {
        return NULL;
    }
    size_t length = 2;
    wchar_t *block = NULL;
    for (int32_t i = 0; i < count; ++i) {
        values[i] = tb_process_widen(entries[i]);
        if (!values[i]) {
            goto done;
        }
        size_t entry_length = wcslen(values[i]) + 1;
        if (entry_length > SIZE_MAX / sizeof(wchar_t) - length) {
            errno = E2BIG;
            goto done;
        }
        length += entry_length;
    }
    qsort(values, (size_t)count, sizeof(*values), tb_process_env_order);
    block = calloc(length, sizeof(*block));
    if (block) {
        wchar_t *next = block;
        for (int32_t i = 0; i < count; ++i) {
            size_t entry_length = wcslen(values[i]) + 1;
            memcpy(next, values[i], entry_length * sizeof(*next));
            next += entry_length;
        }
    }
done:
    for (int32_t i = 0; i < count; ++i) {
        free(values[i]);
    }
    free(values);
    return block;
}

static int tb_process_open_capture(tb_windows_capture *capture, SECURITY_ATTRIBUTES *security) {
    return CreatePipe(&capture->read_end, &capture->write_end, security, 0) &&
           SetHandleInformation(capture->read_end, HANDLE_FLAG_INHERIT, 0);
}

static int tb_process_read_capture(tb_windows_capture *capture) {
    if (capture->eof) {
        return 1;
    }
    DWORD available = 0;
    if (!PeekNamedPipe(capture->read_end, NULL, 0, NULL, &available, NULL)) {
        capture->eof = GetLastError() == ERROR_BROKEN_PIPE;
        return capture->eof;
    }
    if (!available) {
        return 1;
    }
    DWORD amount = available > 65536 ? 65536 : available;
    if (capture->length > SIZE_MAX - amount - 1) {
        return 0;
    }
    size_t needed = capture->length + amount + 1;
    if (needed > capture->capacity) {
        size_t capacity = needed <= SIZE_MAX / 2 ? needed * 2 : needed;
        char *grown = realloc(capture->data, capacity);
        if (!grown) {
            return 0;
        }
        capture->data = grown;
        capture->capacity = capacity;
    }
    DWORD read = 0;
    if (!ReadFile(capture->read_end, capture->data + capture->length, amount, &read, NULL)) {
        return 0;
    }
    capture->length += read;
    return 1;
}

static HANDLE tb_process_input(const char *input, SECURITY_ATTRIBUTES *security) {
    if (input) {
        wchar_t directory[MAX_PATH], path[MAX_PATH];
        DWORD size = GetTempPathW(MAX_PATH, directory);
        if (!size || size >= MAX_PATH || !GetTempFileNameW(directory, L"tb", 0, path)) {
            return INVALID_HANDLE_VALUE;
        }
        HANDLE file = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_DELETE,
                                  security, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_TEMPORARY | FILE_FLAG_DELETE_ON_CLOSE, NULL);
        if (file == INVALID_HANDLE_VALUE) {
            DeleteFileW(path);
            return file;
        }
        size_t remaining = strlen(input);
        while (remaining) {
            DWORD amount = remaining > 65536 ? 65536 : (DWORD)remaining;
            DWORD written = 0;
            if (!WriteFile(file, input, amount, &written, NULL) || written != amount) {
                CloseHandle(file);
                return INVALID_HANDLE_VALUE;
            }
            input += written;
            remaining -= written;
        }
        LARGE_INTEGER start = {0};
        if (!SetFilePointerEx(file, start, NULL, FILE_BEGIN)) {
            CloseHandle(file);
            return INVALID_HANDLE_VALUE;
        }
        return file;
    }
    HANDLE source = GetStdHandle(STD_INPUT_HANDLE);
    if (!source || source == INVALID_HANDLE_VALUE) {
        return CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
                           security, OPEN_EXISTING, 0, NULL);
    }
    HANDLE duplicate = INVALID_HANDLE_VALUE;
    if (!DuplicateHandle(GetCurrentProcess(), source, GetCurrentProcess(), &duplicate,
                         0, TRUE, DUPLICATE_SAME_ACCESS)) {
        return INVALID_HANDLE_VALUE;
    }
    return duplicate;
}

static void tb_process_close(HANDLE handle) {
    if (handle && handle != INVALID_HANDLE_VALUE) {
        CloseHandle(handle);
    }
}

int tb_process_run(const char *const *arguments, int32_t argument_count,
                   const char *input, const char *working_directory,
                   int64_t timeout_ms, const char *const *environment, int32_t environment_count,
                   int64_t *exit_code_out, int32_t *timed_out_out,
                   char **stdout_out, char **stderr_out) {
    if (!arguments || argument_count <= 0 || timeout_ms < -1 || environment_count < -1 ||
        (environment_count > 0 && !environment) || !exit_code_out || !timed_out_out ||
        !stdout_out || !stderr_out || !arguments[0] || !arguments[0][0]) {
        return EINVAL;
    }
    *stdout_out = NULL;
    *stderr_out = NULL;
    *timed_out_out = 0;
    for (int32_t i = 0; i < argument_count; ++i) {
        if (!arguments[i]) {
            return EINVAL;
        }
    }
    for (int32_t i = 0; i < environment_count; ++i) {
        if (!environment[i]) {
            return EINVAL;
        }
    }

    int status = EIO;
    wchar_t *command = tb_process_command(arguments, argument_count);
    wchar_t *directory = working_directory ? tb_process_directory(working_directory) : NULL;
    wchar_t *env = environment_count >= 0 ? tb_process_environment(environment, environment_count) : NULL;
    tb_windows_capture out = {0}, err = {0};
    SECURITY_ATTRIBUTES security = {sizeof(security), NULL, TRUE};
    STARTUPINFOEXW startup = {0};
    startup.StartupInfo.cb = sizeof(startup);
    PROCESS_INFORMATION child = {0};
    HANDLE job = NULL;
    HANDLE in = INVALID_HANDLE_VALUE;
    SIZE_T bytes = 0;
    LPPROC_THREAD_ATTRIBUTE_LIST attributes = NULL;
    if (!command || (working_directory && !directory) || (environment_count >= 0 && !env)) {
        status = errno ? errno : ENOMEM;
        goto done;
    }
    in = tb_process_input(input, &security);
    if (in == INVALID_HANDLE_VALUE || !tb_process_open_capture(&out, &security) ||
        !tb_process_open_capture(&err, &security)) {
        goto done;
    }
    HANDLE handles[] = {in, out.write_end, err.write_end};
    InitializeProcThreadAttributeList(NULL, 1, 0, &bytes);
    if (!bytes || !(attributes = malloc(bytes)) ||
        !InitializeProcThreadAttributeList(attributes, 1, 0, &bytes)) {
        goto done;
    }
    startup.lpAttributeList = attributes;
    if (!UpdateProcThreadAttribute(attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                   handles, sizeof(handles), NULL, NULL)) {
        goto done;
    }
    startup.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    startup.StartupInfo.hStdInput = in;
    startup.StartupInfo.hStdOutput = out.write_end;
    startup.StartupInfo.hStdError = err.write_end;
    if (timeout_ms >= 0) {
        job = CreateJobObjectW(NULL, NULL);
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit = {0};
        limit.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                             &limit, sizeof(limit))) {
            goto done;
        }
    }
    DWORD flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_SUSPENDED;
    if (!CreateProcessW(NULL, command, NULL, NULL, TRUE, flags, env, directory,
                        &startup.StartupInfo, &child)) {
        goto done;
    }
    if ((job && !AssignProcessToJobObject(job, child.hProcess)) ||
        ResumeThread(child.hThread) == (DWORD)-1) {
        goto done;
    }
    tb_process_close(out.write_end);
    out.write_end = NULL;
    tb_process_close(err.write_end);
    err.write_end = NULL;

    ULONGLONG started = GetTickCount64();
    for (;;) {
        DWORD state = WaitForSingleObject(child.hProcess, 0);
        if (state == WAIT_FAILED) {
            goto done;
        }
        size_t before_out = out.length, before_err = err.length;
        if (!tb_process_read_capture(&out) || !tb_process_read_capture(&err)) {
            goto done;
        }
        if (state == WAIT_OBJECT_0 && out.eof && err.eof) {
            break;
        }
        if (job && !*timed_out_out && GetTickCount64() - started >= (uint64_t)timeout_ms &&
            (state != WAIT_OBJECT_0 || !out.eof || !err.eof)) {
            if (!TerminateJobObject(job, 1)) {
                goto done;
            }
            *timed_out_out = 1;
        }
        if (out.length == before_out && err.length == before_err) {
            Sleep(1);
        }
    }

    DWORD code;
    if (!GetExitCodeProcess(child.hProcess, &code)) {
        goto done;
    }
    if (!out.data) {
        out.data = malloc(1);
    }
    if (!err.data) {
        err.data = malloc(1);
    }
    if (!out.data || !err.data) {
        status = ENOMEM;
        goto done;
    }
    out.data[out.length] = 0;
    err.data[err.length] = 0;
    *exit_code_out = (int64_t)(int32_t)code;
    *stdout_out = out.data;
    *stderr_out = err.data;
    out.data = NULL;
    err.data = NULL;
    status = 0;

done:
    if (status && child.hProcess) {
        TerminateProcess(child.hProcess, 1);
        WaitForSingleObject(child.hProcess, INFINITE);
    }
    if (startup.lpAttributeList) {
        DeleteProcThreadAttributeList(startup.lpAttributeList);
    }
    free(attributes);
    tb_process_close(child.hThread);
    tb_process_close(child.hProcess);
    tb_process_close(job);
    tb_process_close(in);
    tb_process_close(out.read_end);
    tb_process_close(out.write_end);
    tb_process_close(err.read_end);
    tb_process_close(err.write_end);
    free(out.data);
    free(err.data);
    free(command);
    free(directory);
    free(env);
    return status;
}

#endif
