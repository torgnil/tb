define private ptr @tb_bootstrap_num_to_string(%tb_bootstrap_num %num) {
entry:
  %value = extractvalue %tb_bootstrap_num %num, 0
  %scale = extractvalue %tb_bootstrap_num %num, 1
  %is.scale.zero = icmp eq i64 %scale, 0
  br i1 %is.scale.zero, label %whole, label %fractional
whole:
  %whole.only.text = call ptr @tb_bootstrap_int_to_string(i64 %value)
  ret ptr %whole.only.text
fractional:
  %is.neg = icmp slt i64 %value, 0
  %neg.value = sub i64 0, %value
  %abs.value = select i1 %is.neg, i64 %neg.value, i64 %value
  %factor = call i64 @tb_bootstrap_num_pow10(i64 %scale)
  %whole.value = udiv i64 %abs.value, %factor
  %fraction.value = urem i64 %abs.value, %factor
  %whole.text = call ptr @tb_bootstrap_int_to_string(i64 %whole.value)
  %fraction.text = call ptr @tb_bootstrap_int_to_string(i64 %fraction.value)
  %whole.len = call i64 @strlen(ptr %whole.text)
  %fraction.len = call i64 @strlen(ptr %fraction.text)
  %sign.len = select i1 %is.neg, i64 1, i64 0
  %scale.minus.fraction = sub i64 %scale, %fraction.len
  %body.len = add i64 %whole.len, 1
  %body.frac = add i64 %body.len, %scale
  %text.len = add i64 %body.frac, %sign.len
  %text.bytes = add i64 %text.len, 1
  %data = call ptr @tb_string_new(i64 %text.len)
  %start = select i1 %is.neg, i64 1, i64 0
  br i1 %is.neg, label %write.minus, label %copy.whole
write.minus:
  store i8 45, ptr %data
  br label %copy.whole
copy.whole:
  %whole.dst = getelementptr inbounds i8, ptr %data, i64 %start
  call void @llvm.memcpy.p0.p0.i64(ptr %whole.dst, ptr %whole.text, i64 %whole.len, i1 false)
  %dot.index = add i64 %start, %whole.len
  %dot.ptr = getelementptr inbounds i8, ptr %data, i64 %dot.index
  store i8 46, ptr %dot.ptr
  br label %zero.cond
zero.cond:
  %zero.index = phi i64 [0, %copy.whole], [%zero.next, %zero.body]
  %zero.keep = icmp slt i64 %zero.index, %scale.minus.fraction
  br i1 %zero.keep, label %zero.body, label %copy.fraction
zero.body:
  %zero.offset.base = add i64 %dot.index, 1
  %zero.offset = add i64 %zero.offset.base, %zero.index
  %zero.ptr = getelementptr inbounds i8, ptr %data, i64 %zero.offset
  store i8 48, ptr %zero.ptr
  %zero.next = add i64 %zero.index, 1
  br label %zero.cond
copy.fraction:
  %fraction.dst.base = add i64 %dot.index, 1
  %fraction.dst.offset = add i64 %fraction.dst.base, %scale.minus.fraction
  %fraction.dst = getelementptr inbounds i8, ptr %data, i64 %fraction.dst.offset
  call void @llvm.memcpy.p0.p0.i64(ptr %fraction.dst, ptr %fraction.text, i64 %fraction.len, i1 false)
  %term.ptr = getelementptr inbounds i8, ptr %data, i64 %text.len
  store i8 0, ptr %term.ptr
  call void @tb_release(ptr %whole.text)
  call void @tb_release(ptr %fraction.text)
  ret ptr %data
}
