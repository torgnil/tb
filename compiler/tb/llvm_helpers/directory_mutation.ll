@.fmt.remove_path.error = private unnamed_addr constant [6 x i8] c"%s%s\0A\00"
@.prefix.remove_path.error = private unnamed_addr constant [31 x i8] c"remove_path: unable to remove \00"
@.fmt.rename_path.error = private unnamed_addr constant [12 x i8] c"%s%s to %s\0A\00"
@.prefix.rename_path.error = private unnamed_addr constant [31 x i8] c"rename_path: unable to rename \00"
@.middle.rename_path.error = private unnamed_addr constant [5 x i8] c" to \00"

define private void @tb_bootstrap_remove_path(ptr %path) {
entry:
  %status = call i32 @tb_directory_remove_path(ptr %path)
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %failure, label %success
failure:
  %handler = load ptr, ptr @__tb_exception_handler
  %has.handler = icmp ne ptr %handler, null
  br i1 %has.handler, label %unwind, label %fatal
unwind:
  %message = call ptr @tb_bootstrap_string_concat(ptr @.prefix.remove_path.error, ptr %path)
  store ptr %message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler, i32 1)
  unreachable
fatal:
  call i32 (ptr, ...) @printf(ptr @.fmt.remove_path.error, ptr @.prefix.remove_path.error, ptr %path)
  call void @exit(i32 1)
  unreachable
success:
  ret void
}

define private void @tb_bootstrap_rename_path(ptr %source, ptr %destination) {
entry:
  %status = call i32 @tb_directory_rename_path(ptr %source, ptr %destination)
  %failed = icmp ne i32 %status, 0
  br i1 %failed, label %failure, label %success
failure:
  %handler = load ptr, ptr @__tb_exception_handler
  %has.handler = icmp ne ptr %handler, null
  br i1 %has.handler, label %unwind, label %fatal
unwind:
  %prefix.source = call ptr @tb_bootstrap_string_concat(ptr @.prefix.rename_path.error, ptr %source)
  %destination.suffix = call ptr @tb_bootstrap_string_concat(ptr @.middle.rename_path.error, ptr %destination)
  %message = call ptr @tb_bootstrap_string_concat(ptr %prefix.source, ptr %destination.suffix)
  call void @tb_release(ptr %prefix.source)
  call void @tb_release(ptr %destination.suffix)
  store ptr %message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler, i32 1)
  unreachable
fatal:
  call i32 (ptr, ...) @printf(ptr @.fmt.rename_path.error, ptr @.prefix.rename_path.error, ptr %source, ptr %destination)
  call void @exit(i32 1)
  unreachable
success:
  ret void
}
