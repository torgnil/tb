define private i64 @tb_bootstrap_shift_left(i64 %value, i64 %amount) {
entry:
  %is.negative = icmp slt i64 %amount, 0
  br i1 %is.negative, label %abort.neg, label %check.range
abort.neg:
  call void @abort()
  unreachable
check.range:
  %too.large = icmp sge i64 %amount, 64
  br i1 %too.large, label %return.zero, label %shift
return.zero:
  ret i64 0
shift:
  %shifted = shl i64 %value, %amount
  ret i64 %shifted
}

define private i64 @tb_bootstrap_shift_right(i64 %value, i64 %amount) {
entry:
  %is.negative = icmp slt i64 %amount, 0
  br i1 %is.negative, label %abort.neg, label %check.range
abort.neg:
  call void @abort()
  unreachable
check.range:
  %too.large = icmp sge i64 %amount, 64
  br i1 %too.large, label %saturate, label %shift
saturate:
  %value.is.negative = icmp slt i64 %value, 0
  %saturated = select i1 %value.is.negative, i64 -1, i64 0
  ret i64 %saturated
shift:
  %shifted = ashr i64 %value, %amount
  ret i64 %shifted
}
