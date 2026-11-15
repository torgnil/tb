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

define private ptr @tb_bootstrap_string_array_map_string_expr_captured(ptr %array, ptr %callback, ptr %context, ptr %cleanup, i1 %release.array.on.exception) {
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
  call void %cleanup(ptr %context)
  call void @longjmp(ptr %prior.handler, i32 1)
  unreachable
done:
  store ptr %prior.handler, ptr @__tb_exception_handler
  call void %cleanup(ptr %context)
  ret ptr %result
}

define private ptr @tb_bootstrap_string_array_flat_map_expr(ptr %array, ptr %callback, i1 %release.array.on.exception) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_string_array_new(i32 0)
  %env = alloca [192 x i8]
  %env.ptr = getelementptr [192 x i8], ptr %env, i32 0, i32 0
  %prior.handler = load ptr, ptr @__tb_exception_handler
  %has.prior.handler = icmp ne ptr %prior.handler, null
  br i1 %has.prior.handler, label %guard.install, label %outer.cond
guard.install:
  store ptr %env.ptr, ptr @__tb_exception_handler
  %state = call i32 @setjmp(ptr %env.ptr)
  %escaped = icmp ne i32 %state, 0
  br i1 %escaped, label %callback.exception, label %outer.cond
outer.cond:
  %outer.index = phi i32 [0, %entry], [0, %guard.install], [%outer.next, %outer.step]
  %keep.outer = icmp slt i32 %outer.index, %len
  br i1 %keep.outer, label %outer.body, label %done
outer.body:
  %item = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %outer.index)
  %chunk = call ptr %callback(ptr %item)
  %chunk.len = call i32 @tb_bootstrap_string_array_length(ptr %chunk)
  br label %inner.cond
inner.cond:
  %inner.index = phi i32 [0, %outer.body], [%inner.next, %inner.step]
  %keep.inner = icmp slt i32 %inner.index, %chunk.len
  br i1 %keep.inner, label %inner.body, label %inner.done
inner.body:
  %chunk.item = call ptr @tb_bootstrap_string_array_get(ptr %chunk, i32 %inner.index)
  %chunk.item.null = icmp eq ptr %chunk.item, null
  br i1 %chunk.item.null, label %store.null, label %copy.item
copy.item:
  %chunk.item.copy = call ptr @tb_bootstrap_string_copy(ptr %chunk.item)
  %appended = call i32 @tb_bootstrap_string_array_push(ptr %result, ptr %chunk.item.copy, i1 true)
  br label %inner.step
store.null:
  %appended.null = call i32 @tb_bootstrap_string_array_push(ptr %result, ptr null, i1 false)
  br label %inner.step
inner.step:
  %inner.next = add i32 %inner.index, 1
  br label %inner.cond
inner.done:
  call void @tb_bootstrap_string_array_free(ptr %chunk)
  br label %outer.step
outer.step:
  %outer.next = add i32 %outer.index, 1
  br label %outer.cond
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
