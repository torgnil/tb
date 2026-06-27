%tb_bootstrap_int_array_array = type { i32, ptr, ptr }
define private ptr @tb_bootstrap_int_array_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 24)
  %len64 = sext i32 %len to i64
  %bytes = mul i64 %len64, 8
  %data = call ptr @malloc(i64 %bytes)
  %owned = call ptr @malloc(i64 %len64)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %len64, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 0
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %owned.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 2
  store i32 %len, ptr %len.ptr
  store ptr %data, ptr %data.ptr
  store ptr %owned, ptr %owned.ptr
  ret ptr %array
}
define private i32 @tb_bootstrap_int_array_array_length(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private ptr @tb_bootstrap_int_array_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %value = load ptr, ptr %slot
  ret ptr %value
}
define private void @tb_bootstrap_int_array_array_release_slot(ptr %array, i32 %index) {
entry:
  %len = call i32 @tb_bootstrap_int_array_array_length(ptr %array)
  %in.bounds = icmp slt i32 %index, %len
  br i1 %in.bounds, label %check, label %done
check:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %free.item, label %done
free.item:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %item.value = load ptr, ptr %item.slot
  call void @tb_bootstrap_int_array_free(ptr %item.value)
  store ptr null, ptr %item.slot
  store i8 0, ptr %owned.slot
  br label %done
done:
  ret void
}
define private void @tb_bootstrap_int_array_array_set_owned(ptr %array, i32 %index, ptr %value, i1 %is_owned) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 0
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
  call void @llvm.memset.p0.i64(ptr %data.new, i8 0, i64 %data.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned.new, i8 0, i64 %owned.bytes, i1 false)
  %data.ptr.grow = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %data.old = load ptr, ptr %data.ptr.grow
  %owned.ptr.grow = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 2
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
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr %value, ptr %slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 2
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
}
define private i32 @tb_bootstrap_int_array_array_push(ptr %array, ptr %value, i1 %is_owned) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  call void @tb_bootstrap_int_array_array_set_owned(ptr %array, i32 %len, ptr %value, i1 %is_owned)
  %next.len = add i32 %len, 1
  ret i32 %next.len
}
define private ptr @tb_bootstrap_int_array_array_clone(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 @tb_bootstrap_int_array_array_length(ptr %array)
  %clone = call ptr @tb_bootstrap_int_array_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_int_array_array_get(ptr %array, i32 %index)
  %is.item.null = icmp eq ptr %item, null
  br i1 %is.item.null, label %store.null, label %copy.item
copy.item:
  %item.copy = call ptr @tb_bootstrap_int_array_clone(ptr %item)
  call void @tb_bootstrap_int_array_array_set_owned(ptr %clone, i32 %index, ptr %item.copy, i1 true)
  br label %loop.step
store.null:
  call void @tb_bootstrap_int_array_array_set_owned(ptr %clone, i32 %index, ptr null, i1 false)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %clone
}
define private ptr @tb_bootstrap_int_array_array_filter_bounds(ptr %array, i64 %r, i64 %c, i64 %width, i64 %height) {
entry:
  %len = call i32 @tb_bootstrap_int_array_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_array_new(i32 0)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_int_array_array_get(ptr %array, i32 %index)
  %d0 = call i64 @tb_bootstrap_int_array_get(ptr %item, i32 0)
  %d1 = call i64 @tb_bootstrap_int_array_get(ptr %item, i32 1)
  %row = add i64 %r, %d0
  %col = add i64 %c, %d1
  %row.min = icmp sge i64 %row, 0
  %row.max = icmp slt i64 %row, %width
  %col.min = icmp sge i64 %col, 0
  %col.max = icmp slt i64 %col, %height
  %keep.row = and i1 %row.min, %row.max
  %keep.col = and i1 %col.min, %col.max
  %keep.item = and i1 %keep.row, %keep.col
  br i1 %keep.item, label %keep, label %loop.step
keep:
  %item.copy = call ptr @tb_bootstrap_int_array_clone(ptr %item)
  %pushed = call i32 @tb_bootstrap_int_array_array_push(ptr %result, ptr %item.copy, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private i64 @tb_bootstrap_int_array_array_sum_grid_eq(ptr %array, ptr %grid, i64 %r, i64 %c, ptr %needle) {
entry:
  %len = call i32 @tb_bootstrap_int_array_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %sum = phi i64 [0, %entry], [%next.sum, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_int_array_array_get(ptr %array, i32 %index)
  %d0 = call i64 @tb_bootstrap_int_array_get(ptr %item, i32 0)
  %d1 = call i64 @tb_bootstrap_int_array_get(ptr %item, i32 1)
  %row = add i64 %r, %d0
  %col = add i64 %c, %d1
  %row.i32 = trunc i64 %row to i32
  %row.line = call ptr @tb_bootstrap_string_array_get(ptr %grid, i32 %row.i32)
  %char = call ptr @tb_bootstrap_string_char_at(ptr %row.line, i64 %col)
  %cmp = call i32 @strcmp(ptr %char, ptr %needle)
  call void @tb_release(ptr %char)
  %match = icmp eq i32 %cmp, 0
  %match.i64 = zext i1 %match to i64
  %next.sum = add i64 %sum, %match.i64
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret i64 %sum
}
define private void @tb_bootstrap_int_array_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 1
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_int_array_array, ptr %array, i32 0, i32 2
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
  call void @tb_bootstrap_int_array_free(ptr %item.value)
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
