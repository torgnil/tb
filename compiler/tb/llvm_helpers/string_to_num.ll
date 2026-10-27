@.msg.to_num.invalid = private unnamed_addr constant [23 x i8] c"to_num: invalid number\00"

define private void @tb_bootstrap_to_num_failure() {
entry:
  %handler = load ptr, ptr @__tb_exception_handler
  %has.handler = icmp ne ptr %handler, null
  br i1 %has.handler, label %unwind, label %fatal
unwind:
  %message = call ptr @tb_bootstrap_string_copy(ptr @.msg.to_num.invalid)
  store ptr %message, ptr @__tb_exception_message
  call void @longjmp(ptr %handler, i32 1)
  unreachable
fatal:
  call i32 @puts(ptr @.msg.to_num.invalid)
  call void @exit(i32 1)
  unreachable
}

; Parse an ASCII decimal into a signed coefficient and fractional digit count.
; The coefficient is accumulated as an unsigned magnitude with a sign-specific
; limit, so INT64_MIN is representable without signed arithmetic overflow.
define private %tb_bootstrap_num @tb_bootstrap_to_num(ptr %src) {
entry:
  %first = load i8, ptr %src
  %negative = icmp eq i8 %first, 45
  %positive = icmp eq i8 %first, 43
  %has.sign = or i1 %negative, %positive
  %start = select i1 %has.sign, i64 1, i64 0
  br label %loop
loop:
  %index = phi i64 [ %start, %entry ], [ %next.index, %digit.next ], [ %next.dot.index, %dot.next ]
  %magnitude = phi i64 [ 0, %entry ], [ %next.magnitude, %digit.next ], [ %magnitude, %dot.next ]
  %scale = phi i64 [ 0, %entry ], [ %next.scale, %digit.next ], [ %scale, %dot.next ]
  %dot = phi i1 [ false, %entry ], [ %dot, %digit.next ], [ true, %dot.next ]
  %has.digit = phi i1 [ false, %entry ], [ true, %digit.next ], [ %has.digit, %dot.next ]
  %char.ptr = getelementptr inbounds i8, ptr %src, i64 %index
  %char = load i8, ptr %char.ptr
  %end = icmp eq i8 %char, 0
  br i1 %end, label %done, label %classify
classify:
  %is.dot = icmp eq i8 %char, 46
  br i1 %is.dot, label %dot.check, label %digit.check
dot.check:
  br i1 %dot, label %invalid, label %dot.next
dot.next:
  %next.dot.index = add i64 %index, 1
  br label %loop
digit.check:
  %digit.lower = icmp uge i8 %char, 48
  %digit.upper = icmp ule i8 %char, 57
  %is.digit = and i1 %digit.lower, %digit.upper
  br i1 %is.digit, label %overflow.check, label %invalid
overflow.check:
  %digit.byte = sub i8 %char, 48
  %digit = zext i8 %digit.byte to i64
  %too.large = icmp ugt i64 %magnitude, 922337203685477580
  %at.limit = icmp eq i64 %magnitude, 922337203685477580
  %last.limit = select i1 %negative, i64 8, i64 7
  %digit.too.large = icmp ugt i64 %digit, %last.limit
  %limit.overflow = and i1 %at.limit, %digit.too.large
  %overflow = or i1 %too.large, %limit.overflow
  br i1 %overflow, label %invalid, label %scale.check
scale.check:
  %scale.full = icmp eq i64 %scale, 2147483647
  %scale.overflow = and i1 %dot, %scale.full
  br i1 %scale.overflow, label %invalid, label %digit.next
digit.next:
  %times.ten = mul i64 %magnitude, 10
  %next.magnitude = add i64 %times.ten, %digit
  %fraction.digit = zext i1 %dot to i64
  %next.scale = add i64 %scale, %fraction.digit
  %next.index = add i64 %index, 1
  br label %loop
done:
  br i1 %has.digit, label %success, label %invalid
success:
  %minus = sub i64 0, %magnitude
  %value = select i1 %negative, i64 %minus, i64 %magnitude
  %num.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %value, 0
  %num.1 = insertvalue %tb_bootstrap_num %num.0, i64 %scale, 1
  ret %tb_bootstrap_num %num.1
invalid:
  call void @tb_bootstrap_to_num_failure()
  unreachable
}
