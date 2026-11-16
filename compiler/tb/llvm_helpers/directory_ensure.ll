@.fmt.ensure_dir.error = private unnamed_addr constant [6 x i8] c"%s%s\0A\00"
@.prefix.ensure_dir.error = private unnamed_addr constant [30 x i8] c"ensure_dir: unable to create \00"

define private void @tb_bootstrap_ensure_dir(ptr %path) {
entry:
  %status = call i32 @tb_directory_ensure(ptr %path)
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %failure, label %success
failure:
  %handler = load ptr, ptr @__tb_exception_handler
  %has.handler = icmp ne ptr %handler, null
  br i1 %has.handler, label %unwind, label %fatal
unwind:
  %prefix = getelementptr inbounds [30 x i8], ptr @.prefix.ensure_dir.error, i32 0, i32 0
  %message = call ptr @tb_bootstrap_string_concat(ptr %prefix, ptr %path)
  store ptr %message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler, i32 1)
  unreachable
fatal:
  %printed = call i32 (ptr, ...) @printf(ptr @.fmt.ensure_dir.error, ptr @.prefix.ensure_dir.error, ptr %path)
  call void @exit(i32 1)
  unreachable
success:
  ret void
}
