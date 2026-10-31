define private i64 @tb_bootstrap_hash_int_array(ptr %value) {
entry:
  %len32 = call i32 @tb_bootstrap_int_array_length(ptr %value)
  %len = sext i32 %len32 to i64
  %hash.seed.raw = mul i64 5381, 33
  %hash.seed = add i64 %hash.seed.raw, %len
  br label %loop
loop:
  %index = phi i32 [0, %entry], [%next.index, %body]
  %hash = phi i64 [%hash.seed, %entry], [%next.hash, %body]
  %done = icmp sge i32 %index, %len32
  br i1 %done, label %exit, label %body
body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %value, i32 %index)
  %hash.item = mul i64 %hash, 33
  %next.hash = add i64 %hash.item, %item
  %next.index = add i32 %index, 1
  br label %loop
exit:
  ret i64 %hash
}

define private i1 @tb_bootstrap_int_array_equals(ptr %left, ptr %right) {
entry:
  %left.len = call i32 @tb_bootstrap_int_array_length(ptr %left)
  %right.len = call i32 @tb_bootstrap_int_array_length(ptr %right)
  %len.match = icmp eq i32 %left.len, %right.len
  br i1 %len.match, label %loop.cond, label %false
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %left.len
  br i1 %keep.loop, label %loop.body, label %true
loop.body:
  %left.item = call i64 @tb_bootstrap_int_array_get(ptr %left, i32 %index)
  %right.item = call i64 @tb_bootstrap_int_array_get(ptr %right, i32 %index)
  %item.match = icmp eq i64 %left.item, %right.item
  br i1 %item.match, label %loop.step, label %false
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
true:
  ret i1 true
false:
  ret i1 false
}

define private i32 __MAP_REHASH_INSERT_NAME__(ptr %keys, ptr %values, ptr %owned, ptr %states, i32 %cap, ptr %key, __VALUE_LLVM_TYPE__ %value, i8 %owned.byte) {
entry:
  %hash = call i64 @tb_bootstrap_hash_int_array(ptr %key)
  %cap64 = zext i32 %cap to i64
  %slot64 = urem i64 %hash, %cap64
  %slot = trunc i64 %slot64 to i32
  br label %probe
probe:
  %index = phi i32 [%slot, %entry], [%next.index, %step]
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %is.empty = icmp eq i8 %state, 0
  br i1 %is.empty, label %insert, label %step
insert:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %index
  store ptr %key, ptr %key.slot
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  store __VALUE_LLVM_TYPE__ %value, ptr %value.slot
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  store i8 %owned.byte, ptr %owned.slot
  store i8 1, ptr %state.slot
  ret i32 %index
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
}

define private void __MAP_GROW_NAME__(ptr %map) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %old.cap = load i32, ptr %cap.ptr
  %grown = mul i32 %old.cap, 2
  %new.cap = add i32 %grown, 1
  %new.cap64 = zext i32 %new.cap to i64
  %key.bytes = mul i64 %new.cap64, 8
  %keys.new = call ptr @malloc(i64 %key.bytes)
  %values.end = getelementptr __VALUE_LLVM_TYPE__, ptr null, i32 %new.cap
  %value.bytes = ptrtoint ptr %values.end to i64
  %values.new = call ptr @malloc(i64 %value.bytes)
  %owned.new = call ptr @malloc(i64 %new.cap64)
  %states.new = call ptr @malloc(i64 %new.cap64)
  %order.bytes = mul i64 %new.cap64, 4
  %order.new = call ptr @malloc(i64 %order.bytes)
  call void @llvm.memset.p0.i64(ptr %keys.new, i8 0, i64 %key.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %values.new, i8 0, i64 %value.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned.new, i8 0, i64 %new.cap64, i1 false)
  call void @llvm.memset.p0.i64(ptr %states.new, i8 0, i64 %new.cap64, i1 false)
  call void @llvm.memset.p0.i64(ptr %order.new, i8 0, i64 %order.bytes, i1 false)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %old.keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %old.values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %old.owned = load ptr, ptr %owned.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %old.states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %old.order = load ptr, ptr %order.ptr
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %old.order.slot = getelementptr inbounds i32, ptr %old.order, i32 %index
  %old.slot = load i32, ptr %old.order.slot
  br label %rehash
rehash:
  %key.slot = getelementptr inbounds ptr, ptr %old.keys, i32 %old.slot
  %key = load ptr, ptr %key.slot
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %old.values, i32 %old.slot
  %value = load __VALUE_LLVM_TYPE__, ptr %value.slot
  %owned.slot = getelementptr inbounds i8, ptr %old.owned, i32 %old.slot
  %owned.byte = load i8, ptr %owned.slot
  %new.slot = call i32 __MAP_REHASH_INSERT_NAME__(ptr %keys.new, ptr %values.new, ptr %owned.new, ptr %states.new, i32 %new.cap, ptr %key, __VALUE_LLVM_TYPE__ %value, i8 %owned.byte)
  %order.new.slot = getelementptr inbounds i32, ptr %order.new, i32 %index
  store i32 %new.slot, ptr %order.new.slot
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  call void @free(ptr %old.keys)
  call void @free(ptr %old.values)
  call void @free(ptr %old.owned)
  call void @free(ptr %old.states)
  call void @free(ptr %old.order)
  store i32 %new.cap, ptr %cap.ptr
  store ptr %keys.new, ptr %keys.ptr
  store ptr %values.new, ptr %values.ptr
  store ptr %owned.new, ptr %owned.ptr
  store ptr %states.new, ptr %states.ptr
  store ptr %order.new, ptr %order.ptr
  ret void
}

define private ptr __MAP_NEW_NAME__(i32 %len) {
entry:
  %size.ptr = getelementptr __MAP_STRUCT__, ptr null, i32 1
  %size = ptrtoint ptr %size.ptr to i64
  %map = call ptr @malloc(i64 %size)
  %double.len = mul i32 %len, 2
  %requested.cap = add i32 %double.len, 1
  %small = icmp slt i32 %requested.cap, 8
  %cap = select i1 %small, i32 8, i32 %requested.cap
  %cap64 = zext i32 %cap to i64
  %key.bytes = mul i64 %cap64, 8
  %keys = call ptr @malloc(i64 %key.bytes)
  %values.end = getelementptr __VALUE_LLVM_TYPE__, ptr null, i32 %cap
  %value.bytes = ptrtoint ptr %values.end to i64
  %values = call ptr @malloc(i64 %value.bytes)
  %owned = call ptr @malloc(i64 %cap64)
  %states = call ptr @malloc(i64 %cap64)
  %order.bytes = mul i64 %cap64, 4
  %order = call ptr @malloc(i64 %order.bytes)
  call void @llvm.memset.p0.i64(ptr %keys, i8 0, i64 %key.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %values, i8 0, i64 %value.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %cap64, i1 false)
  call void @llvm.memset.p0.i64(ptr %states, i8 0, i64 %cap64, i1 false)
  call void @llvm.memset.p0.i64(ptr %order, i8 0, i64 %order.bytes, i1 false)
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  store i32 0, ptr %len.ptr
  store i32 %cap, ptr %cap.ptr
  store ptr %keys, ptr %keys.ptr
  store ptr %values, ptr %values.ptr
  store ptr %owned, ptr %owned.ptr
  store ptr %states, ptr %states.ptr
  store ptr %order, ptr %order.ptr
  ret ptr %map
}

define private void __MAP_SET_NAME__(ptr %map, i32 %index, ptr %key, __VALUE_LLVM_TYPE__ %value, i1 %is_owned) {
entry:
  call void __MAP_SET_BY_KEY_NAME__(ptr %map, ptr %key, __VALUE_LLVM_TYPE__ %value, i1 %is_owned)
  ret void
}

define private i32 __MAP_LENGTH_NAME__(ptr %map) {
entry:
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}

define private __VALUE_LLVM_TYPE__ __MAP_GET_NAME__(ptr %map, ptr %key) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %order = load ptr, ptr %order.ptr
  %hash = call i64 @tb_bootstrap_hash_int_array(ptr %key)
  %cap64 = zext i32 %cap to i64
  %slot64 = urem i64 %hash, %cap64
  %slot = trunc i64 %slot64 to i32
  br label %probe
probe:
  %index = phi i32 [%slot, %entry], [%next.index, %step]
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %is.empty = icmp eq i8 %state, 0
  br i1 %is.empty, label %missing, label %check
check:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %index
  %key.value = load ptr, ptr %key.slot
  %key.match = call i1 @tb_bootstrap_int_array_equals(ptr %key.value, ptr %key)
  br i1 %key.match, label %found, label %step
found:
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  %value.result = load __VALUE_LLVM_TYPE__, ptr %value.slot
  ret __VALUE_LLVM_TYPE__ %value.result
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
missing:
  ret __VALUE_LLVM_TYPE__ __ZERO_VALUE__
}

define private i1 __MAP_CONTAINS_NAME__(ptr %map, ptr %key) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %hash = call i64 @tb_bootstrap_hash_int_array(ptr %key)
  %cap64 = zext i32 %cap to i64
  %slot64 = urem i64 %hash, %cap64
  %slot = trunc i64 %slot64 to i32
  br label %probe
probe:
  %index = phi i32 [%slot, %entry], [%next.index, %step]
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %is.empty = icmp eq i8 %state, 0
  br i1 %is.empty, label %missing, label %check
check:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %index
  %key.value = load ptr, ptr %key.slot
  %key.match = call i1 @tb_bootstrap_int_array_equals(ptr %key.value, ptr %key)
  br i1 %key.match, label %found, label %step
found:
  ret i1 true
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
missing:
  ret i1 false
}


define private void __MAP_SET_BY_KEY_NAME__(ptr %map, ptr %key, __VALUE_LLVM_TYPE__ %value, i1 %is_owned) {
entry:
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %next.len = add i32 %len, 1
  %load.left = mul i32 %next.len, 10
  %load.right = mul i32 %cap, 7
  %needs.grow = icmp sgt i32 %load.left, %load.right
  br i1 %needs.grow, label %grow, label %probe.setup
grow:
  call void __MAP_GROW_NAME__(ptr %map)
  br label %probe.setup
probe.setup:
  %cap.ptr.reload = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap.reload = load i32, ptr %cap.ptr.reload
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %owned = load ptr, ptr %owned.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %order = load ptr, ptr %order.ptr
  %hash = call i64 @tb_bootstrap_hash_int_array(ptr %key)
  %cap64 = zext i32 %cap.reload to i64
  %slot64 = urem i64 %hash, %cap64
  %slot = trunc i64 %slot64 to i32
  br label %probe
probe:
  %index = phi i32 [%slot, %probe.setup], [%next.index, %step]
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %is.empty = icmp eq i8 %state, 0
  br i1 %is.empty, label %insert, label %check
check:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %index
  %key.value = load ptr, ptr %key.slot
  %key.match = call i1 @tb_bootstrap_int_array_equals(ptr %key.value, ptr %key)
  br i1 %key.match, label %update, label %step
update:
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  store __VALUE_LLVM_TYPE__ %value, ptr %value.slot
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
insert:
  %key.copy = call ptr @tb_bootstrap_int_array_clone(ptr %key)
  %key.slot.insert = getelementptr inbounds ptr, ptr %keys, i32 %index
  store ptr %key.copy, ptr %key.slot.insert
  %value.slot.insert = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  store __VALUE_LLVM_TYPE__ %value, ptr %value.slot.insert
  %owned.slot.insert = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte.insert = zext i1 %is_owned to i8
  store i8 %owned.byte.insert, ptr %owned.slot.insert
  store i8 1, ptr %state.slot
  %len.old = load i32, ptr %len.ptr
  %order.slot = getelementptr inbounds i32, ptr %order, i32 %len.old
  store i32 %index, ptr %order.slot
  %len.new = add i32 %len.old, 1
  store i32 %len.new, ptr %len.ptr
  ret void
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap.reload
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
}


define private void __MAP_RELEASE_BY_KEY_NAME__(ptr %map, ptr %key) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %owned = load ptr, ptr %owned.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %hash = call i64 @tb_bootstrap_hash_int_array(ptr %key)
  %cap64 = zext i32 %cap to i64
  %slot64 = urem i64 %hash, %cap64
  %slot = trunc i64 %slot64 to i32
  br label %probe
probe:
  %index = phi i32 [%slot, %entry], [%next.index, %step]
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %is.empty = icmp eq i8 %state, 0
  br i1 %is.empty, label %done, label %check
check:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %index
  %key.value = load ptr, ptr %key.slot
  %key.match = call i1 @tb_bootstrap_int_array_equals(ptr %key.value, ptr %key)
  br i1 %key.match, label %found, label %step
found:
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %value.owned = icmp ne i8 %owned.byte, 0
  br i1 %value.owned, label %release, label %done
release:
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  %value.raw = load __VALUE_LLVM_TYPE__, ptr %value.slot
__VALUE_RELEASE_BLOCK__
  store __VALUE_LLVM_TYPE__ __ZERO_VALUE__, ptr %value.slot
  store i8 0, ptr %owned.slot
  br label %done
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
done:
  ret void
}


define private ptr __MAP_KEYS_NAME__(ptr %map) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %result = call ptr @tb_bootstrap_int_array_array_new(i32 %len)
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %order = load ptr, ptr %order.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %order.slot = getelementptr inbounds i32, ptr %order, i32 %index
  %slot = load i32, ptr %order.slot
  br label %emit
emit:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %slot
  %key.value = load ptr, ptr %key.slot
  %key.copy = call ptr @tb_bootstrap_int_array_clone(ptr %key.value)
  call void @tb_bootstrap_int_array_array_set_owned(ptr %result, i32 %index, ptr %key.copy, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}

__VALUES_BLOCK__

define private ptr __MAP_CLONE_NAME__(ptr %map) {
entry:
  %is.null = icmp eq ptr %map, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %clone = call ptr __MAP_NEW_NAME__(i32 %len)
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %owned = load ptr, ptr %owned.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %order = load ptr, ptr %order.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %order.slot = getelementptr inbounds i32, ptr %order, i32 %index
  %slot = load i32, ptr %order.slot
  br label %clone.entry
clone.entry:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %slot
  %key.value = load ptr, ptr %key.slot
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %slot
  %value.raw = load __VALUE_LLVM_TYPE__, ptr %value.slot
__CLONE_VALUE_COPY_BLOCK__
  call void __MAP_SET_NAME__(ptr %clone, i32 0, ptr %key.value, __VALUE_LLVM_TYPE__ __CLONE_STORED_VALUE__, i1 __CLONE_STORED_OWNED__)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %clone
}

define private void __MAP_FREE_NAME__(ptr %map) {
entry:
  %is.null = icmp eq ptr %map, null
  br i1 %is.null, label %done, label %free
free:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %owned = load ptr, ptr %owned.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 5
  %states = load ptr, ptr %states.ptr
  %order.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 6
  %order = load ptr, ptr %order.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %free], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %loop.done
loop.body:
  %order.slot = getelementptr inbounds i32, ptr %order, i32 %index
  %slot = load i32, ptr %order.slot
  br label %release.entry
release.entry:
  %key.slot = getelementptr inbounds ptr, ptr %keys, i32 %slot
  %key.value = load ptr, ptr %key.slot
  call void @tb_bootstrap_int_array_free(ptr %key.value)
__FREE_VALUE_BLOCK__
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
loop.done:
  call void @free(ptr %states)
  call void @free(ptr %owned)
  call void @free(ptr %order)
  call void @free(ptr %keys)
  call void @free(ptr %values)
  call void @free(ptr %map)
  br label %done
done:
  ret void
}
