define private ptr @tb_bootstrap_args_from_argv(i32 %argc, ptr %argv) {
entry:
  %has.args = icmp sgt i32 %argc, 0
  br i1 %has.args, label %with.args, label %empty
empty:
  %empty.array = call ptr @tb_bootstrap_string_array_new(i32 0)
  ret ptr %empty.array
with.args:
  %array = call ptr @tb_bootstrap_string_array_new(i32 %argc)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %with.args], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %argc
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %argv.slot = getelementptr inbounds ptr, ptr %argv, i32 %index
  %arg.value = load ptr, ptr %argv.slot
  %arg.copy = call ptr @tb_bootstrap_string_copy(ptr %arg.value)
  call void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %index, ptr %arg.copy, i1 true)
  br label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
done:
  ret ptr %array
}
