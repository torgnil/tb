%tb_bootstrap_int_set = type { i32, i32, ptr, i32, ptr, ptr }

define private i64 @tb_bootstrap_int_set_hash(i64 %value) {
entry:
  %mix1.shift = lshr i64 %value, 33
  %mix1 = xor i64 %value, %mix1.shift
  %mix2 = mul i64 %mix1, -49064778989728563
  %mix2.shift = lshr i64 %mix2, 33
  %mix3 = xor i64 %mix2, %mix2.shift
  %mix4 = mul i64 %mix3, -4265267296055464877
  %mix4.shift = lshr i64 %mix4, 33
  %hash.raw = xor i64 %mix4, %mix4.shift
  %is.zero = icmp eq i64 %hash.raw, 0
  %hash = select i1 %is.zero, i64 1, i64 %hash.raw
  ret i64 %hash
}

define private ptr @tb_bootstrap_int_set_new() {
entry:
  %set = call ptr @malloc(i64 40)
  %data = call ptr @malloc(i64 32)
  %hashes = call ptr @malloc(i64 64)
  %index.values = call ptr @malloc(i64 64)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 32, i1 false)
  call void @llvm.memset.p0.i64(ptr %hashes, i8 0, i64 64, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 0
  %cap.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 2
  %index.cap.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 3
  %hashes.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %index.values.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 5
  store i32 0, ptr %len.ptr
  store i32 4, ptr %cap.ptr
  store ptr %data, ptr %data.ptr
  store i32 8, ptr %index.cap.ptr
  store ptr %hashes, ptr %hashes.ptr
  store ptr %index.values, ptr %index.values.ptr
  ret ptr %set
}

define private i32 @tb_bootstrap_int_set_length(ptr %set) {
entry:
  %is.null = icmp eq ptr %set, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}

define private i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data, i32 %index
  %value = load i64, ptr %slot
  ret i64 %value
}

define private i64 @tb_bootstrap_int_set_find_slot(ptr %set, i64 %hash, i64 %value) {
entry:
  %index.cap.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 3
  %hashes.ptr.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %index.values.ptr.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 5
  %index.cap32 = load i32, ptr %index.cap.ptr
  %index.cap = zext i32 %index.cap32 to i64
  %hashes = load ptr, ptr %hashes.ptr.ptr
  %index.values = load ptr, ptr %index.values.ptr.ptr
  %start = urem i64 %hash, %index.cap
  br label %loop
loop:
  %index = phi i64 [%start, %entry], [%next.index, %next]
  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %index
  %current.hash = load i64, ptr %hash.slot
  %is.empty = icmp eq i64 %current.hash, 0
  br i1 %is.empty, label %found, label %check.hash
check.hash:
  %same.hash = icmp eq i64 %current.hash, %hash
  br i1 %same.hash, label %check.value, label %next
check.value:
  %value.slot = getelementptr inbounds i64, ptr %index.values, i64 %index
  %current.value = load i64, ptr %value.slot
  %is.match = icmp eq i64 %current.value, %value
  br i1 %is.match, label %found, label %next
next:
  %index.plus = add i64 %index, 1
  %next.index = urem i64 %index.plus, %index.cap
  br label %loop
found:
  ret i64 %index
}

define private void @tb_bootstrap_int_set_insert_index(ptr %set, i64 %hash, i64 %value) {
entry:
  %hashes.ptr.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %index.values.ptr.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 5
  %slot.index = call i64 @tb_bootstrap_int_set_find_slot(ptr %set, i64 %hash, i64 %value)
  %hashes = load ptr, ptr %hashes.ptr.ptr
  %index.values = load ptr, ptr %index.values.ptr.ptr
  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index
  %value.slot = getelementptr inbounds i64, ptr %index.values, i64 %slot.index
  store i64 %hash, ptr %hash.slot
  store i64 %value, ptr %value.slot
  ret void
}

define private void @tb_bootstrap_int_set_reserve_for_add(ptr %set) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 0
  %cap.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 2
  %index.cap.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 3
  %hashes.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %index.values.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 5
  %len = load i32, ptr %len.ptr
  %cap = load i32, ptr %cap.ptr
  %data = load ptr, ptr %data.ptr
  %index.cap = load i32, ptr %index.cap.ptr
  %next.len = add i32 %len, 1
  %next.used.twice = mul i32 %next.len, 2
  %has.index.capacity = icmp slt i32 %next.used.twice, %index.cap
  %has.data.capacity = icmp slt i32 %len, %cap
  %has.capacity = and i1 %has.index.capacity, %has.data.capacity
  br i1 %has.capacity, label %done, label %grow
grow:
  %cap.doubled = mul i32 %cap, 2
  %new.cap = select i1 %has.data.capacity, i32 %cap, i32 %cap.doubled
  %index.cap.is_zero = icmp eq i32 %index.cap, 0
  %index.doubled = mul i32 %index.cap, 2
  %new.index.cap = select i1 %has.index.capacity, i32 %index.cap, i32 %index.doubled
  %new.cap64 = sext i32 %new.cap to i64
  %new.index.cap64 = sext i32 %new.index.cap to i64
  %new.data.bytes = mul i64 %new.cap64, 8
  %new.index.bytes = mul i64 %new.index.cap64, 8
  %old.hashes = load ptr, ptr %hashes.ptr
  %old.index.values = load ptr, ptr %index.values.ptr
  %new.data = call ptr @malloc(i64 %new.data.bytes)
  %new.hashes = call ptr @malloc(i64 %new.index.bytes)
  %new.index.values = call ptr @malloc(i64 %new.index.bytes)
  call void @llvm.memset.p0.i64(ptr %new.data, i8 0, i64 %new.data.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %new.hashes, i8 0, i64 %new.index.bytes, i1 false)
  store i32 %new.cap, ptr %cap.ptr
  store ptr %new.data, ptr %data.ptr
  store i32 %new.index.cap, ptr %index.cap.ptr
  store ptr %new.hashes, ptr %hashes.ptr
  store ptr %new.index.values, ptr %index.values.ptr
  %len64 = sext i32 %len to i64
  %old.data.bytes = mul i64 %len64, 8
  call void @llvm.memcpy.p0.p0.i64(ptr %new.data, ptr %data, i64 %old.data.bytes, i1 false)
  br label %rehash.loop
rehash.loop:
  %rehash.index = phi i32 [0, %grow], [%rehash.next.index, %rehash.body]
  %rehash.more = icmp slt i32 %rehash.index, %len
  br i1 %rehash.more, label %rehash.body, label %grow.done
rehash.body:
  %value.slot = getelementptr inbounds i64, ptr %data, i32 %rehash.index
  %value = load i64, ptr %value.slot
  %hash = call i64 @tb_bootstrap_int_set_hash(i64 %value)
  call void @tb_bootstrap_int_set_insert_index(ptr %set, i64 %hash, i64 %value)
  %rehash.next.index = add i32 %rehash.index, 1
  br label %rehash.loop
grow.done:
  call void @free(ptr %data)
  call void @free(ptr %old.hashes)
  call void @free(ptr %old.index.values)
  ret void
done:
  ret void
}

define private i1 @tb_bootstrap_int_set_contains(ptr %set, i64 %value) {
entry:
  %hashes.ptr.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %hash = call i64 @tb_bootstrap_int_set_hash(i64 %value)
  %slot.index = call i64 @tb_bootstrap_int_set_find_slot(ptr %set, i64 %hash, i64 %value)
  %hashes = load ptr, ptr %hashes.ptr.ptr
  %hash.slot = getelementptr inbounds i64, ptr %hashes, i64 %slot.index
  %current.hash = load i64, ptr %hash.slot
  %present = icmp ne i64 %current.hash, 0
  ret i1 %present
}

define private i32 @tb_bootstrap_int_set_add(ptr %set, i64 %value) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 0
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 2
  %present = call i1 @tb_bootstrap_int_set_contains(ptr %set, i64 %value)
  br i1 %present, label %done, label %insert
insert:
  call void @tb_bootstrap_int_set_reserve_for_add(ptr %set)
  %hash = call i64 @tb_bootstrap_int_set_hash(i64 %value)
  call void @tb_bootstrap_int_set_insert_index(ptr %set, i64 %hash, i64 %value)
  %len = load i32, ptr %len.ptr
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds i64, ptr %data, i32 %len
  store i64 %value, ptr %slot
  %next.len = add i32 %len, 1
  store i32 %next.len, ptr %len.ptr
  br label %done
done:
  %result.len = load i32, ptr %len.ptr
  ret i32 %result.len
}

define private ptr @tb_bootstrap_int_set_union(ptr %left, ptr %right) {
entry:
  %result = call ptr @tb_bootstrap_int_set_clone(ptr %left)
  %len = call i32 @tb_bootstrap_int_set_length(ptr %right)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call i64 @tb_bootstrap_int_set_get(ptr %right, i32 %index)
  %ignored = call i32 @tb_bootstrap_int_set_add(ptr %result, i64 %item)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}

define private ptr @tb_bootstrap_to_set_int_array(ptr %array) {
entry:
  %result = call ptr @tb_bootstrap_int_set_new()
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %ignored = call i32 @tb_bootstrap_int_set_add(ptr %result, i64 %item)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}

define private ptr @tb_bootstrap_int_set_clone(ptr %set) {
entry:
  %is.null = icmp eq ptr %set, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %clone = call ptr @tb_bootstrap_int_set_new()
  %len = call i32 @tb_bootstrap_int_set_length(ptr %set)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index)
  %ignored = call i32 @tb_bootstrap_int_set_add(ptr %clone, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %clone
}

define private void @tb_bootstrap_int_set_free(ptr %set) {
entry:
  %is.null = icmp eq ptr %set, null
  br i1 %is.null, label %done, label %free
free:
  %data.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 2
  %hashes.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 4
  %index.values.ptr = getelementptr inbounds %tb_bootstrap_int_set, ptr %set, i32 0, i32 5
  %data = load ptr, ptr %data.ptr
  %hashes = load ptr, ptr %hashes.ptr
  %index.values = load ptr, ptr %index.values.ptr
  call void @free(ptr %data)
  call void @free(ptr %hashes)
  call void @free(ptr %index.values)
  call void @free(ptr %set)
  br label %done
done:
  ret void
}

@.fmt.set.int = private unnamed_addr constant [5 x i8] c"%lld\00"
define private i32 @tb_bootstrap_print_int_set(ptr %set) {
entry:
  %open = call i32 @putchar(i32 123)
  %len = call i32 @tb_bootstrap_int_set_length(ptr %set)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %is.first = icmp eq i32 %index, 0
  br i1 %is.first, label %emit.value, label %emit.sep
emit.sep:
  %comma = call i32 @putchar(i32 44)
  %space = call i32 @putchar(i32 32)
  br label %emit.value
emit.value:
  %value = call i64 @tb_bootstrap_int_set_get(ptr %set, i32 %index)
  %print = call i32 (ptr, ...) @printf(ptr @.fmt.set.int, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  %close = call i32 @putchar(i32 125)
  %nl = call i32 @putchar(i32 10)
  ret i32 0
}
