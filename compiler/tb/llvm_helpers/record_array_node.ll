define private i32 @tb_bootstrap_cmp_record_pair_Node_by_value(ptr %left.pair.ptr, ptr %right.pair.ptr) {
entry:
  %left.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %left.pair.ptr, i32 0, i32 0
  %left.item = load ptr, ptr %left.item.ptr
  %right.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %right.pair.ptr, i32 0, i32 0
  %right.item = load ptr, ptr %right.item.ptr
  %left.value.ptr = getelementptr inbounds %tb_bootstrap_record_Node, ptr %left.item, i32 0, i32 1
  %left.value = load i64, ptr %left.value.ptr
  %right.value.ptr = getelementptr inbounds %tb_bootstrap_record_Node, ptr %right.item, i32 0, i32 1
  %right.value = load i64, ptr %right.value.ptr
  %left.gt = icmp sgt i64 %left.value, %right.value
  br i1 %left.gt, label %ret.neg, label %check.lt
check.lt:
  %left.lt = icmp slt i64 %left.value, %right.value
  br i1 %left.lt, label %ret.pos, label %ret.zero
ret.neg:
  ret i32 -1
ret.pos:
  ret i32 1
ret.zero:
  ret i32 0
}
define private ptr @tb_bootstrap_create_prio_q_Node_desc_by_value(ptr %array) {
entry:
  %clone = call ptr @tb_bootstrap_record_array_clone_Node(ptr %array)
  %sorted = call ptr @tb_bootstrap_record_array_sort_Node_by_value(ptr %clone)
  ret ptr %sorted
}
define private i1 @tb_bootstrap_prio_q_Node_is_empty(ptr %pq) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length_Node(ptr %pq)
  %empty = icmp eq i32 %len, 0
  ret i1 %empty
}
define private i32 @tb_bootstrap_prio_q_Node_push_by_value(ptr %pq, ptr %value, i1 %is_owned) {
entry:
  %len = call i32 @tb_bootstrap_record_array_push_Node(ptr %pq, ptr %value, i1 %is_owned)
  %sorted = call ptr @tb_bootstrap_record_array_sort_Node_by_value(ptr %pq)
  ret i32 %len
}
define private ptr @tb_bootstrap_prio_q_Node_pop(ptr %pq) {
entry:
  %len.ptr = getelementptr inbounds %tb_bootstrap_record_array_Node, ptr %pq, i32 0, i32 0
  %len = load i32, ptr %len.ptr
  %is.empty = icmp eq i32 %len, 0
  br i1 %is.empty, label %empty, label %pop
empty:
  ret ptr null
pop:
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array_Node, ptr %pq, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array_Node, ptr %pq, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %first.slot = getelementptr inbounds ptr, ptr %data, i32 0
  %value = load ptr, ptr %first.slot
  %last.index = sub i32 %len, 1
  %has.tail = icmp sgt i32 %last.index, 0
  br i1 %has.tail, label %loop.cond, label %shrink
loop.cond:
  %current = phi i32 [0, %pop], [%next.current, %loop.body]
  %keep.loop = icmp slt i32 %current, %last.index
  br i1 %keep.loop, label %loop.body, label %shrink
loop.body:
  %src = add i32 %current, 1
  %src.slot = getelementptr inbounds ptr, ptr %data, i32 %src
  %src.value = load ptr, ptr %src.slot
  %dst.slot = getelementptr inbounds ptr, ptr %data, i32 %current
  store ptr %src.value, ptr %dst.slot
  %src.owned.slot = getelementptr inbounds i8, ptr %owned, i32 %src
  %src.owned = load i8, ptr %src.owned.slot
  %dst.owned.slot = getelementptr inbounds i8, ptr %owned, i32 %current
  store i8 %src.owned, ptr %dst.owned.slot
  %next.current = add i32 %current, 1
  br label %loop.cond
shrink:
  store i32 %last.index, ptr %len.ptr
  %last.slot = getelementptr inbounds ptr, ptr %data, i32 %last.index
  store ptr null, ptr %last.slot
  %last.owned.slot = getelementptr inbounds i8, ptr %owned, i32 %last.index
  store i8 0, ptr %last.owned.slot
  ret ptr %value
}
define private ptr @tb_bootstrap_record_array_sort_Node_by_value(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length_Node(ptr %array)
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array_Node, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array_Node, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %len64 = sext i32 %len to i64
  %pair.size.ptr = getelementptr { ptr, i8 }, ptr null, i32 1
  %pair.size = ptrtoint ptr %pair.size.ptr to i64
  %pairs.bytes = mul i64 %len64, %pair.size
  %pairs = call ptr @malloc(i64 %pairs.bytes)
  br label %copy.cond.node
copy.cond.node:
  %copy.i.node = phi i32 [0, %entry], [%copy.next.i.node, %copy.step.node]
  %copy.keep.node = icmp slt i32 %copy.i.node, %len
  br i1 %copy.keep.node, label %copy.body.node, label %copy.done.node
copy.body.node:
  %pair.slot.node = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %copy.i.node
  %pair.item.ptr.node = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.node, i32 0, i32 0
  %data.slot.node = getelementptr inbounds ptr, ptr %data, i32 %copy.i.node
  %item.node = load ptr, ptr %data.slot.node
  store ptr %item.node, ptr %pair.item.ptr.node
  %pair.owned.ptr.node = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.node, i32 0, i32 1
  %owned.slot.node = getelementptr inbounds i8, ptr %owned, i32 %copy.i.node
  %owned.value.node = load i8, ptr %owned.slot.node
  store i8 %owned.value.node, ptr %pair.owned.ptr.node
  br label %copy.step.node
copy.step.node:
  %copy.next.i.node = add i32 %copy.i.node, 1
  br label %copy.cond.node
copy.done.node:
  call void @qsort(ptr %pairs, i64 %len64, i64 %pair.size, ptr @tb_bootstrap_cmp_record_pair_Node_by_value)
  br label %write.cond.node
write.cond.node:
  %write.i.node = phi i32 [0, %copy.done.node], [%write.next.i.node, %write.step.node]
  %write.keep.node = icmp slt i32 %write.i.node, %len
  br i1 %write.keep.node, label %write.body.node, label %done.sort
write.body.node:
  %write.pair.slot.node = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %write.i.node
  %write.item.ptr.node = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.node, i32 0, i32 0
  %write.item.node = load ptr, ptr %write.item.ptr.node
  %write.data.slot.node = getelementptr inbounds ptr, ptr %data, i32 %write.i.node
  store ptr %write.item.node, ptr %write.data.slot.node
  %write.owned.ptr.node = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.node, i32 0, i32 1
  %write.owned.node = load i8, ptr %write.owned.ptr.node
  %write.owned.slot.node = getelementptr inbounds i8, ptr %owned, i32 %write.i.node
  store i8 %write.owned.node, ptr %write.owned.slot.node
  br label %write.step.node
write.step.node:
  %write.next.i.node = add i32 %write.i.node, 1
  br label %write.cond.node
done.sort:
  call void @free(ptr %pairs)
  ret ptr %array
}
