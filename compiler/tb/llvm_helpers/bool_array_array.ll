%tb_bootstrap_bool_array_array = type { i32, ptr, ptr }

define private ptr @tb_bootstrap_bool_array_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 24)
  %array.null = icmp eq ptr %array, null
  br i1 %array.null, label %fail, label %allocate
allocate:
  %is.empty = icmp eq i32 %len, 0
  %alloc.len = select i1 %is.empty, i32 1, i32 %len
  %len64 = sext i32 %alloc.len to i64
  %data.bytes = mul i64 %len64, 8
  %data = call ptr @calloc(i64 1, i64 %data.bytes)
  %data.null = icmp eq ptr %data, null
  br i1 %data.null, label %fail.array, label %allocate.owned
allocate.owned:
  %owned = call ptr @calloc(i64 1, i64 %len64)
  %owned.null = icmp eq ptr %owned, null
  br i1 %owned.null, label %fail.data, label %initialize
initialize:
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 0
  store i32 %len, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 1
  store ptr %data, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 2
  store ptr %owned, ptr %owned.ptr
  ret ptr %array
fail.data:
  call void @free(ptr %data)
  br label %fail.array
fail.array:
  call void @free(ptr %array)
  br label %fail
fail:
  call void @abort()
  unreachable
}

define private ptr @tb_bootstrap_bool_array_array_clone(ptr %source) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_array_length(ptr %source)
  %copy = call ptr @tb_bootstrap_bool_array_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [ 0, %entry ], [ %next, %loop.step ]
  %more = icmp slt i32 %index, %len
  br i1 %more, label %loop.body, label %done
loop.body:
  %row = call ptr @tb_bootstrap_bool_array_array_get(ptr %source, i32 %index)
  %row.copy = call ptr @tb_bootstrap_bool_array_clone(ptr %row)
  call void @tb_bootstrap_bool_array_array_set_owned(ptr %copy, i32 %index, ptr %row.copy, i1 true)
  br label %loop.step
loop.step:
  %next = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %copy
}

define private void @tb_bootstrap_bool_array_array_fill(ptr %array, ptr %value) {
entry:
  %hold = call ptr @tb_bootstrap_bool_array_clone(ptr %value)
  %len = call i32 @tb_bootstrap_bool_array_array_length(ptr %array)
  br label %fill.cond
fill.cond:
  %index = phi i32 [ 0, %entry ], [ %next, %fill.step ]
  %more = icmp slt i32 %index, %len
  br i1 %more, label %fill.body, label %fill.done
fill.body:
  %copy = call ptr @tb_bootstrap_bool_array_clone(ptr %hold)
  call void @tb_bootstrap_bool_array_array_set_owned(ptr %array, i32 %index, ptr %copy, i1 true)
  br label %fill.step
fill.step:
  %next = add i32 %index, 1
  br label %fill.cond
fill.done:
  call void @tb_bootstrap_bool_array_free(ptr %hold)
  ret void
}

define private i32 @tb_bootstrap_bool_array_array_length(ptr %array) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}

define private ptr @tb_bootstrap_bool_array_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %value = load ptr, ptr %slot
  ret ptr %value
}

define private void @tb_bootstrap_bool_array_array_release_slot(ptr %array, i32 %index) {
entry:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %flag.ptr = getelementptr inbounds i8, ptr %owned, i32 %index
  %flag = load i8, ptr %flag.ptr
  %is.owned = icmp ne i8 %flag, 0
  br i1 %is.owned, label %release, label %done
release:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %row = load ptr, ptr %slot
  call void @tb_bootstrap_bool_array_free(ptr %row)
  store i8 0, ptr %flag.ptr
  br label %done
done:
  ret void
}

define private void @tb_bootstrap_bool_array_array_set_owned(ptr %array, i32 %index, ptr %value, i1 %is_owned) {
entry:
  call void @tb_bootstrap_bool_array_array_release_slot(ptr %array, i32 %index)
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr %value, ptr %slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %flag.ptr = getelementptr inbounds i8, ptr %owned, i32 %index
  %flag = zext i1 %is_owned to i8
  store i8 %flag, ptr %flag.ptr
  ret void
}

define private void @tb_bootstrap_bool_array_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free.rows
free.rows:
  %len = call i32 @tb_bootstrap_bool_array_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [ 0, %free.rows ], [ %next, %loop.step ]
  %more = icmp slt i32 %index, %len
  br i1 %more, label %loop.body, label %free.storage
loop.body:
  call void @tb_bootstrap_bool_array_array_release_slot(ptr %array, i32 %index)
  br label %loop.step
loop.step:
  %next = add i32 %index, 1
  br label %loop.cond
free.storage:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  call void @free(ptr %data)
  %owned.ptr = getelementptr inbounds %tb_bootstrap_bool_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  call void @free(ptr %owned)
  call void @free(ptr %array)
  br label %done
done:
  ret void
}
