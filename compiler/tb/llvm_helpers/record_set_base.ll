define private ptr @tb_bootstrap_record_set_new___RECORD__() {
entry:
  %set = call ptr @tb_bootstrap_record_array_new___RECORD__(i32 0)
  ret ptr %set
}
define private i32 @tb_bootstrap_record_set_length___RECORD__(ptr %set) {
entry:
  %len = call i32 @tb_bootstrap_record_array_length___RECORD__(ptr %set)
  ret i32 %len
}
define private ptr @tb_bootstrap_record_set_get___RECORD__(ptr %set, i32 %index) {
entry:
  %value = call ptr @tb_bootstrap_record_array_get___RECORD__(ptr %set, i32 %index)
  ret ptr %value
}
define private i1 @tb_bootstrap_record_set_contains___RECORD__(ptr %set, ptr %value) {
entry:
  %len = call i32 @tb_bootstrap_record_set_length___RECORD__(ptr %set)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %missing
loop.body:
  %item = call ptr @tb_bootstrap_record_set_get___RECORD__(ptr %set, i32 %index)
__CONTAINS_FIELD_LINES__
__CONTAINS_DECISION_LINES__
found:
  ret i1 true
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
missing:
  ret i1 false
}
define private i32 @tb_bootstrap_record_set_add___RECORD__(ptr %set, ptr %value, i1 %is_owned) {
entry:
  %exists = call i1 @tb_bootstrap_record_set_contains___RECORD__(ptr %set, ptr %value)
  br i1 %exists, label %existing, label %missing
existing:
  br i1 %is_owned, label %free.value, label %return.len
free.value:
  call void @tb_bootstrap_record_free___RECORD__(ptr %value)
  br label %return.len
return.len:
  %len.existing = call i32 @tb_bootstrap_record_set_length___RECORD__(ptr %set)
  ret i32 %len.existing
missing:
  %len = call i32 @tb_bootstrap_record_array_push___RECORD__(ptr %set, ptr %value, i1 %is_owned)
  ret i32 %len
}
define private ptr @tb_bootstrap_record_set_clone___RECORD__(ptr %set) {
entry:
  %clone = call ptr @tb_bootstrap_record_array_clone___RECORD__(ptr %set)
  ret ptr %clone
}
define private void @tb_bootstrap_record_set_free___RECORD__(ptr %set) {
entry:
  call void @tb_bootstrap_record_array_free___RECORD__(ptr %set)
  ret void
}
