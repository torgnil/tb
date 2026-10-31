define private i32 @tb_checked_array_index(i64 %index, i32 %length) {
entry:
  %length64 = sext i32 %length to i64
  %is.negative = icmp slt i64 %index, 0
  %adjusted = add i64 %length64, %index
  %normalized = select i1 %is.negative, i64 %adjusted, i64 %index
  %nonnegative = icmp sge i64 %normalized, 0
  %below.length = icmp slt i64 %normalized, %length64
  %in.range = and i1 %nonnegative, %below.length
  br i1 %in.range, label %valid, label %invalid
invalid:
  call void @abort()
  unreachable
valid:
  %index32 = trunc i64 %normalized to i32
  ret i32 %index32
}

define private i32 @tb_nested_array_write_index(i64 %index, i32 %length) {
entry:
  %length64 = sext i32 %length to i64
  %is.negative = icmp slt i64 %index, 0
  %adjusted = add i64 %length64, %index
  %normalized = select i1 %is.negative, i64 %adjusted, i64 %index
  %nonnegative = icmp sge i64 %normalized, 0
  %fits_length = icmp slt i64 %normalized, 2147483647
  %valid = and i1 %nonnegative, %fits_length
  br i1 %valid, label %valid.index, label %invalid
invalid:
  call void @abort()
  unreachable
valid.index:
  %index32 = trunc i64 %normalized to i32
  ret i32 %index32
}
