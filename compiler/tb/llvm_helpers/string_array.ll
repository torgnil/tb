%tb_bootstrap_string_array = type { i32, i32, ptr, ptr }
@tb_rt_an = internal global i64 0
@tb_rt_as = internal global i64 0
@tb_rt_ap = internal global i64 0
@tb_rt_ag = internal global i64 0
@tb_rt_ah = internal global i64 0
@.fmt.rt.sc = private unnamed_addr constant [9 x i8] c"sc=%lld\0A\00"
@.fmt.rt.sb = private unnamed_addr constant [9 x i8] c"sb=%lld\0A\00"
@.fmt.rt.xc = private unnamed_addr constant [9 x i8] c"xc=%lld\0A\00"
@.fmt.rt.xb = private unnamed_addr constant [9 x i8] c"xb=%lld\0A\00"
@.fmt.rt.ic = private unnamed_addr constant [9 x i8] c"ic=%lld\0A\00"
@.fmt.rt.ib = private unnamed_addr constant [9 x i8] c"ib=%lld\0A\00"
@.fmt.rt.an = private unnamed_addr constant [9 x i8] c"an=%lld\0A\00"
@.fmt.rt.as = private unnamed_addr constant [9 x i8] c"as=%lld\0A\00"
@.fmt.rt.ap = private unnamed_addr constant [9 x i8] c"ap=%lld\0A\00"
@.fmt.rt.ag = private unnamed_addr constant [9 x i8] c"ag=%lld\0A\00"
@.fmt.rt.ah = private unnamed_addr constant [9 x i8] c"ah=%lld\0A\00"
define private ptr @tb_bootstrap_string_array_new(i32 %len) {
entry:
  %array = call ptr @malloc(i64 24)
  %len64 = sext i32 %len to i64
  %has.items = icmp sgt i32 %len, 0
  %alloc.len64 = select i1 %has.items, i64 %len64, i64 1
  %an.old = load i64, ptr @tb_rt_an
  %an.new = add i64 %an.old, 1
  store i64 %an.new, ptr @tb_rt_an
  %as.old = load i64, ptr @tb_rt_as
  %as.new = add i64 %as.old, %alloc.len64
  store i64 %as.new, ptr @tb_rt_as
  %bytes = mul i64 %alloc.len64, 8
  %data = call ptr @malloc(i64 %bytes)
  %owned = call ptr @malloc(i64 %alloc.len64)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %alloc.len64, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 0
  %cap.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 3
  store i32 %len, ptr %len.ptr
  %cap32 = trunc i64 %alloc.len64 to i32
  store i32 %cap32, ptr %cap.ptr
  store ptr %data, ptr %data.ptr
  store ptr %owned, ptr %owned.ptr
  ret ptr %array
}
define private void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %index, ptr %value, i1 %is_owned) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr %value, ptr %slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
}
define private void @tb_bootstrap_string_array_release_slot(ptr %array, i32 %index) {
entry:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %free.item, label %done
free.item:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %item.value = load ptr, ptr %item.slot
  call void @free(ptr %item.value)
  store ptr null, ptr %item.slot
  store i8 0, ptr %owned.slot
  br label %done
done:
  ret void
}
define private i32 @tb_bootstrap_string_array_length(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %value = load ptr, ptr %slot
  ret ptr %value
}
define private ptr @tb_bootstrap_string_array_slice(ptr %array, i64 %start, i64 %end) {
entry:
  %len32 = call i32 @tb_bootstrap_string_array_length(ptr %array)
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
  %result = call ptr @tb_bootstrap_string_array_new(i32 %slice.len32)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %index64 = sext i32 %index to i64
  %keep.loop = icmp slt i64 %index64, %slice.len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %source.index64 = add i64 %start.clamped, %index64
  %source.index32 = trunc i64 %source.index64 to i32
  %value = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %source.index32)
  %value.copy = call ptr @tb_bootstrap_string_copy(ptr %value)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 %index, ptr %value.copy, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private i32 @tb_bootstrap_string_array_push(ptr %array, ptr %value, i1 %is_owned) {
entry:
  %ap.old = load i64, ptr @tb_rt_ap
  %ap.new = add i64 %ap.old, 1
  store i64 %ap.new, ptr @tb_rt_ap
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %cap.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %next.len = add i32 %len, 1
  %has.capacity = icmp slt i32 %len, %cap
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %data.old = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 3
  %owned.old = load ptr, ptr %owned.ptr
  br i1 %has.capacity, label %store.existing, label %grow
store.existing:
  %slot.existing = getelementptr inbounds ptr, ptr %data.old, i32 %len
  store ptr %value, ptr %slot.existing
  %owned.slot.existing = getelementptr inbounds i8, ptr %owned.old, i32 %len
  %owned.byte.existing = zext i1 %is_owned to i8
  store i8 %owned.byte.existing, ptr %owned.slot.existing
  store i32 %next.len, ptr %len.ptr
  ret i32 %next.len
grow:
  %cap.is.zero = icmp eq i32 %cap, 0
  %cap.twice = mul i32 %cap, 2
  %cap.base = select i1 %cap.is.zero, i32 1, i32 %cap.twice
  %cap.big.enough = icmp sge i32 %cap.base, %next.len
  %new.cap = select i1 %cap.big.enough, i32 %cap.base, i32 %next.len
  %new.cap64 = sext i32 %new.cap to i64
  %ag.old = load i64, ptr @tb_rt_ag
  %ag.new = add i64 %ag.old, 1
  store i64 %ag.new, ptr @tb_rt_ag
  %ah.old = load i64, ptr @tb_rt_ah
  %ah.new = add i64 %ah.old, %new.cap64
  store i64 %ah.new, ptr @tb_rt_ah
  %data.bytes = mul i64 %new.cap64, 8
  %owned.bytes = mul i64 %new.cap64, 1
  %data.new = call ptr @malloc(i64 %data.bytes)
  %owned.new = call ptr @malloc(i64 %owned.bytes)
  call void @llvm.memset.p0.i64(ptr %data.new, i8 0, i64 %data.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned.new, i8 0, i64 %owned.bytes, i1 false)
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %copy.old, label %store.new
copy.old:
  %len64 = sext i32 %len to i64
  %old.data.bytes = mul i64 %len64, 8
  %old.owned.bytes = mul i64 %len64, 1
  call void @llvm.memcpy.p0.p0.i64(ptr %data.new, ptr %data.old, i64 %old.data.bytes, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr %owned.new, ptr %owned.old, i64 %old.owned.bytes, i1 false)
  br label %store.new
store.new:
  %slot = getelementptr inbounds ptr, ptr %data.new, i32 %len
  store ptr %value, ptr %slot
  %owned.slot = getelementptr inbounds i8, ptr %owned.new, i32 %len
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  call void @free(ptr %data.old)
  call void @free(ptr %owned.old)
  store i32 %new.cap, ptr %cap.ptr
  store ptr %data.new, ptr %data.ptr
  store ptr %owned.new, ptr %owned.ptr
  store i32 %next.len, ptr %len.ptr
  ret i32 %next.len
}
define private i1 @tb_bootstrap_string_array_contains(ptr %array, ptr %needle) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %notfound
loop.body:
  %item = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %cmp = call i32 @strcmp(ptr %item, ptr %needle)
  %matches = icmp eq i32 %cmp, 0
  br i1 %matches, label %found, label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
found:
  ret i1 true
notfound:
  ret i1 false
}
define private i32 @tb_bootstrap_print_string_array(ptr %array) {
entry:
  %open = call i32 (ptr, ...) @printf(ptr @.fmt.str_array.open)
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %is.first = icmp eq i32 %index, 0
  br i1 %is.first, label %emit.value, label %emit.sep
emit.sep:
  %sep = call i32 (ptr, ...) @printf(ptr @.fmt.str_array.sep)
  br label %emit.value
emit.value:
  %value = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %printed = call i32 (ptr, ...) @printf(ptr @.fmt.str_array.value, ptr %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  %close = call i32 (ptr, ...) @printf(ptr @.fmt.str_array.close)
  ret i32 0
}
define private ptr @tb_bootstrap_split_lines(ptr %src) {
entry:
  %array = call ptr @tb_bootstrap_split_char(ptr %src, i8 10)
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %check.last, label %done
check.last:
  %last.index = sub i32 %len, 1
  %last.item = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %last.index)
  %last.len = call i64 @strlen(ptr %last.item)
  %drop.last = icmp eq i64 %last.len, 0
  br i1 %drop.last, label %trim, label %done
trim:
  call void @tb_bootstrap_string_array_release_slot(ptr %array, i32 %last.index)
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 0
  store i32 %last.index, ptr %len.ptr
  br label %done
done:
  ret ptr %array
}
define private void @tb_bootstrap_dump_runtime_activity() {
entry:
  %sc = load i64, ptr @tb_rt_sc
  %sb = load i64, ptr @tb_rt_sb
  %xc = load i64, ptr @tb_rt_xc
  %xb = load i64, ptr @tb_rt_xb
  %ic = load i64, ptr @tb_rt_ic
  %ib = load i64, ptr @tb_rt_ib
  %an = load i64, ptr @tb_rt_an
  %as = load i64, ptr @tb_rt_as
  %ap = load i64, ptr @tb_rt_ap
  %ag = load i64, ptr @tb_rt_ag
  %ah = load i64, ptr @tb_rt_ah
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.sc, i64 %sc)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.sb, i64 %sb)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.xc, i64 %xc)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.xb, i64 %xb)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.ic, i64 %ic)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.ib, i64 %ib)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.an, i64 %an)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.as, i64 %as)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.ap, i64 %ap)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.ag, i64 %ag)
  call i32 (ptr, ...) @printf(ptr @.fmt.rt.ah, i64 %ah)
  ret void
}
define private ptr @tb_bootstrap_string_array_clone(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  %clone = call ptr @tb_bootstrap_string_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %is.item.null = icmp eq ptr %item, null
  br i1 %is.item.null, label %store.null, label %copy.item
copy.item:
  %item.copy = call ptr @tb_bootstrap_string_copy(ptr %item)
  call void @tb_bootstrap_string_array_set_owned(ptr %clone, i32 %index, ptr %item.copy, i1 true)
  br label %loop.step
store.null:
  call void @tb_bootstrap_string_array_set_owned(ptr %clone, i32 %index, ptr null, i1 false)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %clone
}
define private void @tb_bootstrap_string_array_free(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %len.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_string_array, ptr %array, i32 0, i32 3
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
  call void @free(ptr %item.value)
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
define private ptr @tb_bootstrap_split_chars(ptr %src) {
entry:
  %len64 = call i64 @strlen(ptr %src)
  %len32 = trunc i64 %len64 to i32
  %array = call ptr @tb_bootstrap_string_array_new(i32 %len32)
  br label %loop.cond
loop.cond:
  %index = phi i64 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i64 %index, %len64
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call ptr @tb_bootstrap_string_char_at(ptr %src, i64 %index)
  %index32 = trunc i64 %index to i32
  call void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %index32, ptr %item, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i64 %index, 1
  br label %loop.cond
done:
  ret ptr %array
}
define private ptr @tb_bootstrap_join_strings(ptr %array, ptr %delimiter) {
entry:
  %result.slot = alloca ptr
  %empty = call ptr @malloc(i64 1)
  store i8 0, ptr %empty
  store ptr %empty, ptr %result.slot
  %len = call i32 @tb_bootstrap_string_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step.item]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %current = load ptr, ptr %result.slot
  %item = call ptr @tb_bootstrap_string_array_get(ptr %array, i32 %index)
  %has.delim = icmp sgt i32 %index, 0
  br i1 %has.delim, label %loop.delim, label %loop.item
loop.delim:
  %with.delim = call ptr @tb_bootstrap_string_concat(ptr %current, ptr %delimiter)
  call void @free(ptr %current)
  store ptr %with.delim, ptr %result.slot
  br label %loop.item
loop.item:
  %current.item = load ptr, ptr %result.slot
  %next.value = call ptr @tb_bootstrap_string_concat(ptr %current.item, ptr %item)
  call void @free(ptr %current.item)
  store ptr %next.value, ptr %result.slot
  br label %loop.step.item
loop.step.item:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  %result = load ptr, ptr %result.slot
  ret ptr %result
}
