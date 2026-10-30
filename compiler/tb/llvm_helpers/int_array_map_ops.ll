define private ptr @tb_bootstrap_int_array_map_add(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = add i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_sub(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = sub i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_mul(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = mul i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_div(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = call i64 @tb_bootstrap_checked_int_div(i64 %value, i64 %rhs)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_mod(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = call i64 @tb_bootstrap_checked_int_rem(i64 %value, i64 %rhs)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_self_add(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = add i64 %value, %value
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_self_sub(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = sub i64 %value, %value
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_self_mul(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = mul i64 %value, %value
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_self_div(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = call i64 @tb_bootstrap_checked_int_div(i64 %value, i64 %value)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_self_mod(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = call i64 @tb_bootstrap_checked_int_rem(i64 %value, i64 %value)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_expr(ptr %array, ptr %callback) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  %env = alloca [192 x i8]
  %env.ptr = getelementptr [192 x i8], ptr %env, i32 0, i32 0
  %prior.handler = load ptr, ptr @__tb_exception_handler
  %has.prior.handler = icmp ne ptr %prior.handler, null
  br i1 %has.prior.handler, label %guard.install, label %loop.cond
guard.install:
  store ptr %env.ptr, ptr @__tb_exception_handler
  %state = call i32 @setjmp(ptr %env.ptr)
  %escaped = icmp ne i32 %state, 0
  br i1 %escaped, label %callback.exception, label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [0, %guard.install], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = call i64 %callback(i64 %value)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
callback.exception:
  store ptr %prior.handler, ptr @__tb_exception_handler
  call void @tb_bootstrap_int_array_free(ptr %result)
  call void @longjmp(ptr %prior.handler, i32 1)
  unreachable
done:
  store ptr %prior.handler, ptr @__tb_exception_handler
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_filter_expr(ptr %array, ptr %callback) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 0)
  %env = alloca [192 x i8]
  %env.ptr = getelementptr [192 x i8], ptr %env, i32 0, i32 0
  %prior.handler = load ptr, ptr @__tb_exception_handler
  %has.prior.handler = icmp ne ptr %prior.handler, null
  br i1 %has.prior.handler, label %guard.install, label %loop.cond
guard.install:
  store ptr %env.ptr, ptr @__tb_exception_handler
  %state = call i32 @setjmp(ptr %env.ptr)
  %escaped = icmp ne i32 %state, 0
  br i1 %escaped, label %callback.exception, label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [0, %guard.install], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %selected = call i1 %callback(i64 %value)
  br i1 %selected, label %append, label %loop.step
append:
  call i32 @tb_bootstrap_int_array_push(ptr %result, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
callback.exception:
  store ptr %prior.handler, ptr @__tb_exception_handler
  call void @tb_bootstrap_int_array_free(ptr %result)
  call void @longjmp(ptr %prior.handler, i32 1)
  unreachable
done:
  store ptr %prior.handler, ptr @__tb_exception_handler
  ret ptr %result
}
