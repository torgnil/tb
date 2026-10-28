#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

#ifdef TB_RANDOM_TEST
int tb_random_test_open(const char *path, int flags);
ssize_t tb_random_test_read(int fd, void *buffer, size_t length);
int tb_random_test_close(int fd);
#define TB_RANDOM_OPEN(path, flags) tb_random_test_open((path), (flags))
#define TB_RANDOM_READ(fd, buffer, length) tb_random_test_read((fd), (buffer), (length))
#define TB_RANDOM_CLOSE(fd) tb_random_test_close(fd)
#else
#define TB_RANDOM_OPEN(path, flags) open((path), (flags))
#define TB_RANDOM_READ(fd, buffer, length) read((fd), (buffer), (length))
#define TB_RANDOM_CLOSE(fd) close(fd)
#endif

static int tb_secure_random_bytes(unsigned char *buffer, size_t length) {
    int descriptor = TB_RANDOM_OPEN("/dev/urandom", O_RDONLY);
    if (descriptor < 0) {
        return -1;
    }

    size_t offset = 0;
    int failed = 0;
    while (offset < length) {
        ssize_t count = TB_RANDOM_READ(descriptor, buffer + offset, length - offset);
        if (count > 0) {
            offset += (size_t)count;
        } else if (count < 0 && errno == EINTR) {
            continue;
        } else {
            failed = 1;
            break;
        }
    }

    if (TB_RANDOM_CLOSE(descriptor) != 0) {
        failed = 1;
    }
    return failed ? -1 : 0;
}

int tb_secure_random_i64(int64_t *result) {
    if (result == NULL) {
        return -1;
    }

    unsigned char bytes[8];
    if (tb_secure_random_bytes(bytes, sizeof(bytes)) != 0) {
        return -1;
    }

    uint64_t bits = 0;
    for (size_t index = 0; index < sizeof(bytes); index += 1) {
        bits = (bits << 8) | bytes[index];
    }
    memcpy(result, &bits, sizeof(bits));
    return 0;
}
