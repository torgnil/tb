define private ptr @tb_bootstrap_record_clone___RECORD__(ptr %record) {
entry:
  %is.null = icmp eq ptr %record, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %size.ptr = getelementptr __RECORD_TYPE__, ptr null, i32 1
  %size = ptrtoint ptr %size.ptr to i64
  %clone = call ptr @malloc(i64 %size)
__CLONE_FIELD_LINES__
  ret ptr %clone
}
define private void @tb_bootstrap_record_free___RECORD__(ptr %record) {
entry:
  %is.null = icmp eq ptr %record, null
  br i1 %is.null, label %done, label %free
free:
__FREE_FIELD_LINES__
  call void @free(ptr %record)
  br label %done
done:
  ret void
}
