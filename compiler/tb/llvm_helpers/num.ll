define private %tb_bootstrap_num @tb_bootstrap_num_make(i64 %value, i64 %scale) {
entry:
  %num.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %value, 0
  %num.1 = insertvalue %tb_bootstrap_num %num.0, i64 %scale, 1
  ret %tb_bootstrap_num %num.1
}
define private i64 @tb_bootstrap_num_pow10(i64 %scale) {
entry:
  br label %loop.cond
loop.cond:
  %index = phi i64 [0, %entry], [%next.index, %loop.body]
  %value = phi i64 [1, %entry], [%next.value, %loop.body]
  %keep.loop = icmp slt i64 %index, %scale
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %next.value = mul i64 %value, 10
  %next.index = add i64 %index, 1
  br label %loop.cond
done:
  ret i64 %value
}
define private i64 @tb_bootstrap_num_rescale_value(i64 %value, i64 %from_scale, i64 %to_scale) {
entry:
  %already.scale = icmp sle i64 %to_scale, %from_scale
  br i1 %already.scale, label %done, label %scale.up
scale.up:
  %delta = sub i64 %to_scale, %from_scale
  %factor = call i64 @tb_bootstrap_num_pow10(i64 %delta)
  %scaled = mul i64 %value, %factor
  ret i64 %scaled
done:
  ret i64 %value
}
define private i64 @tb_bootstrap_num_cmp(%tb_bootstrap_num %left, %tb_bootstrap_num %right) {
entry:
  %left.value = extractvalue %tb_bootstrap_num %left, 0
  %left.scale = extractvalue %tb_bootstrap_num %left, 1
  %right.value = extractvalue %tb_bootstrap_num %right, 0
  %right.scale = extractvalue %tb_bootstrap_num %right, 1
  %left.scale.gt = icmp sgt i64 %left.scale, %right.scale
  %target.scale = select i1 %left.scale.gt, i64 %left.scale, i64 %right.scale
  %left.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %left.value, i64 %left.scale, i64 %target.scale)
  %right.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %right.value, i64 %right.scale, i64 %target.scale)
  %is.lt = icmp slt i64 %left.scaled, %right.scaled
  %is.gt = icmp sgt i64 %left.scaled, %right.scaled
  %gt.or.eq = select i1 %is.gt, i64 1, i64 0
  %result = select i1 %is.lt, i64 -1, i64 %gt.or.eq
  ret i64 %result
}
define private %tb_bootstrap_num @tb_bootstrap_num_neg(%tb_bootstrap_num %value) {
entry:
  %raw = extractvalue %tb_bootstrap_num %value, 0
  %scale = extractvalue %tb_bootstrap_num %value, 1
  %neg = sub i64 0, %raw
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %neg, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %scale, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_add(%tb_bootstrap_num %left, %tb_bootstrap_num %right) {
entry:
  %left.value = extractvalue %tb_bootstrap_num %left, 0
  %left.scale = extractvalue %tb_bootstrap_num %left, 1
  %right.value = extractvalue %tb_bootstrap_num %right, 0
  %right.scale = extractvalue %tb_bootstrap_num %right, 1
  %left.scale.gt = icmp sgt i64 %left.scale, %right.scale
  %target.scale = select i1 %left.scale.gt, i64 %left.scale, i64 %right.scale
  %left.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %left.value, i64 %left.scale, i64 %target.scale)
  %right.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %right.value, i64 %right.scale, i64 %target.scale)
  %sum = add i64 %left.scaled, %right.scaled
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %sum, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %target.scale, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_sub(%tb_bootstrap_num %left, %tb_bootstrap_num %right) {
entry:
  %left.value = extractvalue %tb_bootstrap_num %left, 0
  %left.scale = extractvalue %tb_bootstrap_num %left, 1
  %right.value = extractvalue %tb_bootstrap_num %right, 0
  %right.scale = extractvalue %tb_bootstrap_num %right, 1
  %left.scale.gt = icmp sgt i64 %left.scale, %right.scale
  %target.scale = select i1 %left.scale.gt, i64 %left.scale, i64 %right.scale
  %left.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %left.value, i64 %left.scale, i64 %target.scale)
  %right.scaled = call i64 @tb_bootstrap_num_rescale_value(i64 %right.value, i64 %right.scale, i64 %target.scale)
  %diff = sub i64 %left.scaled, %right.scaled
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %diff, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %target.scale, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_mul(%tb_bootstrap_num %left, %tb_bootstrap_num %right) {
entry:
  %left.value = extractvalue %tb_bootstrap_num %left, 0
  %left.scale = extractvalue %tb_bootstrap_num %left, 1
  %right.value = extractvalue %tb_bootstrap_num %right, 0
  %right.scale = extractvalue %tb_bootstrap_num %right, 1
  %left.scale.gt = icmp sgt i64 %left.scale, %right.scale
  %target.scale = select i1 %left.scale.gt, i64 %left.scale, i64 %right.scale
  %product.scale = add i64 %left.scale, %right.scale
  %left.ext = sext i64 %left.value to i128
  %right.ext = sext i64 %right.value to i128
  %product = mul i128 %left.ext, %right.ext
  %delta = sub i64 %product.scale, %target.scale
  %needs.round = icmp sgt i64 %delta, 0
  br i1 %needs.round, label %round, label %direct
direct:
  %direct.value = trunc i128 %product to i64
  br label %make
round:
  %factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 %delta)
  %factor = sext i64 %factor.i64 to i128
  %product.neg = icmp slt i128 %product, 0
  %product.neg.value = sub i128 0, %product
  %abs.product = select i1 %product.neg, i128 %product.neg.value, i128 %product
  %quot = udiv i128 %abs.product, %factor
  %rem = urem i128 %abs.product, %factor
  %twice.rem = mul i128 %rem, 2
  %round.up = icmp uge i128 %twice.rem, %factor
  %quot.plus = add i128 %quot, 1
  %quot.rounded = select i1 %round.up, i128 %quot.plus, i128 %quot
  %signed.neg = sub i128 0, %quot.rounded
  %signed.value = select i1 %product.neg, i128 %signed.neg, i128 %quot.rounded
  %rounded.value = trunc i128 %signed.value to i64
  br label %make
make:
  %result.value = phi i64 [%direct.value, %direct], [%rounded.value, %round]
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %result.value, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %target.scale, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_div(%tb_bootstrap_num %left, %tb_bootstrap_num %right) {
entry:
  %left.value = extractvalue %tb_bootstrap_num %left, 0
  %left.scale = extractvalue %tb_bootstrap_num %left, 1
  %right.value = extractvalue %tb_bootstrap_num %right, 0
  %right.scale = extractvalue %tb_bootstrap_num %right, 1
  %left.scale.gt = icmp sgt i64 %left.scale, %right.scale
  %target.scale = select i1 %left.scale.gt, i64 %left.scale, i64 %right.scale
  %num.scale = add i64 %right.scale, %target.scale
  %num.factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 %num.scale)
  %den.factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 %left.scale)
  %left.ext = sext i64 %left.value to i128
  %right.ext = sext i64 %right.value to i128
  %num.factor = sext i64 %num.factor.i64 to i128
  %den.factor = sext i64 %den.factor.i64 to i128
  %numerator = mul i128 %left.ext, %num.factor
  %denominator = mul i128 %right.ext, %den.factor
  %numerator.neg = icmp slt i128 %numerator, 0
  %denominator.neg = icmp slt i128 %denominator, 0
  %result.neg = xor i1 %numerator.neg, %denominator.neg
  %numerator.neg.value = sub i128 0, %numerator
  %abs.numerator = select i1 %numerator.neg, i128 %numerator.neg.value, i128 %numerator
  %denominator.neg.value = sub i128 0, %denominator
  %abs.denominator = select i1 %denominator.neg, i128 %denominator.neg.value, i128 %denominator
  %quot = udiv i128 %abs.numerator, %abs.denominator
  %rem = urem i128 %abs.numerator, %abs.denominator
  %twice.rem = mul i128 %rem, 2
  %round.up = icmp uge i128 %twice.rem, %abs.denominator
  %quot.plus = add i128 %quot, 1
  %quot.rounded = select i1 %round.up, i128 %quot.plus, i128 %quot
  %signed.neg = sub i128 0, %quot.rounded
  %signed.value = select i1 %result.neg, i128 %signed.neg, i128 %quot.rounded
  %result.value = trunc i128 %signed.value to i64
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %result.value, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %target.scale, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_round(%tb_bootstrap_num %num, i64 %places) {
entry:
  %value = extractvalue %tb_bootstrap_num %num, 0
  %scale = extractvalue %tb_bootstrap_num %num, 1
  %needs.round = icmp sgt i64 %scale, %places
  br i1 %needs.round, label %round, label %done
done:
  ret %tb_bootstrap_num %num
round:
  %delta = sub i64 %scale, %places
  %factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 %delta)
  %factor = sext i64 %factor.i64 to i128
  %value.ext = sext i64 %value to i128
  %value.neg = icmp slt i128 %value.ext, 0
  %value.neg.raw = sub i128 0, %value.ext
  %abs.value = select i1 %value.neg, i128 %value.neg.raw, i128 %value.ext
  %quot = udiv i128 %abs.value, %factor
  %rem = urem i128 %abs.value, %factor
  %twice.rem = mul i128 %rem, 2
  %round.up = icmp uge i128 %twice.rem, %factor
  %quot.plus = add i128 %quot, 1
  %quot.rounded = select i1 %round.up, i128 %quot.plus, i128 %quot
  %signed.neg = sub i128 0, %quot.rounded
  %signed.value = select i1 %value.neg, i128 %signed.neg, i128 %quot.rounded
  %rounded.value = trunc i128 %signed.value to i64
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %rounded.value, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 %places, 1
  ret %tb_bootstrap_num %result.1
}
define private %tb_bootstrap_num @tb_bootstrap_num_sqrt(%tb_bootstrap_num %num) {
entry:
  %value = extractvalue %tb_bootstrap_num %num, 0
  %scale = extractvalue %tb_bootstrap_num %num, 1
  %factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 %scale)
  %value.f64 = sitofp i64 %value to double
  %factor.f64 = sitofp i64 %factor.i64 to double
  %normalized = fdiv double %value.f64, %factor.f64
  %root = call double @llvm.sqrt.f64(double %normalized)
  %result.factor.i64 = call i64 @tb_bootstrap_num_pow10(i64 6)
  %result.factor.f64 = sitofp i64 %result.factor.i64 to double
  %scaled = fmul double %root, %result.factor.f64
  %rounded = call double @llvm.round.f64(double %scaled)
  %result.value = fptosi double %rounded to i64
  %result.0 = insertvalue %tb_bootstrap_num zeroinitializer, i64 %result.value, 0
  %result.1 = insertvalue %tb_bootstrap_num %result.0, i64 6, 1
  ret %tb_bootstrap_num %result.1
}
define private i32 @tb_bootstrap_num_print(%tb_bootstrap_num %num) {
entry:
  %value = extractvalue %tb_bootstrap_num %num, 0
  %scale = extractvalue %tb_bootstrap_num %num, 1
  %is.scale.zero = icmp eq i64 %scale, 0
  br i1 %is.scale.zero, label %whole, label %fractional
whole:
  %whole.result = call i32 (ptr, ...) @printf(ptr @.fmt.int, i64 %value)
  ret i32 %whole.result
fractional:
  %is.neg = icmp slt i64 %value, 0
  %neg.value = sub i64 0, %value
  %abs.value = select i1 %is.neg, i64 %neg.value, i64 %value
  %factor = call i64 @tb_bootstrap_num_pow10(i64 %scale)
  %whole.value = udiv i64 %abs.value, %factor
  %fraction.value = urem i64 %abs.value, %factor
  %minus.ptr = getelementptr inbounds [2 x i8], ptr @.num.minus, i32 0, i32 0
  %empty.ptr = getelementptr inbounds [1 x i8], ptr @.num.empty, i32 0, i32 0
  %sign.ptr = select i1 %is.neg, ptr %minus.ptr, ptr %empty.ptr
  %scale.i32 = trunc i64 %scale to i32
  %result = call i32 (ptr, ...) @printf(ptr @.fmt.num.frac, ptr %sign.ptr, i64 %whole.value, i32 %scale.i32, i64 %fraction.value)
  ret i32 %result
}
