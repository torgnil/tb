%tb_bootstrap_record_array___RECORD__ = type { i32, i32, ptr, ptr }
define private ptr @tb_bootstrap_record_array_new___RECORD__(i32 %len) {
entry:
  %array = call ptr @malloc(i64 24)
  %len64 = sext i32 %len to i64
  %has.items = icmp sgt i32 %len, 0
  %alloc.len64 = select i1 %has.items, i64 %len64, i64 1
  %bytes = mul i64 %alloc.len64, 8
  %data = call ptr @malloc(i64 %bytes)
  %owned = call ptr @malloc(i64 %alloc.len64)
  call void @llvm.memset.p0.i64(ptr %data, i8 0, i64 %bytes, i1 false)
  call void @llvm.memset.p0.i64(ptr %owned, i8 0, i64 %alloc.len64, i1 false)
  %len.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 0
  %cap.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 1
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 3
  store i32 %len, ptr %len.ptr
  %cap32 = trunc i64 %alloc.len64 to i32
  store i32 %cap32, ptr %cap.ptr
  store ptr %data, ptr %data.ptr
  store ptr %owned, ptr %owned.ptr
  ret ptr %array
}
define private void @tb_bootstrap_record_array_set_owned___RECORD__(ptr %array, i32 %index, ptr %value, i1 %is_owned) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  store ptr %value, ptr %slot
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = zext i1 %is_owned to i8
  store i8 %owned.byte, ptr %owned.slot
  ret void
}
define private ptr @tb_bootstrap_record_array_get___RECORD__(ptr %array, i32 %index) {
entry:
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %value = load ptr, ptr %slot
  ret ptr %value
}
define private void @tb_bootstrap_record_array_release_slot___RECORD__(ptr %array, i32 %index) {
entry:
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %owned.slot = getelementptr inbounds i8, ptr %owned, i32 %index
  %owned.byte = load i8, ptr %owned.slot
  %item.owned = icmp ne i8 %owned.byte, 0
  br i1 %item.owned, label %free.item, label %done
free.item:
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %item.slot = getelementptr inbounds ptr, ptr %data, i32 %index
  %item.value = load ptr, ptr %item.slot
  call void @tb_bootstrap_record_free___RECORD__(ptr %item.value)
  store ptr null, ptr %item.slot
  store i8 0, ptr %owned.slot
  br label %done
done:
  ret void
}
define private i32 @tb_bootstrap_record_array_length___RECORD__(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %null, label %read
null:
  ret i32 0
read:
  %len.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  ret i32 %len
}
define private i32 @tb_bootstrap_record_array_push___RECORD__(ptr %array, ptr %value, i1 %is_owned) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %cap.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 1
  %cap = load i32, ptr %cap.ptr
  %next.len = add i32 %len, 1
  %has.capacity = icmp slt i32 %len, %cap
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %data.old = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 3
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
define private ptr @tb_bootstrap_record_array_clone___RECORD__(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length___RECORD__(ptr %array)
  %clone = call ptr @tb_bootstrap_record_array_new___RECORD__(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.body]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %loop.done
loop.body:
  %item = call ptr @tb_bootstrap_record_array_get___RECORD__(ptr %array, i32 %index)
  %item.copy = call ptr @tb_bootstrap_record_clone___RECORD__(ptr %item)
  call void @tb_bootstrap_record_array_set_owned___RECORD__(ptr %clone, i32 %index, ptr %item.copy, i1 true)
  %next.index = add i32 %index, 1
  br label %loop.cond
loop.done:
  ret ptr %clone
}
define private void @tb_bootstrap_record_array_free___RECORD__(ptr %array) {
entry:
  %is.null = icmp eq ptr %array, null
  br i1 %is.null, label %done, label %free
free:
  %len.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array___RECORD__, ptr %array, i32 0, i32 3
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
  call void @tb_bootstrap_record_free___RECORD__(ptr %item.value)
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
