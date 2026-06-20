%tb_bootstrap_bool_array = type { i32, ptr }
define private ptr @tb_bootstrap_bool_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 16)
  %len64 = sext i32 %len to i64
  %bytes = mul i64 %len64, 1
  %data = call ptr @malloc(i64 %bytes)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 0
  store i32 %len, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  store ptr %data, ptr %data.ptr
  ret ptr %array
}
define private i32 @tb_bootstrap_bool_array_length(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private i32 @tb_bootstrap_bool_array_push(ptr %array, i1 %value) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  %new.len = add i32 %len, 1
  %new.len64 = sext i32 %new.len to i64
  %new.data = call ptr @malloc(i64 %new.len64)
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %old.data = load ptr, ptr %data.ptr
  %len64 = sext i32 %len to i64
  call void @llvm.memcpy.p0.p0.i64(ptr %new.data, ptr %old.data, i64 %len64, i1 false)
  %slot = getelementptr inbounds i8, ptr %new.data, i32 %len
  %value.byte = zext i1 %value to i8
  store i8 %value.byte, ptr %slot
  call void @free(ptr %old.data)
  store ptr %new.data, ptr %data.ptr
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 0
  store i32 %new.len, ptr %len.ptr
  ret i32 %new.len
}
define private i1 @tb_bootstrap_bool_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i8, ptr %data, i32 %index
  %value.byte = load i8, ptr %slot
  %value = icmp ne i8 %value.byte, 0
  ret i1 %value
}
define private void @tb_bootstrap_bool_array_set(ptr %array, i32 %index, i1 %value) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i8, ptr %data, i32 %index
  %value.byte = zext i1 %value to i8
  store i8 %value.byte, ptr %slot
  ret void
}
define private i1 @tb_bootstrap_bool_array_contains(ptr %array, i1 %needle) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %notfound
loop.body:
  %item = call i1 @tb_bootstrap_bool_array_get(ptr %array, i32 %index)
  %matches = icmp eq i1 %item, %needle
  br i1 %matches, label %found, label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
found:
  ret i1 true
notfound:
  ret i1 false
}
define private ptr @tb_bootstrap_bool_array_clone(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  %clone = call ptr @tb_bootstrap_bool_array_new(i32 %len)
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %clone.data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %clone, i32 0, i32 1
  %clone.data = load ptr, ptr %clone.data.ptr
  %len64 = sext i32 %len to i64
  call void @llvm.memcpy.p0.p0.i64(ptr %clone.data, ptr %data, i64 %len64, i1 false)
  ret ptr %clone
}
define private void @tb_bootstrap_bool_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  call void @free(ptr %data)
  call void @free(ptr %array)
  br label %done
done:
  ret void
}
