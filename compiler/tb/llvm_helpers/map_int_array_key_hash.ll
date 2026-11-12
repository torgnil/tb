define private i64 __MAP_KEY_HASH_NAME__(ptr %value) {
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

define private i1 __MAP_KEY_EQUALS_NAME__(ptr %left, ptr %right) {
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
