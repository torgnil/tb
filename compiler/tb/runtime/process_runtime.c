#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

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

/* Drain until the pipe would block or reaches EOF. Returns 1 at EOF. */
static int tb_process_drain(int *fd, tb_process_buffer *buffer) {
    char chunk[8192];
    for (;;) {
        ssize_t read_count = read(*fd, chunk, sizeof(chunk));
        if (read_count > 0) {
            if (tb_process_buffer_append(buffer, chunk,
                                         (size_t)read_count) != 0) {
                return -1;
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
                                        int *stderr_fd) {
    tb_process_close_fd(stdout_fd);
    tb_process_close_fd(stderr_fd);
    if (child <= 0) {
        return;
    }
    kill(child, SIGKILL);
    int status;
    while (waitpid(child, &status, 0) < 0 && errno == EINTR) {
    }
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
 * modified or retained. On success, the caller owns both output buffers.
 * The return value is zero on success and a nonzero error number on failure.
 */
int tb_process_run(const char *const *arguments, int32_t argument_count,
                   int64_t *exit_code_out, char **stdout_out,
                   char **stderr_out) {
    if (arguments == NULL || argument_count <= 0 || exit_code_out == NULL ||
        stdout_out == NULL || stderr_out == NULL || arguments[0] == NULL ||
        arguments[0][0] == '\0') {
        return EINVAL;
    }
    *stdout_out = NULL;
    *stderr_out = NULL;

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

    int stdout_pipe[2] = {-1, -1};
    int stderr_pipe[2] = {-1, -1};
    tb_process_buffer stdout_buffer = {NULL, 0, 0};
    tb_process_buffer stderr_buffer = {NULL, 0, 0};
    pid_t child = -1;
    int failed = 0;
    int failure_errno = 0;

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
    spawn_error = posix_spawn_file_actions_adddup2(
        &actions, stdout_pipe[1], STDOUT_FILENO);
    if (spawn_error == 0) {
        spawn_error = posix_spawn_file_actions_adddup2(
            &actions, stderr_pipe[1], STDERR_FILENO);
    }
    int pipe_fds[] = {stdout_pipe[0], stdout_pipe[1],
                      stderr_pipe[0], stderr_pipe[1]};
    for (size_t index = 0; spawn_error == 0 && index < 4; index += 1) {
        spawn_error = posix_spawn_file_actions_addclose(&actions,
                                                        pipe_fds[index]);
    }
    if (spawn_error == 0) {
        spawn_error = posix_spawnp(&child, argv[0], &actions, NULL, argv,
                                   environ);
    }
    posix_spawn_file_actions_destroy(&actions);
    if (spawn_error != 0) {
        failed = 1;
        failure_errno = spawn_error;
        goto done;
    }

    tb_process_close_fd(&stdout_pipe[1]);
    tb_process_close_fd(&stderr_pipe[1]);
    while (stdout_pipe[0] >= 0 || stderr_pipe[0] >= 0) {
        struct pollfd pipes[2];
        pipes[0].fd = stdout_pipe[0];
        pipes[0].events = POLLIN | POLLHUP;
        pipes[0].revents = 0;
        pipes[1].fd = stderr_pipe[0];
        pipes[1].events = POLLIN | POLLHUP;
        pipes[1].revents = 0;
        int poll_result;
        do {
            poll_result = poll(pipes, 2, -1);
        } while (poll_result < 0 && errno == EINTR);
        if (poll_result < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
        if (stdout_pipe[0] >= 0 && pipes[0].revents != 0 &&
            tb_process_drain(&stdout_pipe[0], &stdout_buffer) < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
        if (stderr_pipe[0] >= 0 && pipes[1].revents != 0 &&
            tb_process_drain(&stderr_pipe[0], &stderr_buffer) < 0) {
            failed = 1;
            failure_errno = errno;
            break;
        }
    }

    if (failed) {
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0]);
        child = -1;
        goto done;
    }

    int wait_status = 0;
    pid_t waited;
    do {
        waited = waitpid(child, &wait_status, 0);
    } while (waited < 0 && errno == EINTR);
    if (waited < 0) {
        failed = 1;
        failure_errno = errno;
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0]);
        child = -1;
        goto done;
    }
    child = -1;
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
        tb_process_reap_after_error(child, &stdout_pipe[0], &stderr_pipe[0]);
    }
    tb_process_close_fd(&stdout_pipe[0]);
    tb_process_close_fd(&stdout_pipe[1]);
    tb_process_close_fd(&stderr_pipe[0]);
    tb_process_close_fd(&stderr_pipe[1]);
    free(stdout_buffer.data);
    free(stderr_buffer.data);
    free(argv);
    if (failed) {
        return failure_errno == 0 ? EIO : failure_errno;
    }
    return 0;
}
