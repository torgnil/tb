define private i32 @tb_bootstrap_cmp_record_pair_Edge_compare_edges(ptr %left.pair.ptr, ptr %right.pair.ptr) {
entry:
  %left.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %left.pair.ptr, i32 0, i32 0
  %left.item = load ptr, ptr %left.item.ptr
  %right.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %right.pair.ptr, i32 0, i32 0
  %right.item = load ptr, ptr %right.item.ptr
  %left.dist.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %left.item, i32 0, i32 0
  %left.dist = load i64, ptr %left.dist.ptr
  %right.dist.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %right.item, i32 0, i32 0
  %right.dist = load i64, ptr %right.dist.ptr
  %dist.lt = icmp slt i64 %left.dist, %right.dist
  br i1 %dist.lt, label %ret.neg, label %dist.gt.check
dist.gt.check:
  %dist.gt = icmp sgt i64 %left.dist, %right.dist
  br i1 %dist.gt, label %ret.pos, label %compare.a
compare.a:
  %left.a.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %left.item, i32 0, i32 1
  %left.a = load i64, ptr %left.a.ptr
  %right.a.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %right.item, i32 0, i32 1
  %right.a = load i64, ptr %right.a.ptr
  %a.lt = icmp slt i64 %left.a, %right.a
  br i1 %a.lt, label %ret.neg, label %a.gt.check
a.gt.check:
  %a.gt = icmp sgt i64 %left.a, %right.a
  br i1 %a.gt, label %ret.pos, label %compare.b
compare.b:
  %left.b.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %left.item, i32 0, i32 2
  %left.b = load i64, ptr %left.b.ptr
  %right.b.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %right.item, i32 0, i32 2
  %right.b = load i64, ptr %right.b.ptr
  %b.lt = icmp slt i64 %left.b, %right.b
  br i1 %b.lt, label %ret.neg, label %b.gt.check
b.gt.check:
  %b.gt = icmp sgt i64 %left.b, %right.b
  br i1 %b.gt, label %ret.pos, label %ret.zero
ret.neg:
  ret i32 -1
ret.pos:
  ret i32 1
ret.zero:
  ret i32 0
}
define private ptr @tb_bootstrap_record_array_sort_Edge_compare_edges(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length_Edge(ptr %array)
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array_Edge, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array_Edge, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %len64 = sext i32 %len to i64
  %pair.size.ptr = getelementptr { ptr, i8 }, ptr null, i32 1
  %pair.size = ptrtoint ptr %pair.size.ptr to i64
  %pairs.bytes = mul i64 %len64, %pair.size
  %pairs = call ptr @malloc(i64 %pairs.bytes)
  br label %copy.cond.named
copy.cond.named:
  %copy.i.named = phi i32 [0, %entry], [%copy.next.i.named, %copy.step.named]
  %copy.keep.named = icmp slt i32 %copy.i.named, %len
  br i1 %copy.keep.named, label %copy.body.named, label %copy.done.named
copy.body.named:
  %pair.slot.named = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %copy.i.named
  %pair.item.ptr.named = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.named, i32 0, i32 0
  %data.slot.named = getelementptr inbounds ptr, ptr %data, i32 %copy.i.named
  %item.named = load ptr, ptr %data.slot.named
  store ptr %item.named, ptr %pair.item.ptr.named
  %pair.owned.ptr.named = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.named, i32 0, i32 1
  %owned.slot.named = getelementptr inbounds i8, ptr %owned, i32 %copy.i.named
  %owned.value.named = load i8, ptr %owned.slot.named
  store i8 %owned.value.named, ptr %pair.owned.ptr.named
  br label %copy.step.named
copy.step.named:
  %copy.next.i.named = add i32 %copy.i.named, 1
  br label %copy.cond.named
copy.done.named:
  call void @qsort(ptr %pairs, i64 %len64, i64 %pair.size, ptr @tb_bootstrap_cmp_record_pair_Edge_compare_edges)
  br label %write.cond.named
write.cond.named:
  %write.i.named = phi i32 [0, %copy.done.named], [%write.next.i.named, %write.step.named]
  %write.keep.named = icmp slt i32 %write.i.named, %len
  br i1 %write.keep.named, label %write.body.named, label %done.sort.named
write.body.named:
  %write.pair.slot.named = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %write.i.named
  %write.item.ptr.named = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.named, i32 0, i32 0
  %write.item.named = load ptr, ptr %write.item.ptr.named
  %write.data.slot.named = getelementptr inbounds ptr, ptr %data, i32 %write.i.named
  store ptr %write.item.named, ptr %write.data.slot.named
  %write.owned.ptr.named = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.named, i32 0, i32 1
  %write.owned.named = load i8, ptr %write.owned.ptr.named
  %write.owned.slot.named = getelementptr inbounds i8, ptr %owned, i32 %write.i.named
  store i8 %write.owned.named, ptr %write.owned.slot.named
  br label %write.step.named
write.step.named:
  %write.next.i.named = add i32 %write.i.named, 1
  br label %write.cond.named
done.sort.named:
  call void @free(ptr %pairs)
  ret ptr %array
}
define private i32 @tb_bootstrap_cmp_record_pair_Edge_by_distance(ptr %left.pair.ptr, ptr %right.pair.ptr) {
entry:
  %left.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %left.pair.ptr, i32 0, i32 0
  %left.item = load ptr, ptr %left.item.ptr
  %right.item.ptr = getelementptr inbounds { ptr, i8 }, ptr %right.pair.ptr, i32 0, i32 0
  %right.item = load ptr, ptr %right.item.ptr
  %left.dist.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %left.item, i32 0, i32 2
  %left.dist = load i64, ptr %left.dist.ptr
  %right.dist.ptr = getelementptr inbounds %tb_bootstrap_record_Edge, ptr %right.item, i32 0, i32 2
  %right.dist = load i64, ptr %right.dist.ptr
  %left.gt = icmp sgt i64 %left.dist, %right.dist
  br i1 %left.gt, label %ret.pos, label %check.lt
check.lt:
  %left.lt = icmp slt i64 %left.dist, %right.dist
  br i1 %left.lt, label %ret.neg, label %ret.zero
ret.neg:
  ret i32 -1
ret.pos:
  ret i32 1
ret.zero:
  ret i32 0
}
define private ptr @tb_bootstrap_record_array_sort_Edge_by_distance(ptr %array) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length_Edge(ptr %array)
  %data.ptr = getelementptr inbounds %tb_bootstrap_record_array_Edge, ptr %array, i32 0, i32 2
  %data = load ptr, ptr %data.ptr
  %owned.ptr = getelementptr inbounds %tb_bootstrap_record_array_Edge, ptr %array, i32 0, i32 3
  %owned = load ptr, ptr %owned.ptr
  %len64 = sext i32 %len to i64
  %pair.size.ptr = getelementptr { ptr, i8 }, ptr null, i32 1
  %pair.size = ptrtoint ptr %pair.size.ptr to i64
  %pairs.bytes = mul i64 %len64, %pair.size
  %pairs = call ptr @malloc(i64 %pairs.bytes)
  br label %copy.cond.dist
copy.cond.dist:
  %copy.i.dist = phi i32 [0, %entry], [%copy.next.i.dist, %copy.step.dist]
  %copy.keep.dist = icmp slt i32 %copy.i.dist, %len
  br i1 %copy.keep.dist, label %copy.body.dist, label %copy.done.dist
copy.body.dist:
  %pair.slot.dist = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %copy.i.dist
  %pair.item.ptr.dist = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.dist, i32 0, i32 0
  %data.slot.dist = getelementptr inbounds ptr, ptr %data, i32 %copy.i.dist
  %item.dist = load ptr, ptr %data.slot.dist
  store ptr %item.dist, ptr %pair.item.ptr.dist
  %pair.owned.ptr.dist = getelementptr inbounds { ptr, i8 }, ptr %pair.slot.dist, i32 0, i32 1
  %owned.slot.dist = getelementptr inbounds i8, ptr %owned, i32 %copy.i.dist
  %owned.value.dist = load i8, ptr %owned.slot.dist
  store i8 %owned.value.dist, ptr %pair.owned.ptr.dist
  br label %copy.step.dist
copy.step.dist:
  %copy.next.i.dist = add i32 %copy.i.dist, 1
  br label %copy.cond.dist
copy.done.dist:
  call void @qsort(ptr %pairs, i64 %len64, i64 %pair.size, ptr @tb_bootstrap_cmp_record_pair_Edge_by_distance)
  br label %write.cond.dist
write.cond.dist:
  %write.i.dist = phi i32 [0, %copy.done.dist], [%write.next.i.dist, %write.step.dist]
  %write.keep.dist = icmp slt i32 %write.i.dist, %len
  br i1 %write.keep.dist, label %write.body.dist, label %done.sort
write.body.dist:
  %write.pair.slot.dist = getelementptr inbounds { ptr, i8 }, ptr %pairs, i32 %write.i.dist
  %write.item.ptr.dist = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.dist, i32 0, i32 0
  %write.item.dist = load ptr, ptr %write.item.ptr.dist
  %write.data.slot.dist = getelementptr inbounds ptr, ptr %data, i32 %write.i.dist
  store ptr %write.item.dist, ptr %write.data.slot.dist
  %write.owned.ptr.dist = getelementptr inbounds { ptr, i8 }, ptr %write.pair.slot.dist, i32 0, i32 1
  %write.owned.dist = load i8, ptr %write.owned.ptr.dist
  %write.owned.slot.dist = getelementptr inbounds i8, ptr %owned, i32 %write.i.dist
  store i8 %write.owned.dist, ptr %write.owned.slot.dist
  br label %write.step.dist
write.step.dist:
  %write.next.i.dist = add i32 %write.i.dist, 1
  br label %write.cond.dist
done.sort:
  call void @free(ptr %pairs)
  ret ptr %array
}
