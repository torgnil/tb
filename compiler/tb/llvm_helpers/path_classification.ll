@.fmt.path.test.error = private unnamed_addr constant [6 x i8] c"%s%s\0A\00"
@.prefix.path_exists.error = private unnamed_addr constant [32 x i8] c"path_exists: unable to inspect \00"
@.prefix.is_file.error = private unnamed_addr constant [28 x i8] c"is_file: unable to inspect \00"
@.prefix.is_dir.error = private unnamed_addr constant [27 x i8] c"is_dir: unable to inspect \00"

define private i1 @tb_bootstrap_path_test(ptr %path, i32 %kind, ptr %prefix) {
entry:
  %matches.slot = alloca i32
  store i32 0, ptr %matches.slot
  %status = call i32 @tb_path_test(ptr %path, i32 %kind, ptr %matches.slot)
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %failure, label %success
failure:
  %handler = load ptr, ptr @__tb_exception_handler
  %has.handler = icmp ne ptr %handler, null
  br i1 %has.handler, label %unwind, label %fatal
unwind:
  %message = call ptr @tb_bootstrap_string_concat(ptr %prefix, ptr %path)
  store ptr %message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler, i32 1)
  unreachable
fatal:
  call i32 (ptr, ...) @printf(ptr @.fmt.path.test.error, ptr %prefix, ptr %path)
  call void @exit(i32 1)
  unreachable
success:
  %matches = load i32, ptr %matches.slot
  %result = icmp ne i32 %matches, 0
  ret i1 %result
}

define private i1 @tb_bootstrap_path_exists(ptr %path) {
entry:
  %result = call i1 @tb_bootstrap_path_test(ptr %path, i32 0, ptr @.prefix.path_exists.error)
  ret i1 %result
}

define private i1 @tb_bootstrap_is_file(ptr %path) {
entry:
  %result = call i1 @tb_bootstrap_path_test(ptr %path, i32 1, ptr @.prefix.is_file.error)
  ret i1 %result
}

define private i1 @tb_bootstrap_is_dir(ptr %path) {
entry:
  %result = call i1 @tb_bootstrap_path_test(ptr %path, i32 2, ptr @.prefix.is_dir.error)
  ret i1 %result
}
