@.fmt.process.capture.error = private unnamed_addr constant [6 x i8] c"%s%s\0A\00"
@.prefix.process.capture.error = private unnamed_addr constant [28 x i8] c"run_process: unable to run \00"
@.message.process.capture.empty = private unnamed_addr constant [27 x i8] c"run_process: empty command\00"
define private ptr @tb_bootstrap_process_capture(ptr %args) {
  %result = call ptr @tb_bootstrap_process_capture_impl(ptr %args, ptr null)
  ret ptr %result
}
define private ptr @tb_bootstrap_process_capture_with_input(ptr %args, ptr %input) {
  %result = call ptr @tb_bootstrap_process_capture_impl(ptr %args, ptr %input)
  ret ptr %result
}
define private ptr @tb_bootstrap_process_capture_impl(ptr %args, ptr %input) {
entry:
  %argc = call i32 @tb_bootstrap_string_array_length(ptr %args)
  %empty = icmp sle i32 %argc, 0
  br i1 %empty, label %empty.command, label %start
empty.command:
  %handler.empty = load ptr, ptr @__tb_exception_handler
  %has.handler.empty = icmp ne ptr %handler.empty, null
  br i1 %has.handler.empty, label %empty.unwind, label %empty.fatal
empty.unwind:
  %empty.message.ptr = getelementptr inbounds [27 x i8], ptr @.message.process.capture.empty, i32 0, i32 0
  %empty.message = call ptr @tb_bootstrap_string_copy(ptr %empty.message.ptr)
  store ptr %empty.message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler.empty, i32 1)
  unreachable
empty.fatal:
  %empty.fatal.message = getelementptr inbounds [27 x i8], ptr @.message.process.capture.empty, i32 0, i32 0
  call void @puts(ptr %empty.fatal.message)
  call void @exit(i32 1)
  unreachable
start:
  %status.slot = alloca i64
  %stdout.slot = alloca ptr
  %stderr.slot = alloca ptr
  %array.data.ptr.ptr = getelementptr inbounds { i32, i32, ptr, ptr }, ptr %args, i32 0, i32 2
  %array.data = load ptr, ptr %array.data.ptr.ptr
  %status = call i32 @tb_process_run(ptr %array.data, i32 %argc, ptr %input, ptr %status.slot, ptr %stdout.slot, ptr %stderr.slot)
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %run.error, label %run.success
run.error:
  %command = call ptr @tb_bootstrap_string_array_get(ptr %args, i32 0)
  %error.prefix = getelementptr inbounds [28 x i8], ptr @.prefix.process.capture.error, i32 0, i32 0
  %error.message = call ptr @tb_bootstrap_string_concat(ptr %error.prefix, ptr %command)
  %handler.error = load ptr, ptr @__tb_exception_handler
  %has.handler.error = icmp ne ptr %handler.error, null
  br i1 %has.handler.error, label %run.unwind, label %run.fatal
run.unwind:
  store ptr %error.message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler.error, i32 1)
  unreachable
run.fatal:
  %fatal.format = getelementptr inbounds [6 x i8], ptr @.fmt.process.capture.error, i32 0, i32 0
  %fatal.prefix = getelementptr inbounds [28 x i8], ptr @.prefix.process.capture.error, i32 0, i32 0
  call i32 (ptr, ...) @printf(ptr %fatal.format, ptr %fatal.prefix, ptr %command)
  call void @exit(i32 1)
  unreachable
run.success:
  %exit.code = load i64, ptr %status.slot
  %stdout.raw = load ptr, ptr %stdout.slot
  %stderr.raw = load ptr, ptr %stderr.slot
  %exit.text = call ptr @tb_bootstrap_int_to_string(i64 %exit.code)
  %stdout.text = call ptr @tb_bootstrap_string_copy(ptr %stdout.raw)
  %stderr.text = call ptr @tb_bootstrap_string_copy(ptr %stderr.raw)
  call void @free(ptr %stdout.raw)
  call void @free(ptr %stderr.raw)
  %result = call ptr @tb_bootstrap_string_array_new(i32 3)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 0, ptr %exit.text, i1 true)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 1, ptr %stdout.text, i1 true)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 2, ptr %stderr.text, i1 true)
  ret ptr %result
}
