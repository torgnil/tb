define private ptr @tb_bootstrap_string_array_map_string_expr(ptr %array, ptr %callback, i1 %release.array.on.exception) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_string_array_new(i32 %len)
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
  %value = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %mapped = call ptr %callback(ptr %value)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 %index, ptr %mapped, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
callback.exception:
  store ptr %prior.handler, ptr @__tb_exception_handler
  call void @tb_bootstrap_string_array_free(ptr %result)
  br i1 %release.array.on.exception, label %callback.exception.free.array, label %callback.exception.rethrow
callback.exception.free.array:
  call void @tb_bootstrap_string_array_free(ptr %array)
  br label %callback.exception.rethrow
callback.exception.rethrow:
  call void @longjmp(ptr %prior.handler, i32 1)
  unreachable
done:
  store ptr %prior.handler, ptr @__tb_exception_handler
  ret ptr %result
}

define private ptr @tb_bootstrap_string_array_map_string_expr_captured(ptr %array, ptr %callback, ptr %context, i1 %release.array.on.exception) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_string_array_new(i32 %len)
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
  %value = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %mapped = call ptr %callback(ptr %value, ptr %context)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 %index, ptr %mapped, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
callback.exception:
  store ptr %prior.handler, ptr @__tb_exception_handler
  call void @tb_bootstrap_string_array_free(ptr %result)
  br i1 %release.array.on.exception, label %callback.exception.free.array, label %callback.exception.rethrow
callback.exception.free.array:
  call void @tb_bootstrap_string_array_free(ptr %array)
  br label %callback.exception.rethrow
callback.exception.rethrow:
  call void @longjmp(ptr %prior.handler, i32 1)
  unreachable
done:
  store ptr %prior.handler, ptr @__tb_exception_handler
  ret ptr %result
}
