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
define private i1 @tb_bootstrap_bool_array_pop(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  %is.empty = icmp sle i32 %len, 0
  br i1 %is.empty, label %empty, label %pop
empty:
  ret i1 false
pop:
  %last.index = sub i32 %len, 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i8, ptr %data, i32 %last.index
  %value.byte = load i8, ptr %slot
  %value = icmp ne i8 %value.byte, 0
  %len.ptr = getelementptr inbounds %tb_bootstrap_bool_array, ptr %array, i32 0, i32 0
  store i32 %last.index, ptr %len.ptr
  ret i1 %value
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
define private ptr @tb_bootstrap_bool_array_slice(ptr %array, i64 %start, i64 %end) {
entry:
  %len32 = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  %len = sext i32 %len32 to i64
  %start.negative = icmp slt i64 %start, 0
  %start.from.end = add i64 %len, %start
  %start.adjusted = select i1 %start.negative, i64 %start.from.end, i64 %start
  %start.before.zero = icmp slt i64 %start.adjusted, 0
  %start.clamped.low = select i1 %start.before.zero, i64 0, i64 %start.adjusted
  %start.past.end = icmp sgt i64 %start.clamped.low, %len
  %start.clamped = select i1 %start.past.end, i64 %len, i64 %start.clamped.low
  %end.negative = icmp slt i64 %end, 0
  %end.from.end = add i64 %len, %end
  %end.adjusted = select i1 %end.negative, i64 %end.from.end, i64 %end
  %end.before.zero = icmp slt i64 %end.adjusted, 0
  %end.clamped.low = select i1 %end.before.zero, i64 0, i64 %end.adjusted
  %end.past.end = icmp sgt i64 %end.clamped.low, %len
  %end.clamped.high = select i1 %end.past.end, i64 %len, i64 %end.clamped.low
  %end.before.start = icmp slt i64 %end.clamped.high, %start.clamped
  %end.clamped = select i1 %end.before.start, i64 %start.clamped, i64 %end.clamped.high
  %slice.len64 = sub i64 %end.clamped, %start.clamped
  %slice.len32 = trunc i64 %slice.len64 to i32
  %result = call ptr @tb_bootstrap_bool_array_new(i32 %slice.len32)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.body]
  %index64 = sext i32 %index to i64
  %keep.loop = icmp slt i64 %index64, %slice.len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %source.index64 = add i64 %start.clamped, %index64
  %source.index32 = trunc i64 %source.index64 to i32
  %value = call i1 @tb_bootstrap_bool_array_get(ptr %array, i32 %source.index32)
  call void @tb_bootstrap_bool_array_set(ptr %result, i32 %index, i1 %value)
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
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
define private void @tb_bootstrap_bool_array_fill(ptr %array, i1 %value) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [ 0, %entry ], [ %next.index, %loop.body ]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  call void @tb_bootstrap_bool_array_set(ptr %array, i32 %index, i1 %value)
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
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
define private i64 @tb_bootstrap_bool_array_sum(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_bool_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %sum = phi i64 [0, %entry], [%next.sum, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i1 @tb_bootstrap_bool_array_get(ptr %array, i32 %index)
  %value.i64 = zext i1 %value to i64
  %next.sum = add i64 %sum, %value.i64
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret i64 %sum
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
