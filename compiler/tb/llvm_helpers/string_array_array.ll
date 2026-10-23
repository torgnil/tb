%tb_bootstrap_string_array_array = type { i32, ptr, ptr }
define private ptr @tb_bootstrap_string_array_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 24)
  %len64 = sext i32 %len to i64
  %bytes = mul i64 %len64, 8
  %data = call ptr @malloc(i64 %bytes)
  %owned = call ptr @malloc(i64 %len64)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %len64, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  store i32 %len, ptr %len.ptr
  store ptr %data, ptr %data.ptr
  store ptr %owned, ptr %owned.ptr
  ret ptr %array
}
define private i32 @tb_bootstrap_string_array_array_length(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private ptr @tb_bootstrap_string_array_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %value = load ptr, ptr %slot
  ret ptr %value
}
define private void @tb_bootstrap_string_array_array_release_slot(ptr %array, i32 %index) {
entry:
  %len = call i32 @tb_bootstrap_string_array_array_length(ptr %array)
  %in.bounds = icmp slt i32 %index, %len
  br i1 %in.bounds, label %check, label %done
check:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %free.item, label %done
free.item:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %item.value = load ptr, ptr %item.slot
  call void @tb_bootstrap_string_array_free(ptr %item.value)
  store ptr null, ptr %item.slot
  store i8 0, ptr %owned.slot
  br label %done
done:
  ret void
}
define private void @tb_bootstrap_string_array_array_clear(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %start
start:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %start], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %loop.done
loop.body:
  call void @tb_bootstrap_string_array_array_release_slot(ptr %array, i32 %index)
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr null, ptr %item.slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  store i8 0, ptr %owned.slot
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
loop.done:
  store i32 0, ptr %len.ptr
  br label %done
done:
  ret void
}
define private void @tb_bootstrap_string_array_array_set_owned(ptr %array, i32 %index, ptr %value, i1 %is_owned) {
entry:
  %index.nonnegative = icmp sge i32 %index, 0
  %index.fits.length = icmp slt i32 %index, 2147483647
  %index.valid = and i1 %index.nonnegative, %index.fits.length
  br i1 %index.valid, label %check.grow, label %invalid.index
invalid.index:
  call void @abort()
  unreachable
check.grow:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %needs.grow = icmp sge i32 %index, %len
  br i1 %needs.grow, label %grow, label %store.ready
grow:
  %next.len = add i32 %index, 1
  %next.len64 = sext i32 %next.len to i64
  %data.bytes = mul i64 %next.len64, 8
  %owned.bytes = mul i64 %next.len64, 1
  %data.new = call ptr @malloc(i64 %data.bytes)
  %owned.new = call ptr @malloc(i64 %owned.bytes)
  %data.failed = icmp eq ptr %data.new, null
  %owned.failed = icmp eq ptr %owned.new, null
  %allocation.failed = or i1 %data.failed, %owned.failed
  br i1 %allocation.failed, label %allocation.abort, label %allocation.ready
allocation.abort:
  call void @abort()
  unreachable
allocation.ready:
  call void @llvm.memset.p0.i64(ptr %data.new, i8 0, i64 %data.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned.new, i8 0, i64 %owned.bytes, i1 false)
  %data.ptr.grow = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data.old = load ptr, ptr %data.ptr.grow
  %owned.ptr.grow = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned.old = load ptr, ptr %owned.ptr.grow
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %copy.old, label %store.new.ptrs
copy.old:
  %len64 = sext i32 %len to i64
  %old.data.bytes = mul i64 %len64, 8
  %old.owned.bytes = mul i64 %len64, 1
  call void @llvm.memcpy.p0.p0.i64(ptr %data.new, ptr %data.old, i64 %old.data.bytes, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr %owned.new, ptr %owned.old, i64 %old.owned.bytes, i1 false)
  br label %store.new.ptrs
store.new.ptrs:
  call void @free(ptr %data.old)
  call void @free(ptr %owned.old)
  store ptr %data.new, ptr %data.ptr.grow
  store ptr %owned.new, ptr %owned.ptr.grow
  store i32 %next.len, ptr %len.ptr
  br label %store.ready
store.ready:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr %value, ptr %slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
}
define private i32 @tb_bootstrap_string_array_array_push(ptr %array, ptr %value, i1 %is_owned) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  call void @tb_bootstrap_string_array_array_set_owned(ptr %array, i32 %len, ptr %value, i1 %is_owned)
  %next.len = add i32 %len, 1
  ret i32 %next.len
}
define private ptr @tb_bootstrap_string_array_array_clone(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 @tb_bootstrap_string_array_array_length(ptr %array)
  %clone = call ptr @tb_bootstrap_string_array_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_string_array_array_get(ptr %array, i32 %index)
  %is.item.null = icmp eq ptr %item, null
  br i1 %is.item.null, label %store.null, label %copy.item
copy.item:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %copy.owned, label %copy.borrowed
copy.owned:
  %item.copy = call ptr @tb_bootstrap_string_array_clone(ptr %item)
  call void @tb_bootstrap_string_array_array_set_owned(ptr %clone, i32 %index, ptr %item.copy, i1 true)
  br label %loop.step
copy.borrowed:
  call void @tb_bootstrap_string_array_array_set_owned(ptr %clone, i32 %index, ptr %item, i1 false)
  br label %loop.step
store.null:
  call void @tb_bootstrap_string_array_array_set_owned(ptr %clone, i32 %index, ptr null, i1 false)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %clone
}
define private ptr @tb_bootstrap_string_array_array_last(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_string_array_array_length(ptr %array)
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %last, label %empty
empty:
  call void @abort()
  unreachable
last:
  %index = sub i32 %len, 1
  %row = call ptr @tb_bootstrap_string_array_array_get(ptr %array, i32 %index)
  %clone = call ptr @tb_bootstrap_string_array_clone(ptr %row)
  ret ptr %clone
}
define private ptr @tb_bootstrap_string_array_array_pop(ptr %array) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %pop, label %empty
empty:
  %empty.row = call ptr @tb_bootstrap_string_array_new(i32 0)
  ret ptr %empty.row
pop:
  %index = sub i32 %len, 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %row.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %row = load ptr, ptr %row.slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %row.owned = icmp ne i8 %owned.byte, 0
  br i1 %row.owned, label %transfer, label %clone
transfer:
  br label %remove
clone:
  %row.clone = call ptr @tb_bootstrap_string_array_clone(ptr %row)
  br label %remove
remove:
  %result = phi ptr [%row, %transfer], [%row.clone, %clone]
  store ptr null, ptr %row.slot
  store i8 0, ptr %owned.slot
  %next.len = sub i32 %len, 1
  store i32 %next.len, ptr %len.ptr
  ret ptr %result
}
define private ptr @tb_bootstrap_string_array_array_slice(ptr %array, i64 %start, i64 %end) {
entry:
  %len32 = call i32 @tb_bootstrap_string_array_array_length(ptr %array)
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
  %result = call ptr @tb_bootstrap_string_array_array_new(i32 %slice.len32)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %index64 = sext i32 %index to i64
  %keep.loop = icmp slt i64 %index64, %slice.len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %source.index64 = add i64 %start.clamped, %index64
  %source.index32 = trunc i64 %source.index64 to i32
  %row = call ptr @tb_bootstrap_string_array_array_get(ptr %array, i32 %source.index32)
  %row.null = icmp eq ptr %row, null
  br i1 %row.null, label %store.null, label %clone.row
clone.row:
  %row.copy = call ptr @tb_bootstrap_string_array_clone(ptr %row)
  call void @tb_bootstrap_string_array_array_set_owned(ptr %result, i32 %index, ptr %row.copy, i1 true)
  br label %loop.step
store.null:
  call void @tb_bootstrap_string_array_array_set_owned(ptr %result, i32 %index, ptr null, i1 false)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private void @tb_bootstrap_string_array_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %free], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %loop.done
loop.body:
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %loop.free.item, label %loop.step
loop.free.item:
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %item.value = load ptr, ptr %item.slot
  call void @tb_bootstrap_string_array_free(ptr %item.value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
loop.done:
  call void @free(ptr %owned)
  call void @free(ptr %data)
  call void @free(ptr %array)
  br label %done
done:
  ret void
}
define private void @tb_bootstrap_string_array_array_fill(ptr %array, ptr %value) {
entry:
  %hold = call ptr @tb_bootstrap_string_array_clone(ptr %value)
  %len = call i32 @tb_bootstrap_string_array_array_length(ptr %array)
  br label %fill.cond
fill.cond:
  %index = phi i32 [0, %entry], [%next.index, %fill.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %fill.body, label %fill.done
fill.body:
  %copy = call ptr @tb_bootstrap_string_array_clone(ptr %hold)
  call void @tb_bootstrap_string_array_array_release_slot(ptr %array, i32 %index)
  call void @tb_bootstrap_string_array_array_set_owned(ptr %array, i32 %index, ptr %copy, i1 true)
  br label %fill.step
fill.step:
  %next.index = add i32 %index, 1
  br label %fill.cond
fill.done:
  call void @tb_bootstrap_string_array_free(ptr %hold)
  ret void
}
