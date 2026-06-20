define private ptr @tb_bootstrap_int_set_new() {
entry:
  %set = call ptr @tb_bootstrap_int_array_new(i32 0)
  ret ptr %set
}
define private i32 @tb_bootstrap_int_set_length(ptr %set) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %set)
  ret i32 %len
}
define private i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index) {
entry:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %set, i32 %index)
  ret i64 %value
}
define private i1 @tb_bootstrap_int_set_contains(ptr %set, i64 %value) {
entry:
  %len = call i32 @tb_bootstrap_int_set_length(ptr %set)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index)
  %is.match = icmp eq i64 %item, %value
  br i1 %is.match, label %found, label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
found:
  ret i1 true
done:
  ret i1 false
}
define private i32 @tb_bootstrap_int_set_add(ptr %set, i64 %value) {
entry:
  %exists = call i1 @tb_bootstrap_int_set_contains(ptr %set, i64 %value)
  br i1 %exists, label %existing, label %insert
existing:
  %len.existing = call i32 @tb_bootstrap_int_set_length(ptr %set)
  ret i32 %len.existing
insert:
  %len.new = call i32 @tb_bootstrap_int_array_push(ptr %set, i64 %value)
  ret i32 %len.new
}
define private ptr @tb_bootstrap_int_set_union(ptr %left, ptr %right) {
entry:
  %result = call ptr @tb_bootstrap_int_array_clone(ptr %left)
  %len = call i32 @tb_bootstrap_int_set_length(ptr %right)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call i64 @tb_bootstrap_int_set_get(ptr %right, i32 %index)
  %ignored = call i32 @tb_bootstrap_int_set_add(ptr %result, i64 %item)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_to_set_int_array(ptr %array) {
entry:
  %result = call ptr @tb_bootstrap_int_set_new()
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %ignored = call i32 @tb_bootstrap_int_set_add(ptr %result, i64 %item)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_set_clone(ptr %set) {
entry:
  %clone = call ptr @tb_bootstrap_int_array_clone(ptr %set)
  ret ptr %clone
}
define private void @tb_bootstrap_int_set_free(ptr %set) {
entry:
  call void @tb_bootstrap_int_array_free(ptr %set)
  ret void
}
@.fmt.set.int = private unnamed_addr constant [5 x i8] c"%lld\00"
define private i32 @tb_bootstrap_print_int_set(ptr %set) {
entry:
  %open = call i32 @putchar(i32 123)
  %len = call i32 @tb_bootstrap_int_set_length(ptr %set)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %is.first = icmp eq i32 %index, 0
  br i1 %is.first, label %emit.value, label %emit.sep
emit.sep:
  %comma = call i32 @putchar(i32 44)
  %space = call i32 @putchar(i32 32)
  br label %emit.value
emit.value:
  %value = call i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index)
  %print = call i32 (ptr, ...) @printf(ptr @.fmt.set.int, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  %close = call i32 @putchar(i32 125)
  %nl = call i32 @putchar(i32 10)
  ret i32 0
}
