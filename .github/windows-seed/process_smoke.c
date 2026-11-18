#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

int tb_process_run(const char *const *arguments, int32_t argument_count,
                   const char *input, const char *working_directory,
                   int64_t timeout_ms, const char *const *environment, int32_t environment_count,
                   int64_t *exit_code_out, int32_t *timed_out_out,
                   char **stdout_out, char **stderr_out);

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "%s\n", message);
    }
    return condition;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "child") == 0) {
        const char *variable = getenv("TB_PROCESS_SMOKE");
        FILE *marker = fopen("build_tb.sh", "rb");
        if (strcmp(argv[2], "space \"quote\" \\") || !variable ||
            strcmp(variable, "one=two") || !marker) {
            return 2;
        }
        fclose(marker);
        char input[16];
        size_t length = fread(input, 1, sizeof(input), stdin);
        fwrite(input, 1, length, stdout);
        fputs("child stderr", stderr);
        return 7;
    }
    if (argc == 2 && strcmp(argv[1], "timeout") == 0) {
        fputs("ready", stdout);
        fflush(stdout);
        Sleep(5000);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "spawn") == 0) {
        wchar_t path[MAX_PATH], command[MAX_PATH + 12];
        DWORD length = GetModuleFileNameW(NULL, path, MAX_PATH);
        if (!length || length >= MAX_PATH ||
            swprintf(command, MAX_PATH + 12, L"\"%ls\" timeout", path) < 0) {
            return 2;
        }
        STARTUPINFOW startup = {0};
        startup.cb = sizeof(startup);
        startup.dwFlags = STARTF_USESTDHANDLES;
        startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
        startup.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
        startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
        PROCESS_INFORMATION child = {0};
        if (!CreateProcessW(path, command, NULL, NULL, TRUE, 0,
                            NULL, NULL, &startup, &child)) {
            return 3;
        }
        CloseHandle(child.hThread);
        CloseHandle(child.hProcess);
        return 0;
    }

    char executable[MAX_PATH];
    DWORD length = GetModuleFileNameA(NULL, executable, MAX_PATH);
    if (!check(length > 0 && length < MAX_PATH, "could not resolve smoke executable")) {
        return 1;
    }
    const char *command[] = {executable, "child", "space \"quote\" \\"};
    const char *environment[] = {"TB_PROCESS_SMOKE=one=two"};
    char *out = NULL, *err = NULL;
    int64_t code = 0;
    int32_t timed_out = 0;
    int status = tb_process_run(command, 3, "payload", "source", 10000, environment, 1,
                                &code, &timed_out, &out, &err);
    int ok = check(!status && code == 7 && !timed_out &&
                   !strcmp(out, "payload") && !strcmp(err, "child stderr"),
                   "process arguments, input, streams, cwd or environment failed");
    free(out);
    free(err);

    const char *slow[] = {executable, "timeout"};
    status = tb_process_run(slow, 2, NULL, NULL, 1000, NULL, -1,
                            &code, &timed_out, &out, &err);
    ok &= check(!status && timed_out && code != 0 && !strcmp(out, "ready") && !strcmp(err, ""),
                "process timeout or partial capture failed");
    free(out);
    free(err);
    const char *descendant[] = {executable, "spawn"};
    status = tb_process_run(descendant, 2, NULL, NULL, 1000, NULL, -1,
                            &code, &timed_out, &out, &err);
    ok &= check(!status && timed_out && code == 0 && !strcmp(out, "ready") && !strcmp(err, ""),
                "descendant keeping capture handles open was not timed out");
    free(out);
    free(err);
    return ok ? 0 : 1;
}
