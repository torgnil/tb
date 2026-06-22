%tb_bootstrap_int_array = type { i32, i32, ptr }
%tb_bootstrap_prio_q_int = type { ptr, ptr }
define private ptr @tb_bootstrap_int_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 16)
  %cap.small = icmp slt i32 %len, 4
  %cap = select i1 %cap.small, i32 4, i32 %len
  %cap64 = sext i32 %cap to i64
  %bytes = mul i64 %cap64, 8
  %data = call ptr @malloc(i64 %bytes)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  store i32 %len, ptr %len.ptr
  %cap.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 1
  store i32 %cap, ptr %cap.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  store ptr %data, ptr %data.ptr
  ret ptr %array
}
define private i32 @tb_bootstrap_int_array_length(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private ptr @tb_bootstrap_int_array_slice(ptr %array, i64 %start, i64 %end) {
entry:
  %len32 = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %len = sext i32 %len32 to i64
  %start.neg = icmp slt i64 %start, 0
  %start.low = select i1 %start.neg, i64 0, i64 %start
  %start.high = icmp sgt i64 %start.low, %len
  %start.clamped = select i1 %start.high, i64 %len, i64 %start.low
  %end.neg = icmp slt i64 %end, 0
  %end.low = select i1 %end.neg, i64 0, i64 %end
  %end.high = icmp sgt i64 %end.low, %len
  %end.clamped.high = select i1 %end.high, i64 %len, i64 %end.low
  %end.before.start = icmp slt i64 %end.clamped.high, %start.clamped
  %end.clamped = select i1 %end.before.start, i64 %start.clamped, i64 %end.clamped.high
  %slice.len64 = sub i64 %end.clamped, %start.clamped
  %slice.len32 = trunc i64 %slice.len64 to i32
  %result = call ptr @tb_bootstrap_int_array_new(i32 %slice.len32)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.body]
  %index64 = sext i32 %index to i64
  %keep.loop = icmp slt i64 %index64, %slice.len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %source.index64 = add i64 %start.clamped, %index64
  %source.index32 = trunc i64 %source.index64 to i32
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %source.index32)
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %value)
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_range(i64 %start, i64 %end) {
entry:
  %delta = sub i64 %end, %start
  %has.items = icmp sgt i64 %delta, 0
  %len64 = select i1 %has.items, i64 %delta, i64 0
  %len = trunc i64 %len64 to i32
  %array = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.body]
  %index64 = sext i32 %index to i64
  %keep.loop = icmp slt i64 %index64, %len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = add i64 %start, %index64
  call void @tb_bootstrap_int_array_set(ptr %array, i32 %index, i64 %value)
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %array
}
define private i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data, i32 %index
  %value = load i64, ptr %slot
  ret i64 %value
}
define private i1 @tb_bootstrap_int_array_contains(ptr %array, i64 %needle) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %notfound
loop.body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %matches = icmp eq i64 %item, %needle
  br i1 %matches, label %found, label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
found:
  ret i1 true
notfound:
  ret i1 false
}
define private void @tb_bootstrap_int_array_set(ptr %array, i32 %index, i64 %value) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data, i32 %index
  store i64 %value, ptr %slot
  ret void
}
define private i32 @tb_bootstrap_cmp_int_desc(ptr %left.ptr, ptr %right.ptr) {
entry:
  %left = load i64, ptr %left.ptr
  %right = load i64, ptr %right.ptr
  %left.gt = icmp sgt i64 %left, %right
  br i1 %left.gt, label %gt, label %check.lt
gt:
  ret i32 -1
check.lt:
  %left.lt = icmp slt i64 %left, %right
  br i1 %left.lt, label %lt, label %eq
lt:
  ret i32 1
eq:
  ret i32 0
}
define private i32 @tb_bootstrap_cmp_int_asc(ptr %left.ptr, ptr %right.ptr) {
entry:
  %left = load i64, ptr %left.ptr
  %right = load i64, ptr %right.ptr
  %left.lt = icmp slt i64 %left, %right
  br i1 %left.lt, label %lt, label %check.gt
lt:
  ret i32 -1
check.gt:
  %left.gt = icmp sgt i64 %left, %right
  br i1 %left.gt, label %gt, label %eq
gt:
  ret i32 1
eq:
  ret i32 0
}
define private ptr @tb_bootstrap_int_array_sort_asc(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %len64 = sext i32 %len to i64
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  call void @qsort(ptr %data, i64 %len64, i64 8, ptr @tb_bootstrap_cmp_int_asc)
  ret ptr %array
}
define private ptr @tb_bootstrap_int_array_sort_by(ptr %array, ptr %cmp) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %len64 = sext i32 %len to i64
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  call void @qsort(ptr %data, i64 %len64, i64 8, ptr %cmp)
  ret ptr %array
}
define private ptr @tb_bootstrap_int_array_sort_desc(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %len64 = sext i32 %len to i64
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  call void @qsort(ptr %data, i64 %len64, i64 8, ptr @tb_bootstrap_cmp_int_desc)
  ret ptr %array
}
define private ptr @tb_bootstrap_create_prio_q_int_by(ptr %array, ptr %cmp) {
entry:
  %clone = call ptr @tb_bootstrap_int_array_clone(ptr %array)
  %sorted = call ptr @tb_bootstrap_int_array_sort_by(ptr %clone, ptr %cmp)
  %pq = call ptr @malloc(i64 16)
  %array.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 0
  %cmp.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 1
  store ptr %sorted, ptr %array.ptr
  store ptr %cmp, ptr %cmp.ptr
  ret ptr %pq
}
define private ptr @tb_bootstrap_create_prio_q_int_desc(ptr %array) {
entry:
  %pq = call ptr @tb_bootstrap_create_prio_q_int_by(ptr %array, ptr @tb_bootstrap_cmp_int_desc)
  ret ptr %pq
}
define private i1 @tb_bootstrap_prio_q_int_is_empty(ptr %pq) {
entry:
  %array.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 0
  %array = load ptr, ptr %array.ptr
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %empty = icmp eq i32 %len, 0
  ret i1 %empty
}
define private i32 @tb_bootstrap_prio_q_int_push(ptr %pq, i64 %value) {
entry:
  %array.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 0
  %array = load ptr, ptr %array.ptr
  %cmp.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 1
  %cmp = load ptr, ptr %cmp.ptr
  %len = call i32 @tb_bootstrap_int_array_push(ptr %array, i64 %value)
  %sorted = call ptr @tb_bootstrap_int_array_sort_by(ptr %array, ptr %cmp)
  ret i32 %len
}
define private i64 @tb_bootstrap_prio_q_int_pop(ptr %pq) {
entry:
  %array.ptr = getelementptr inbounds %tb_bootstrap_prio_q_int, ptr %pq, i32 0, i32 0
  %array = load ptr, ptr %array.ptr
  %value = call i64 @tb_bootstrap_int_array_remove_at(ptr %array, i32 0)
  ret i64 %value
}
define private ptr @tb_bootstrap_int_array_clone(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %clone = call ptr @tb_bootstrap_int_array_new(i32 %len)
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %clone.data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %clone, i32 0, i32 2
  %clone.data = load ptr, ptr %clone.data.ptr
  %len64 = sext i32 %len to i64
  %bytes = mul i64 %len64, 8
  call void @llvm.memcpy.p0.p0.i64(ptr %clone.data, ptr %data, i64 %bytes, i1 false)
  ret ptr %clone
}
define private i32 @tb_bootstrap_int_array_push(ptr %array, i64 %value) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %cap.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data.old = load ptr, ptr %data.ptr
  %need.grow = icmp eq i32 %len, %cap
  br i1 %need.grow, label %grow, label %store
grow:
  %new.cap = mul i32 %cap, 2
  %new.cap64 = sext i32 %new.cap to i64
  %new.bytes = mul i64 %new.cap64, 8
  %new.data = call ptr @malloc(i64 %new.bytes)
  %old.cap64 = sext i32 %cap to i64
  %old.bytes = mul i64 %old.cap64, 8
  call void @llvm.memcpy.p0.p0.i64(ptr %new.data, ptr %data.old, i64 %old.bytes, i1 false)
  call void @free(ptr %data.old)
  store i32 %new.cap, ptr %cap.ptr
  store ptr %new.data, ptr %data.ptr
  br label %store
store:
  %data.current = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data.current, i32 %len
  store i64 %value, ptr %slot
  %next.len = add i32 %len, 1
  store i32 %next.len, ptr %len.ptr
  ret i32 %next.len
}
define private i32 @tb_bootstrap_int_array_insert(ptr %array, i32 %index, i64 %value) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %index.low = icmp slt i32 %index, 0
  %index.nonneg = select i1 %index.low, i32 0, i32 %index
  %index.high = icmp sgt i32 %index.nonneg, %len
  %index.clamped = select i1 %index.high, i32 %len, i32 %index.nonneg
  %new.len = call i32 @tb_bootstrap_int_array_push(ptr %array, i64 0)
  %old.last = sub i32 %new.len, 2
  %need.shift = icmp sgt i32 %old.last, %index.clamped
  br label %loop.cond
loop.cond:
  %current = phi i32 [%old.last, %entry], [%prev.current, %loop.body]
  %keep.loop = icmp sge i32 %current, %index.clamped
  %can.loop = and i1 %need.shift, %keep.loop
  br i1 %can.loop, label %loop.body, label %store
loop.body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %current)
  %dest = add i32 %current, 1
  call void @tb_bootstrap_int_array_set(ptr %array, i32 %dest, i64 %item)
  %prev.current = sub i32 %current, 1
  br label %loop.cond
store:
  call void @tb_bootstrap_int_array_set(ptr %array, i32 %index.clamped, i64 %value)
  ret i32 %new.len
}
define private i64 @tb_bootstrap_int_array_pop(ptr %array) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %is.empty = icmp eq i32 %len, 0
  br i1 %is.empty, label %empty, label %pop
empty:
  ret i64 0
pop:
  %last.index = sub i32 %len, 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data, i32 %last.index
  %value = load i64, ptr %slot
  store i32 %last.index, ptr %len.ptr
  ret i64 %value
}
define private i64 @tb_bootstrap_int_array_remove_at(ptr %array, i32 %index) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %index.low = icmp slt i32 %index, 0
  %index.high = icmp sge i32 %index, %len
  %bad.index = or i1 %index.low, %index.high
  br i1 %bad.index, label %empty, label %remove
empty:
  ret i64 0
remove:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %last.index = sub i32 %len, 1
  %has.tail = icmp slt i32 %index, %last.index
  br i1 %has.tail, label %loop.cond, label %shrink
loop.cond:
  %current = phi i32 [%index, %remove], [%next.current, %loop.body]
  %keep.loop = icmp slt i32 %current, %last.index
  br i1 %keep.loop, label %loop.body, label %shrink
loop.body:
  %src = add i32 %current, 1
  %item = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %src)
  call void @tb_bootstrap_int_array_set(ptr %array, i32 %current, i64 %item)
  %next.current = add i32 %current, 1
  br label %loop.cond
shrink:
  store i32 %last.index, ptr %len.ptr
  ret i64 %value
}
define private void @tb_bootstrap_int_array_clear(ptr %array) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 0
  store i32 0, ptr %len.ptr
  ret void
}
define private i64 @tb_bootstrap_int_array_sum(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %sum = phi i64 [0, %entry], [%next.sum, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %next.sum = add i64 %sum, %value
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret i64 %sum
}
define private i32 @tb_bootstrap_print_int_array(ptr %array) {
entry:
  %open = call i32 (ptr, ...) @printf(ptr @.fmt.array.open)
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %is.first = icmp eq i32 %index, 0
  br i1 %is.first, label %print.value, label %print.sep
print.sep:
  %sep = call i32 (ptr, ...) @printf(ptr @.fmt.array.sep)
  br label %print.value
print.value:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %printed = call i32 (ptr, ...) @printf(ptr @.fmt.array.value, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  %close = call i32 (ptr, ...) @printf(ptr @.fmt.array.close)
  ret i32 %close
}

define private void @tb_bootstrap_int_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  call void @free(ptr %data)
  call void @free(ptr %array)
  br label %done
done:
  ret void
}
