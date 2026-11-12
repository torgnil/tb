define private i64 __MAP_KEY_HASH_NAME__(ptr %value) {
entry:
  %outer.len32 = call i32 @tb_bootstrap_int_array_array_length(ptr %value)
  %outer.len = sext i32 %outer.len32 to i64
  %seed.raw = mul i64 5381, 33
  %seed = add i64 %seed.raw, %outer.len
  br label %outer.cond
outer.cond:
  %outer.index = phi i32 [0, %entry], [%next.outer.index, %outer.step]
  %outer.hash = phi i64 [%seed, %entry], [%next.outer.hash, %outer.step]
  %outer.done = icmp sge i32 %outer.index, %outer.len32
  br i1 %outer.done, label %exit, label %outer.body
outer.body:
  %row = call ptr @tb_bootstrap_int_array_array_get(ptr %value, i32 %outer.index)
  %row.null = icmp eq ptr %row, null
  br i1 %row.null, label %null.row, label %present.row
null.row:
  %null.hash.raw = mul i64 %outer.hash, 33
  %null.hash = add i64 %null.hash.raw, -1
  br label %outer.step
present.row:
  %row.len32 = call i32 @tb_bootstrap_int_array_length(ptr %row)
  %row.len = sext i32 %row.len32 to i64
  %row.hash.raw = mul i64 %outer.hash, 33
  %row.hash = add i64 %row.hash.raw, %row.len
  br label %inner.cond
inner.cond:
  %inner.index = phi i32 [0, %present.row], [%next.inner.index, %inner.body]
  %inner.hash = phi i64 [%row.hash, %present.row], [%next.inner.hash, %inner.body]
  %inner.done = icmp sge i32 %inner.index, %row.len32
  br i1 %inner.done, label %outer.step, label %inner.body
inner.body:
  %item = call i64 @tb_bootstrap_int_array_get(ptr %row, i32 %inner.index)
  %item.hash.raw = mul i64 %inner.hash, 33
  %next.inner.hash = add i64 %item.hash.raw, %item
  %next.inner.index = add i32 %inner.index, 1
  br label %inner.cond
outer.step:
  %next.outer.hash = phi i64 [%null.hash, %null.row], [%inner.hash, %inner.cond]
  %next.outer.index = add i32 %outer.index, 1
  br label %outer.cond
exit:
  ret i64 %outer.hash
}

define private i1 __MAP_KEY_EQUALS_NAME__(ptr %left, ptr %right) {
entry:
  %left.len = call i32 @tb_bootstrap_int_array_array_length(ptr %left)
  %right.len = call i32 @tb_bootstrap_int_array_array_length(ptr %right)
  %outer.match = icmp eq i32 %left.len, %right.len
  br i1 %outer.match, label %outer.cond, label %false
outer.cond:
  %outer.index = phi i32 [0, %entry], [%next.outer.index, %outer.step]
  %outer.done = icmp sge i32 %outer.index, %left.len
  br i1 %outer.done, label %true, label %outer.body
outer.body:
  %left.row = call ptr @tb_bootstrap_int_array_array_get(ptr %left, i32 %outer.index)
  %right.row = call ptr @tb_bootstrap_int_array_array_get(ptr %right, i32 %outer.index)
  %left.null = icmp eq ptr %left.row, null
  %right.null = icmp eq ptr %right.row, null
  %both.null = and i1 %left.null, %right.null
  br i1 %both.null, label %outer.step, label %check.row.null
check.row.null:
  %one.null = xor i1 %left.null, %right.null
  br i1 %one.null, label %false, label %check.row.length
check.row.length:
  %left.row.len = call i32 @tb_bootstrap_int_array_length(ptr %left.row)
  %right.row.len = call i32 @tb_bootstrap_int_array_length(ptr %right.row)
  %row.len.match = icmp eq i32 %left.row.len, %right.row.len
  br i1 %row.len.match, label %inner.cond, label %false
inner.cond:
  %inner.index = phi i32 [0, %check.row.length], [%next.inner.index, %inner.step]
  %inner.done = icmp sge i32 %inner.index, %left.row.len
  br i1 %inner.done, label %outer.step, label %inner.body
inner.body:
  %left.item = call i64 @tb_bootstrap_int_array_get(ptr %left.row, i32 %inner.index)
  %right.item = call i64 @tb_bootstrap_int_array_get(ptr %right.row, i32 %inner.index)
  %item.match = icmp eq i64 %left.item, %right.item
  br i1 %item.match, label %inner.step, label %false
inner.step:
  %next.inner.index = add i32 %inner.index, 1
  br label %inner.cond
outer.step:
  %next.outer.index = add i32 %outer.index, 1
  br label %outer.cond
true:
  ret i1 true
false:
  ret i1 false
}
