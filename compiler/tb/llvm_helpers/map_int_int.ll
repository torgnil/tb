define private void @tb_bootstrap_map_int_int_insert_rehash(ptr %keys, ptr %values, ptr %states, i32 %cap, i64 %key, i64 %value) {
entry:
  %hash = call i64 @tb_bootstrap_hash_int(i64 %key)
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
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  store i64 %key, ptr %key.slot
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  store i64 %value, ptr %value.slot
  store i8 1, ptr %state.slot
  ret void
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
}

define private void @tb_bootstrap_map_int_int_grow(ptr %map) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %old.cap = load i32, ptr %cap.ptr
  %grown = mul i32 %old.cap, 2
  %new.cap = add i32 %grown, 1
  %new.cap64 = zext i32 %new.cap to i64
  %key.bytes = mul i64 %new.cap64, 8
  %keys.new = call ptr @malloc(i64 %key.bytes)
  %value.bytes = mul i64 %new.cap64, 8
  %values.new = call ptr @malloc(i64 %value.bytes)
  %states.new = call ptr @malloc(i64 %new.cap64)
  call void @llvm.memset.p0.i64(ptr %keys.new, i8 0, i64 %key.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %values.new, i8 0, i64 %value.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %states.new, i8 0, i64 %new.cap64, i1 false)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %old.keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %old.values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %old.states = load ptr, ptr %states.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %old.cap
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %state.slot = getelementptr inbounds i8, ptr %old.states, i32 %index
  %state = load i8, ptr %state.slot
  %occupied = icmp eq i8 %state, 1
  br i1 %occupied, label %rehash, label %loop.step
rehash:
  %key.slot = getelementptr inbounds i64, ptr %old.keys, i32 %index
  %key = load i64, ptr %key.slot
  %value.slot = getelementptr inbounds i64, ptr %old.values, i32 %index
  %value = load i64, ptr %value.slot
  call void @tb_bootstrap_map_int_int_insert_rehash(ptr %keys.new, ptr %values.new, ptr %states.new, i32 %new.cap, i64 %key, i64 %value)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  call void @free(ptr %old.keys)
  call void @free(ptr %old.values)
  call void @free(ptr %old.states)
  store i32 %new.cap, ptr %cap.ptr
  store ptr %keys.new, ptr %keys.ptr
  store ptr %values.new, ptr %values.ptr
  store ptr %states.new, ptr %states.ptr
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
  %value.bytes = mul i64 %cap64, 8
  %values = call ptr @malloc(i64 %value.bytes)
  %states = call ptr @malloc(i64 %cap64)
  call void @llvm.memset.p0.i64(ptr %keys, i8 0, i64 %key.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %values, i8 0, i64 %value.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %states, i8 0, i64 %cap64, i1 false)
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  store i32 0, ptr %len.ptr
  store i32 %cap, ptr %cap.ptr
  store ptr %keys, ptr %keys.ptr
  store ptr %values, ptr %values.ptr
  store ptr %states, ptr %states.ptr
  ret ptr %map
}

define private void __MAP_SET_NAME__(ptr %map, i32 %index, i64 %key, i64 %value, i1 %is_owned) {
entry:
  call void __MAP_SET_BY_KEY_NAME__(ptr %map, i64 %key, i64 %value, i1 false)
  ret void
}

define private i32 __MAP_LENGTH_NAME__(ptr %map) {
entry:
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}

define private i64 __MAP_GET_NAME__(ptr %map, i64 %key) {
entry:
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  %hash = call i64 @tb_bootstrap_hash_int(i64 %key)
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
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  %key.value = load i64, ptr %key.slot
  %key.match = icmp eq i64 %key.value, %key
  br i1 %key.match, label %found, label %step
found:
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  %value.result = load i64, ptr %value.slot
  ret i64 %value.result
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
missing:
  ret i64 0
}

define private void __MAP_SET_BY_KEY_NAME__(ptr %map, i64 %key, i64 %value, i1 %is_owned) {
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
  call void @tb_bootstrap_map_int_int_grow(ptr %map)
  br label %probe.setup
probe.setup:
  %cap.ptr.reload = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap.reload = load i32, ptr %cap.ptr.reload
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  %hash = call i64 @tb_bootstrap_hash_int(i64 %key)
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
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  %key.value = load i64, ptr %key.slot
  %key.match = icmp eq i64 %key.value, %key
  br i1 %key.match, label %update, label %step
update:
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  store i64 %value, ptr %value.slot
  ret void
insert:
  %key.slot.insert = getelementptr inbounds i64, ptr %keys, i32 %index
  store i64 %key, ptr %key.slot.insert
  %value.slot.insert = getelementptr inbounds i64, ptr %values, i32 %index
  store i64 %value, ptr %value.slot.insert
  store i8 1, ptr %state.slot
  %len.old = load i32, ptr %len.ptr
  %len.new = add i32 %len.old, 1
  store i32 %len.new, ptr %len.ptr
  ret void
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap.reload
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
}

define private void __MAP_INCREMENT_BY_KEY_NAME__(ptr %map, i64 %key, i64 %delta) {
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
  call void @tb_bootstrap_map_int_int_grow(ptr %map)
  br label %probe.setup
probe.setup:
  %cap.ptr.reload = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap.reload = load i32, ptr %cap.ptr.reload
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  %hash = call i64 @tb_bootstrap_hash_int(i64 %key)
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
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  %key.value = load i64, ptr %key.slot
  %key.match = icmp eq i64 %key.value, %key
  br i1 %key.match, label %update, label %step
update:
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  %value.old = load i64, ptr %value.slot
  %value.new = add i64 %value.old, %delta
  store i64 %value.new, ptr %value.slot
  ret void
insert:
  %key.slot.insert = getelementptr inbounds i64, ptr %keys, i32 %index
  store i64 %key, ptr %key.slot.insert
  %value.slot.insert = getelementptr inbounds i64, ptr %values, i32 %index
  store i64 %delta, ptr %value.slot.insert
  store i8 1, ptr %state.slot
  %len.old = load i32, ptr %len.ptr
  %len.new = add i32 %len.old, 1
  store i32 %len.new, ptr %len.ptr
  ret void
step:
  %next.raw = add i32 %index, 1
  %wrap = icmp eq i32 %next.raw, %cap.reload
  %next.index = select i1 %wrap, i32 0, i32 %next.raw
  br label %probe
}

define private void __MAP_RELEASE_BY_KEY_NAME__(ptr %map, i64 %key) {
entry:
  ret void
}

define private ptr __MAP_KEYS_NAME__(ptr %map) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %result = call ptr @tb_bootstrap_string_array_new(i32 %len)
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %out = phi i32 [0, %entry], [%next.out, %loop.step]
  %keep.loop = icmp slt i32 %index, %cap
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %occupied = icmp eq i8 %state, 1
  br i1 %occupied, label %emit, label %skip
emit:
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  %key.value = load i64, ptr %key.slot
  %key.text = call ptr @tb_bootstrap_int_to_string(i64 %key.value)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 %out, ptr %key.text, i1 true)
  %out.bump = add i32 %out, 1
  br label %loop.step
skip:
  br label %loop.step
loop.step:
  %next.out = phi i32 [%out.bump, %emit], [%out, %skip]
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}

define private ptr __MAP_VALUES_NAME__(ptr %map) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %result = call ptr @tb_bootstrap_string_array_new(i32 %len)
  %cap.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %out = phi i32 [0, %entry], [%next.out, %loop.step]
  %keep.loop = icmp slt i32 %index, %cap
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %occupied = icmp eq i8 %state, 1
  br i1 %occupied, label %emit, label %skip
emit:
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  %value.raw = load i64, ptr %value.slot
  %value.text = call ptr @tb_bootstrap_int_to_string(i64 %value.raw)
  call void @tb_bootstrap_string_array_set_owned(ptr %result, i32 %out, ptr %value.text, i1 true)
  %out.bump = add i32 %out, 1
  br label %loop.step
skip:
  br label %loop.step
loop.step:
  %next.out = phi i32 [%out.bump, %emit], [%out, %skip]
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}

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
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %cap
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %state.slot = getelementptr inbounds i8, ptr %states, i32 %index
  %state = load i8, ptr %state.slot
  %occupied = icmp eq i8 %state, 1
  br i1 %occupied, label %clone.item, label %loop.step
clone.item:
  %key.slot = getelementptr inbounds i64, ptr %keys, i32 %index
  %key.value = load i64, ptr %key.slot
  %value.slot = getelementptr inbounds i64, ptr %values, i32 %index
  %value.raw = load i64, ptr %value.slot
  call void __MAP_SET_BY_KEY_NAME__(ptr %clone, i64 %key.value, i64 %value.raw, i1 false)
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
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %values = load ptr, ptr %values.ptr
  %states.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 4
  %states = load ptr, ptr %states.ptr
  call void @free(ptr %states)
  call void @free(ptr %keys)
  call void @free(ptr %values)
  call void @free(ptr %map)
  br label %done
done:
  ret void
}
