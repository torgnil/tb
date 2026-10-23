define private i64 @tb_bootstrap_checked_int_div(i64 %dividend, i64 %divisor) {
entry:
  %divisor.zero = icmp eq i64 %divisor, 0
  %dividend.minimum = icmp eq i64 %dividend, -9223372036854775808
  %divisor.negative.one = icmp eq i64 %divisor, -1
  %overflow = and i1 %dividend.minimum, %divisor.negative.one
  %invalid = or i1 %divisor.zero, %overflow
  br i1 %invalid, label %invalid.operands, label %divide
invalid.operands:
  call void @abort()
  unreachable
divide:
  %result = sdiv i64 %dividend, %divisor
  ret i64 %result
}

define private i64 @tb_bootstrap_checked_int_rem(i64 %dividend, i64 %divisor) {
entry:
  %divisor.zero = icmp eq i64 %divisor, 0
  %dividend.minimum = icmp eq i64 %dividend, -9223372036854775808
  %divisor.negative.one = icmp eq i64 %divisor, -1
  %overflow = and i1 %dividend.minimum, %divisor.negative.one
  %invalid = or i1 %divisor.zero, %overflow
  br i1 %invalid, label %invalid.operands, label %remainder
invalid.operands:
  call void @abort()
  unreachable
remainder:
  %result = srem i64 %dividend, %divisor
  ret i64 %result
}
