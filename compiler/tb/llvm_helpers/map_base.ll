define private ptr __MAP_NEW_NAME__(i32 %len) {
entry:
  %size.ptr = getelementptr __MAP_STRUCT__, ptr null, i32 1
  %size = ptrtoint ptr %size.ptr to i64
  %map = call ptr @malloc(i64 %size)
  %len64 = sext i32 %len to i64
  %key.bytes = mul i64 %len64, 8
  %keys = call ptr @malloc(i64 %key.bytes)
  %values.end = getelementptr __VALUE_LLVM_TYPE__, ptr null, i32 %len
  %value.bytes = ptrtoint ptr %values.end to i64
  %values = call ptr @malloc(i64 %value.bytes)
  %owned = call ptr @malloc(i64 %len64)
  call void @llvm.memset.p0.i64(ptr %keys, i8 0, i64 %key.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %values, i8 0, i64 %value.bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %len64, i1 false)
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  store i32 %len, ptr %len.ptr
  store ptr %keys, ptr %keys.ptr
  store ptr %values, ptr %values.ptr
  store ptr %owned, ptr %owned.ptr
  ret ptr %map
}

define private void __MAP_SET_NAME__(ptr %map, i32 %index, __KEY_LLVM_TYPE__ %key, __VALUE_LLVM_TYPE__ %value, i1 %is_owned) {
entry:
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  store __KEY_LLVM_TYPE__ %key, ptr %key.slot
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  store __VALUE_LLVM_TYPE__ %value, ptr %value.slot
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
}

define private i32 __MAP_LENGTH_NAME__(ptr %map) {
entry:
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}

define private __VALUE_LLVM_TYPE__ __MAP_GET_NAME__(ptr %map, __KEY_LLVM_TYPE__ %key) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %missing
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  %key.value = load __KEY_LLVM_TYPE__, ptr %key.slot
__KEY_COMPARE_GET__
  br i1 %key.match, label %found, label %loop.step
found:
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  %value.result = load __VALUE_LLVM_TYPE__, ptr %value.slot
  ret __VALUE_LLVM_TYPE__ %value.result
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
missing:
  ret __VALUE_LLVM_TYPE__ __ZERO_VALUE__
}

define private void __MAP_SET_BY_KEY_NAME__(ptr %map, __KEY_LLVM_TYPE__ %key, __VALUE_LLVM_TYPE__ %value, i1 %is_owned) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %insert
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  %key.value = load __KEY_LLVM_TYPE__, ptr %key.slot
__KEY_COMPARE_SET_BY_KEY__
  br i1 %key.match, label %found, label %loop.step
found:
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  store __VALUE_LLVM_TYPE__ %value, ptr %value.slot
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  br label %done
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret void
insert:
  %next.len = add i32 %len, 1
  %next.len64 = sext i32 %next.len to i64
  %key.bytes = mul i64 %next.len64, 8
  %keys.new = call ptr @malloc(i64 %key.bytes)
  %values.end = getelementptr __VALUE_LLVM_TYPE__, ptr null, i32 %next.len
  %value.bytes = ptrtoint ptr %values.end to i64
  %values.new = call ptr @malloc(i64 %value.bytes)
  %owned.new = call ptr @malloc(i64 %next.len64)
  %has.items = icmp sgt i32 %len, 0
  br i1 %has.items, label %copy.old, label %store.new
copy.old:
  %len64 = sext i32 %len to i64
  %old.key.bytes = mul i64 %len64, 8
  %old.values.end = getelementptr __VALUE_LLVM_TYPE__, ptr null, i32 %len
  %old.value.bytes = ptrtoint ptr %old.values.end to i64
  call void @llvm.memcpy.p0.p0.i64(ptr %keys.new, ptr %keys, i64 %old.key.bytes, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr %values.new, ptr %values, i64 %old.value.bytes, i1 false)
  call void @llvm.memcpy.p0.p0.i64(ptr %owned.new, ptr %owned, i64 %len64, i1 false)
  br label %store.new
store.new:
  %new.key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys.new, i32 %len
__INSERT_KEY_BLOCK__
  %new.value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values.new, i32 %len
  store __VALUE_LLVM_TYPE__ %value, ptr %new.value.slot
  %new.owned.slot = getelementptr inbounds i8, ptr %owned.new, i32 %len
  %new.owned.byte = zext i1 %is_owned to i8
  store i8 %new.owned.byte, ptr %new.owned.slot
  call void @free(ptr %keys)
  call void @free(ptr %values)
  call void @free(ptr %owned)
  store ptr %keys.new, ptr %keys.ptr
  store ptr %values.new, ptr %values.ptr
  store ptr %owned.new, ptr %owned.ptr
  %len.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 0
  store i32 %next.len, ptr %len.ptr
  ret void
}

define private void __MAP_RELEASE_BY_KEY_NAME__(ptr %map, __KEY_LLVM_TYPE__ %key) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  %key.value = load __KEY_LLVM_TYPE__, ptr %key.slot
__KEY_COMPARE_RELEASE_BY_KEY__
  br i1 %key.match, label %found, label %loop.step
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
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret void
}

define private ptr __MAP_KEYS_NAME__(ptr %map) {
entry:
  %len = call i32 __MAP_LENGTH_NAME__(ptr %map)
  %result = call ptr @tb_bootstrap_string_array_new(i32 %len)
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  %key.value = load __KEY_LLVM_TYPE__, ptr %key.slot
__KEYS_RESULT_BLOCK__
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
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %copy], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
  %key.value = load __KEY_LLVM_TYPE__, ptr %key.slot
__CLONE_KEY_COPY_BLOCK__
  %value.slot = getelementptr inbounds __VALUE_LLVM_TYPE__, ptr %values, i32 %index
  %value.raw = load __VALUE_LLVM_TYPE__, ptr %value.slot
__CLONE_VALUE_COPY_BLOCK__
  call void __MAP_SET_NAME__(ptr %clone, i32 %index, __KEY_LLVM_TYPE__ %key.copy, __VALUE_LLVM_TYPE__ __CLONE_STORED_VALUE__, i1 __CLONE_STORED_OWNED__)
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
  %keys.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 1
  %keys = load ptr, ptr %keys.ptr
  %values.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 2
  %values = load ptr, ptr %values.ptr
  %owned.ptr = getelementptr inbounds __MAP_STRUCT__, ptr %map, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %free], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %loop.done
loop.body:
  %key.slot = getelementptr inbounds __KEY_LLVM_TYPE__, ptr %keys, i32 %index
__FREE_KEY_BLOCK__
__FREE_VALUE_BLOCK__
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
loop.done:
  call void @free(ptr %owned)
  call void @free(ptr %keys)
  call void @free(ptr %values)
  call void @free(ptr %map)
  br label %done
done:
  ret void
}
