define private ptr @tb_bootstrap_string_set_new() {
entry:
  %set = call ptr @tb_bootstrap_string_array_new(i32 0)
  ret ptr %set
}
define private i32 @tb_bootstrap_string_set_length(ptr %set) {
entry:
  %length = call i32 @tb_bootstrap_string_array_length(ptr %set)
  ret i32 %length
}
define private ptr @tb_bootstrap_string_set_get(ptr %set, i32 %index) {
entry:
  %value = call ptr @tb_bootstrap_string_array_get(ptr %set, i32 %index)
  ret ptr %value
}
define private i1 @tb_bootstrap_string_set_contains(ptr %set, ptr %value) {
entry:
  %contains = call i1 @tb_bootstrap_string_array_contains(ptr %set, ptr %value)
  ret i1 %contains
}
define private i32 @tb_bootstrap_string_set_add(ptr %set, ptr %value, i1 %is_owned) {
entry:
  %contains = call i1 @tb_bootstrap_string_set_contains(ptr %set, ptr %value)
  br i1 %contains, label %duplicate, label %insert
duplicate:
  br i1 %is_owned, label %release.duplicate, label %return.length
release.duplicate:
  call void @tb_release(ptr %value)
  br label %return.length
return.length:
  %duplicate.length = call i32 @tb_bootstrap_string_set_length(ptr %set)
  ret i32 %duplicate.length
insert:
  br i1 %is_owned, label %transfer, label %copy
transfer:
  br label %store
copy:
  %copied.value = call ptr @tb_bootstrap_string_copy(ptr %value)
  br label %store
store:
  %stored.value = phi ptr [ %value, %transfer ], [ %copied.value, %copy ]
  %length = call i32 @tb_bootstrap_string_array_push(ptr %set, ptr %stored.value, i1 true)
  ret i32 %length
}
define private i1 @tb_bootstrap_string_set_remove(ptr %set, ptr %value) {
entry:
  %index = call i64 @tb_bootstrap_string_array_index_of(ptr %set, ptr %value)
  %present = icmp sge i64 %index, 0
  br i1 %present, label %remove, label %missing
remove:
  %removed.value = call ptr @tb_bootstrap_string_array_remove_at(ptr %set, i64 %index)
  call void @tb_release(ptr %removed.value)
  ret i1 true
missing:
  ret i1 false
}
define private ptr @tb_bootstrap_string_set_clone(ptr %set) {
entry:
  %clone = call ptr @tb_bootstrap_string_array_clone(ptr %set)
  ret ptr %clone
}
define private void @tb_bootstrap_string_set_free(ptr %set) {
entry:
  call void @tb_bootstrap_string_array_free(ptr %set)
  ret void
}
define private ptr @tb_bootstrap_string_set_union(ptr %left, ptr %right) {
entry:
  %result = call ptr @tb_bootstrap_string_set_new()
  %left.length = call i32 @tb_bootstrap_string_set_length(ptr %left)
  br label %left.condition
left.condition:
  %left.index = phi i32 [0, %entry], [%left.next, %left.body]
  %left.more = icmp slt i32 %left.index, %left.length
  br i1 %left.more, label %left.body, label %right.start
left.body:
  %left.value = call ptr @tb_bootstrap_string_set_get(ptr %left, i32 %left.index)
  %left.ignored = call i32 @tb_bootstrap_string_set_add(ptr %result, ptr %left.value, i1 false)
  %left.next = add i32 %left.index, 1
  br label %left.condition
right.start:
  %right.length = call i32 @tb_bootstrap_string_set_length(ptr %right)
  br label %right.condition
right.condition:
  %right.index = phi i32 [0, %right.start], [%right.next, %right.body]
  %right.more = icmp slt i32 %right.index, %right.length
  br i1 %right.more, label %right.body, label %done
right.body:
  %right.value = call ptr @tb_bootstrap_string_set_get(ptr %right, i32 %right.index)
  %right.ignored = call i32 @tb_bootstrap_string_set_add(ptr %result, ptr %right.value, i1 false)
  %right.next = add i32 %right.index, 1
  br label %right.condition
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_string_set_intersection(ptr %left, ptr %right) {
entry:
  %result = call ptr @tb_bootstrap_string_set_new()
  %left.length = call i32 @tb_bootstrap_string_set_length(ptr %left)
  br label %condition
condition:
  %index = phi i32 [0, %entry], [%next, %step]
  %more = icmp slt i32 %index, %left.length
  br i1 %more, label %body, label %done
body:
  %value = call ptr @tb_bootstrap_string_set_get(ptr %left, i32 %index)
  %present = call i1 @tb_bootstrap_string_set_contains(ptr %right, ptr %value)
  br i1 %present, label %add.value, label %step
add.value:
  %ignored = call i32 @tb_bootstrap_string_set_add(ptr %result, ptr %value, i1 false)
  br label %step
step:
  %next = add i32 %index, 1
  br label %condition
done:
  ret ptr %result
}
define private ptr @tb_bootstrap_string_set_difference(ptr %left, ptr %right) {
entry:
  %result = call ptr @tb_bootstrap_string_set_new()
  %left.length = call i32 @tb_bootstrap_string_set_length(ptr %left)
  br label %condition
condition:
  %index = phi i32 [0, %entry], [%next, %step]
  %more = icmp slt i32 %index, %left.length
  br i1 %more, label %body, label %done
body:
  %value = call ptr @tb_bootstrap_string_set_get(ptr %left, i32 %index)
  %present = call i1 @tb_bootstrap_string_set_contains(ptr %right, ptr %value)
  br i1 %present, label %step, label %add.value
add.value:
  %ignored = call i32 @tb_bootstrap_string_set_add(ptr %result, ptr %value, i1 false)
  br label %step
step:
  %next = add i32 %index, 1
  br label %condition
done:
  ret ptr %result
}
