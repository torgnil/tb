define private ptr @tb_bootstrap_int_array_map_add(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = add i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_sub(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = sub i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_mul(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = mul i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_div(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = sdiv i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_int_array_map_mod(ptr %array, i64 %rhs) {
entry:
  %len = call i32 @tb_bootstrap_int_array_length(ptr %array)
  %result = call ptr @tb_bootstrap_int_array_new(i32 %len)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %value = call i64 @tb_bootstrap_int_array_get(ptr %array, i32 %index)
  %mapped = srem i64 %value, %rhs
  call void @tb_bootstrap_int_array_set(ptr %result, i32 %index, i64 %mapped)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %result
}
