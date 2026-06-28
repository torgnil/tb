%tb_bootstrap_rc_header = type { i64, i64, i64 }
@tb_rt_sc = internal global i64 0
@tb_rt_sb = internal global i64 0
@tb_rt_xc = internal global i64 0
@tb_rt_xb = internal global i64 0
@tb_rt_ic = internal global i64 0
@tb_rt_ib = internal global i64 0
@tb_char_cache = internal global [256 x ptr] zeroinitializer

define private ptr @tb_retain(ptr %value) {
entry:
  %is.null = icmp eq ptr %value, null
  br i1 %is.null, label %done, label %retain
retain:
  %header = getelementptr inbounds i8, ptr %value, i64 -24
  %magic.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 0
  %magic = load i64, ptr %magic.ptr
  %is.managed = icmp eq i64 %magic, 6071506869271343153
  br i1 %is.managed, label %retain.managed, label %done
retain.managed:
  %refcount.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 1
  %refcount = load i64, ptr %refcount.ptr
  %next.refcount = add i64 %refcount, 1
  store i64 %next.refcount, ptr %refcount.ptr
  br label %done
done:
  ret ptr %value
}
define private void @tb_release(ptr %value) {
entry:
  %is.null = icmp eq ptr %value, null
  br i1 %is.null, label %done, label %release
release:
  %header = getelementptr inbounds i8, ptr %value, i64 -24
  %magic.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 0
  %magic = load i64, ptr %magic.ptr
  %is.managed = icmp eq i64 %magic, 6071506869271343153
  br i1 %is.managed, label %release.managed, label %done
release.managed:
  %refcount.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 1
  %refcount = load i64, ptr %refcount.ptr
  %next.refcount = sub i64 %refcount, 1
  store i64 %next.refcount, ptr %refcount.ptr
  %is.zero = icmp eq i64 %next.refcount, 0
  br i1 %is.zero, label %destroy, label %done
destroy:
  call void @free(ptr %header)
  br label %done
done:
  ret void
}
define private ptr @tb_string_new(i64 %length) {
entry:
  %total.size = add i64 %length, 25
  %allocation = call ptr @malloc(i64 %total.size)
  %magic.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %allocation, i32 0, i32 0
  %refcount.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %allocation, i32 0, i32 1
  %length.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %allocation, i32 0, i32 2
  store i64 6071506869271343153, ptr %magic.ptr
  store i64 1, ptr %refcount.ptr
  store i64 %length, ptr %length.ptr
  %payload = getelementptr inbounds i8, ptr %allocation, i64 24
  %terminator = getelementptr inbounds i8, ptr %payload, i64 %length
  store i8 0, ptr %terminator
  ret ptr %payload
}
define private i64 @tb_managed_string_length(ptr %src) {
entry:
  %is.null = icmp eq ptr %src, null
  br i1 %is.null, label %empty, label %read
empty:
  ret i64 0
read:
  %header = getelementptr inbounds i8, ptr %src, i64 -24
  %length.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 2
  %length = load i64, ptr %length.ptr
  ret i64 %length
}
define private i8 @tb_managed_string_byte_at_or_zero(ptr %src, i64 %index) {
entry:
  %is.null = icmp eq ptr %src, null
  br i1 %is.null, label %empty, label %read
empty:
  ret i8 0
read:
  %len = call i64 @tb_managed_string_length(ptr %src)
  %index.negative = icmp slt i64 %index, 0
  %index.from.end = add i64 %len, %index
  %index.effective = select i1 %index.negative, i64 %index.from.end, i64 %index
  %in.bounds.low = icmp sge i64 %index.effective, 0
  %in.bounds.high = icmp slt i64 %index.effective, %len
  %in.bounds = and i1 %in.bounds.low, %in.bounds.high
  br i1 %in.bounds, label %load, label %empty
load:
  %ch.ptr = getelementptr inbounds i8, ptr %src, i64 %index.effective
  %ch = load i8, ptr %ch.ptr
  ret i8 %ch
}
define private ptr @tb_managed_string_char_at(ptr %src, i64 %index) {
entry:
  %ch = call i8 @tb_managed_string_byte_at_or_zero(ptr %src, i64 %index)
  %is.empty = icmp eq i8 %ch, 0
  br i1 %is.empty, label %empty, label %copy
empty:
  %empty.data = call ptr @tb_string_new(i64 0)
  ret ptr %empty.data
copy:
  %data = call ptr @tb_bootstrap_cached_char(i8 %ch)
  ret ptr %data
}
define private ptr @tb_string_clone(ptr %source) {
entry:
  %is.null = icmp eq ptr %source, null
  br i1 %is.null, label %null, label %copy
null:
  ret ptr null
copy:
  %length = call i64 @strlen(ptr %source)
  %buffer = call ptr @tb_string_clone_len(ptr %source, i64 %length)
  ret ptr %buffer
}
define private ptr @tb_string_clone_len(ptr %source, i64 %length) {
entry:
  %buffer = call ptr @tb_string_new(i64 %length)
  call void @llvm.memcpy.p0.p0.i64(ptr %buffer, ptr %source, i64 %length, i1 false)
  %terminator = getelementptr inbounds i8, ptr %buffer, i64 %length
  store i8 0, ptr %terminator
  ret ptr %buffer
}
define private i1 @tb_bootstrap_is_space(i8 %ch) {
entry:
  %is.space = icmp eq i8 %ch, 32
  %is.tab = icmp eq i8 %ch, 9
  %is.nl = icmp eq i8 %ch, 10
  %is.cr = icmp eq i8 %ch, 13
  %space.or.tab = or i1 %is.space, %is.tab
  %nl.or.cr = or i1 %is.nl, %is.cr
  %result = or i1 %space.or.tab, %nl.or.cr
  ret i1 %result
}
define private ptr @tb_bootstrap_string_copy(ptr %src) {
entry:
  %len = call i64 @strlen(ptr %src)
  %bytes = add i64 %len, 1
  %sc.old = load i64, ptr @tb_rt_sc
  %sc.new = add i64 %sc.old, 1
  store i64 %sc.new, ptr @tb_rt_sc
  %sb.old = load i64, ptr @tb_rt_sb
  %sb.new = add i64 %sb.old, %bytes
  store i64 %sb.new, ptr @tb_rt_sb
  %data = call ptr @tb_string_clone(ptr %src)
  ret ptr %data
}
define private ptr @tb_bootstrap_cached_char(i8 %ch) {
entry:
  %index = zext i8 %ch to i64
  %slot = getelementptr inbounds [256 x ptr], ptr @tb_char_cache, i32 0, i64 %index
  %cached = load ptr, ptr %slot
  %has.cached = icmp ne ptr %cached, null
  br i1 %has.cached, label %reuse, label %create
reuse:
  %retained = call ptr @tb_retain(ptr %cached)
  ret ptr %retained
create:
  %data = call ptr @tb_string_new(i64 1)
  store i8 %ch, ptr %data
  %term = getelementptr inbounds i8, ptr %data, i64 1
  store i8 0, ptr %term
  %cache.ref = call ptr @tb_retain(ptr %data)
  store ptr %data, ptr %slot
  ret ptr %data
}
define private i8 @tb_bootstrap_string_byte_at_or_zero(ptr %src, i64 %index) {
entry:
  %len = call i64 @strlen(ptr %src)
  %index.negative = icmp slt i64 %index, 0
  %index.from.end = add i64 %len, %index
  %index.effective = select i1 %index.negative, i64 %index.from.end, i64 %index
  %in.bounds.low = icmp sge i64 %index.effective, 0
  %in.bounds.high = icmp slt i64 %index.effective, %len
  %in.bounds = and i1 %in.bounds.low, %in.bounds.high
  br i1 %in.bounds, label %load, label %empty
empty:
  ret i8 0
load:
  %ch.ptr = getelementptr inbounds i8, ptr %src, i64 %index.effective
  %ch = load i8, ptr %ch.ptr
  ret i8 %ch
}
define private ptr @tb_bootstrap_string_char_at(ptr %src, i64 %index) {
entry:
  %ch = call i8 @tb_bootstrap_string_byte_at_or_zero(ptr %src, i64 %index)
  %is.empty = icmp eq i8 %ch, 0
  br i1 %is.empty, label %empty, label %copy
empty:
  %empty.data = call ptr @tb_string_new(i64 0)
  ret ptr %empty.data
copy:
  %data = call ptr @tb_bootstrap_cached_char(i8 %ch)
  ret ptr %data
}
define private i1 @tb_bootstrap_string_is_alpha(ptr %src) {
entry:
  %ch = load i8, ptr %src
  %is.empty = icmp eq i8 %ch, 0
  br i1 %is.empty, label %false, label %len.check
len.check:
  %next.ptr = getelementptr inbounds i8, ptr %src, i64 1
  %next = load i8, ptr %next.ptr
  %len.ok = icmp eq i8 %next, 0
  br i1 %len.ok, label %check, label %false
check:
  %lower.lo = icmp sge i8 %ch, 97
  %lower.hi = icmp sle i8 %ch, 122
  %is.lower = and i1 %lower.lo, %lower.hi
  %upper.lo = icmp sge i8 %ch, 65
  %upper.hi = icmp sle i8 %ch, 90
  %is.upper = and i1 %upper.lo, %upper.hi
  %result = or i1 %is.lower, %is.upper
  ret i1 %result
false:
  ret i1 false
}
define private i1 @tb_bootstrap_string_is_digit(ptr %src) {
entry:
  %ch = load i8, ptr %src
  %is.empty = icmp eq i8 %ch, 0
  br i1 %is.empty, label %false, label %len.check
len.check:
  %next.ptr = getelementptr inbounds i8, ptr %src, i64 1
  %next = load i8, ptr %next.ptr
  %len.ok = icmp eq i8 %next, 0
  br i1 %len.ok, label %check, label %false
check:
  %digit.lo = icmp sge i8 %ch, 48
  %digit.hi = icmp sle i8 %ch, 57
  %result = and i1 %digit.lo, %digit.hi
  ret i1 %result
false:
  ret i1 false
}
define private i1 @tb_bootstrap_string_is_space(ptr %src) {
entry:
  %ch = load i8, ptr %src
  %is.empty = icmp eq i8 %ch, 0
  br i1 %is.empty, label %false, label %len.check
len.check:
  %next.ptr = getelementptr inbounds i8, ptr %src, i64 1
  %next = load i8, ptr %next.ptr
  %len.ok = icmp eq i8 %next, 0
  br i1 %len.ok, label %check, label %false
check:
  %result = call i1 @tb_bootstrap_is_space(i8 %ch)
  ret i1 %result
false:
  ret i1 false
}
define private i1 @tb_bootstrap_starts_with_at(ptr %src, ptr %prefix, i64 %start) {
entry:
  %src.len = call i64 @strlen(ptr %src)
  %prefix.len = call i64 @strlen(ptr %prefix)
  %start.nonneg = icmp sge i64 %start, 0
  %remaining = sub i64 %src.len, %start
  %fits = icmp sge i64 %remaining, %prefix.len
  %can.match = and i1 %start.nonneg, %fits
  br i1 %can.match, label %loop.cond, label %false
loop.cond:
  %index = phi i64 [0, %entry], [%next.index, %loop.step]
  %done = icmp eq i64 %index, %prefix.len
  br i1 %done, label %true, label %loop.body
loop.body:
  %src.offset = add i64 %start, %index
  %src.ptr = getelementptr inbounds i8, ptr %src, i64 %src.offset
  %src.ch = load i8, ptr %src.ptr
  %prefix.ptr = getelementptr inbounds i8, ptr %prefix, i64 %index
  %prefix.ch = load i8, ptr %prefix.ptr
  %same = icmp eq i8 %src.ch, %prefix.ch
  br i1 %same, label %loop.step, label %false
loop.step:
  %next.index = add i64 %index, 1
  br label %loop.cond
true:
  ret i1 true
false:
  ret i1 false
}
define private i1 @tb_bootstrap_starts_with(ptr %src, ptr %prefix) {
entry:
  %result = call i1 @tb_bootstrap_starts_with_at(ptr %src, ptr %prefix, i64 0)
  ret i1 %result
}
define private i1 @tb_bootstrap_ends_with(ptr %src, ptr %suffix) {
entry:
  %src.len = call i64 @strlen(ptr %src)
  %suffix.len = call i64 @strlen(ptr %suffix)
  %fits = icmp sge i64 %src.len, %suffix.len
  br i1 %fits, label %check, label %false
check:
  %start = sub i64 %src.len, %suffix.len
  %result = call i1 @tb_bootstrap_starts_with_at(ptr %src, ptr %suffix, i64 %start)
  ret i1 %result
false:
  ret i1 false
}
define private ptr @tb_bootstrap_substring_start(ptr %src, i64 %start) {
entry:
  %len = call i64 @strlen(ptr %src)
  %start.negative = icmp slt i64 %start, 0
  %start.from.end = add i64 %len, %start
  %start.adjusted = select i1 %start.negative, i64 %start.from.end, i64 %start
  %start.before.zero = icmp slt i64 %start.adjusted, 0
  %start.clamped.low = select i1 %start.before.zero, i64 0, i64 %start.adjusted
  %start.past.end = icmp sgt i64 %start.clamped.low, %len
  %start.clamped = select i1 %start.past.end, i64 %len, i64 %start.clamped.low
  %start.ptr = getelementptr inbounds i8, ptr %src, i64 %start.clamped
  %copy.len = sub i64 %len, %start.clamped
  %copy.value = call ptr @tb_string_clone_len(ptr %start.ptr, i64 %copy.len)
  ret ptr %copy.value
}
define private ptr @tb_bootstrap_substring_range(ptr %src, i64 %start, i64 %end) {
entry:
  %len = call i64 @strlen(ptr %src)
  %start.negative = icmp slt i64 %start, 0
  %start.from.end = add i64 %len, %start
  %start.adjusted = select i1 %start.negative, i64 %start.from.end, i64 %start
  %start.before.zero = icmp slt i64 %start.adjusted, 0
  %start.clamped.low = select i1 %start.before.zero, i64 0, i64 %start.adjusted
  %start.past.end = icmp sgt i64 %start.clamped.low, %len
  %start.clamped = select i1 %start.past.end, i64 %len, i64 %start.clamped.low
  %end.negative = icmp slt i64 %end, 0
  %end.from.end = add i64 %len, %end
  %end.adjusted = select i1 %end.negative, i64 %end.from.end, i64 %end
  %end.before.zero = icmp slt i64 %end.adjusted, 0
  %end.clamped.low = select i1 %end.before.zero, i64 0, i64 %end.adjusted
  %end.past.end = icmp sgt i64 %end.clamped.low, %len
  %end.clamped.high = select i1 %end.past.end, i64 %len, i64 %end.clamped.low
  %end.before.start = icmp slt i64 %end.clamped.high, %start.clamped
  %end.clamped = select i1 %end.before.start, i64 %start.clamped, i64 %end.clamped.high
  %slice.len = sub i64 %end.clamped, %start.clamped
  %slice.bytes = add i64 %slice.len, 1
  %data = call ptr @tb_string_new(i64 %slice.len)
  %src.ptr = getelementptr inbounds i8, ptr %src, i64 %start.clamped
  call void @llvm.memcpy.p0.p0.i64(ptr %data, ptr %src.ptr, i64 %slice.len, i1 false)
  %term = getelementptr inbounds i8, ptr %data, i64 %slice.len
  store i8 0, ptr %term
  ret ptr %data
}
define private i64 @tb_bootstrap_string_index_of(ptr %haystack, ptr %needle) {
entry:
  %needle.len = call i64 @strlen(ptr %needle)
  %is.empty = icmp eq i64 %needle.len, 0
  br i1 %is.empty, label %empty, label %setup
empty:
  ret i64 0
setup:
  %haystack.len = call i64 @strlen(ptr %haystack)
  %needle.longer = icmp sgt i64 %needle.len, %haystack.len
  br i1 %needle.longer, label %notfound, label %loop.cond
loop.cond:
  %index = phi i64 [0, %setup], [%next.index, %loop.step]
  %remaining = sub i64 %haystack.len, %index
  %can.match = icmp sge i64 %remaining, %needle.len
  br i1 %can.match, label %loop.body, label %notfound
loop.body:
  br label %cmp.cond
cmp.cond:
  %cmp.index = phi i64 [0, %loop.body], [%cmp.next, %cmp.step]
  %cmp.done = icmp eq i64 %cmp.index, %needle.len
  br i1 %cmp.done, label %found, label %cmp.body
cmp.body:
  %haystack.offset = add i64 %index, %cmp.index
  %haystack.ptr = getelementptr inbounds i8, ptr %haystack, i64 %haystack.offset
  %haystack.ch = load i8, ptr %haystack.ptr
  %needle.ptr = getelementptr inbounds i8, ptr %needle, i64 %cmp.index
  %needle.ch = load i8, ptr %needle.ptr
  %chars.match = icmp eq i8 %haystack.ch, %needle.ch
  br i1 %chars.match, label %cmp.step, label %loop.step
cmp.step:
  %cmp.next = add i64 %cmp.index, 1
  br label %cmp.cond
loop.step:
  %next.index = add i64 %index, 1
  br label %loop.cond
found:
  br label %count.cond
count.cond:
  %char.index = phi i64 [0, %found], [%next.char.index, %count.step]
  %byte.index = phi i64 [0, %found], [%next.byte.index, %count.step]
  %done.count = icmp eq i64 %byte.index, %index
  br i1 %done.count, label %count.done, label %count.body
count.body:
  %byte.ptr = getelementptr inbounds i8, ptr %haystack, i64 %byte.index
  %byte.value = load i8, ptr %byte.ptr
  %is.cont.mask = and i8 %byte.value, -64
  %is.cont = icmp eq i8 %is.cont.mask, -128
  %next.char.bump = add i64 %char.index, 1
  %next.char.index = select i1 %is.cont, i64 %char.index, i64 %next.char.bump
  %next.byte.index = add i64 %byte.index, 1
  br label %count.step
count.step:
  br label %count.cond
count.done:
  ret i64 %char.index
notfound:
  ret i64 -1
}
define private i64 @tb_bootstrap_string_index_of_char(ptr %haystack, i8 %needle) {
entry:
  br label %loop.cond
loop.cond:
  %char.index = phi i64 [0, %entry], [%next.char.index, %loop.step]
  %byte.index = phi i64 [0, %entry], [%next.byte.index, %loop.step]
  %byte.ptr = getelementptr inbounds i8, ptr %haystack, i64 %byte.index
  %byte.value = load i8, ptr %byte.ptr
  %is.end = icmp eq i8 %byte.value, 0
  br i1 %is.end, label %notfound, label %loop.body
loop.body:
  %is.match = icmp eq i8 %byte.value, %needle
  br i1 %is.match, label %found, label %loop.step
loop.step:
  %is.cont.mask = and i8 %byte.value, -64
  %is.cont = icmp eq i8 %is.cont.mask, -128
  %next.char.bump = add i64 %char.index, 1
  %next.char.index = select i1 %is.cont, i64 %char.index, i64 %next.char.bump
  %next.byte.index = add i64 %byte.index, 1
  br label %loop.cond
found:
  ret i64 %char.index
notfound:
  ret i64 -1
}
define private ptr @tb_bootstrap_trim_left(ptr %src) {
entry:
  %len = call i64 @strlen(ptr %src)
  br label %loop.cond
loop.cond:
  %index = phi i64 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i64 %index, %len
  br i1 %keep.loop, label %loop.body, label %done
loop.body:
  %ch.ptr = getelementptr inbounds i8, ptr %src, i64 %index
  %ch = load i8, ptr %ch.ptr
  %is.space = call i1 @tb_bootstrap_is_space(i8 %ch)
  br i1 %is.space, label %loop.step, label %copy
loop.step:
  %next.index = add i64 %index, 1
  br label %loop.cond
copy:
  %start.ptr = getelementptr inbounds i8, ptr %src, i64 %index
  %copy.len = sub i64 %len, %index
  %copy.value = call ptr @tb_string_clone_len(ptr %start.ptr, i64 %copy.len)
  ret ptr %copy.value
done:
  %end.ptr = getelementptr inbounds i8, ptr %src, i64 %len
  %empty.copy = call ptr @tb_string_clone_len(ptr %end.ptr, i64 0)
  ret ptr %empty.copy
}
define private ptr @tb_bootstrap_trim_right(ptr %src) {
entry:
  %len = call i64 @strlen(ptr %src)
  %is.empty = icmp eq i64 %len, 0
  br i1 %is.empty, label %empty, label %loop.start
empty:
  %empty.copy = call ptr @tb_string_clone_len(ptr %src, i64 0)
  ret ptr %empty.copy
loop.start:
  %last = sub i64 %len, 1
  br label %loop.cond
loop.cond:
  %index = phi i64 [%last, %loop.start], [%next.index, %loop.step]
  %ch.ptr = getelementptr inbounds i8, ptr %src, i64 %index
  %ch = load i8, ptr %ch.ptr
  %is.space = call i1 @tb_bootstrap_is_space(i8 %ch)
  br i1 %is.space, label %loop.check, label %copy
loop.check:
  %at.start = icmp eq i64 %index, 0
  br i1 %at.start, label %all.space, label %loop.step
loop.step:
  %next.index = sub i64 %index, 1
  br label %loop.cond
all.space:
  %data.empty = call ptr @tb_string_new(i64 0)
  ret ptr %data.empty
copy:
  %copy.len = add i64 %index, 1
  %copy.bytes = add i64 %copy.len, 1
  %data = call ptr @tb_string_new(i64 %copy.len)
  call void @llvm.memcpy.p0.p0.i64(ptr %data, ptr %src, i64 %copy.len, i1 false)
  %term = getelementptr inbounds i8, ptr %data, i64 %copy.len
  store i8 0, ptr %term
  ret ptr %data
}
define private ptr @tb_bootstrap_trim(ptr %src) {
entry:
  %left = call ptr @tb_bootstrap_trim_left(ptr %src)
  %right = call ptr @tb_bootstrap_trim_right(ptr %left)
  call void @tb_release(ptr %left)
  ret ptr %right
}
define private ptr @tb_bootstrap_string_replace(ptr %src, ptr %old, ptr %new) {
entry:
  %old.len = call i64 @strlen(ptr %old)
  %src.len.pre = call i64 @strlen(ptr %src)
  %old.empty = icmp eq i64 %old.len, 0
  br i1 %old.empty, label %copy.src, label %setup
copy.src:
  %src.copy = call ptr @tb_string_clone_len(ptr %src, i64 %src.len.pre)
  ret ptr %src.copy
setup:
  %src.len = add i64 %src.len.pre, 0
  %new.len = call i64 @strlen(ptr %new)
  br label %count.cond
count.cond:
  %count.index = phi i64 [0, %setup], [%count.next.index, %count.body]
  %count.out = phi i64 [0, %setup], [%count.next.out, %count.body]
  %count.done = icmp sge i64 %count.index, %src.len
  br i1 %count.done, label %alloc, label %count.body
count.body:
  %count.match = call i1 @tb_bootstrap_starts_with_at(ptr %src, ptr %old, i64 %count.index)
  %count.next.out.match = add i64 %count.out, %new.len
  %count.next.out.char = add i64 %count.out, 1
  %count.next.out = select i1 %count.match, i64 %count.next.out.match, i64 %count.next.out.char
  %count.next.index.match = add i64 %count.index, %old.len
  %count.next.index.char = add i64 %count.index, 1
  %count.next.index = select i1 %count.match, i64 %count.next.index.match, i64 %count.next.index.char
  br label %count.cond
alloc:
  %bytes = add i64 %count.out, 1
  %data = call ptr @tb_string_new(i64 %count.out)
  br label %write.cond
write.cond:
  %write.src.index = phi i64 [0, %alloc], [%write.next.src.index, %write.step]
  %write.out.index = phi i64 [0, %alloc], [%write.next.out.index, %write.step]
  %write.done = icmp sge i64 %write.src.index, %src.len
  br i1 %write.done, label %finish, label %write.body
write.body:
  %write.match = call i1 @tb_bootstrap_starts_with_at(ptr %src, ptr %old, i64 %write.src.index)
  br i1 %write.match, label %write.match.body, label %write.char.body
write.match.body:
  %write.dst.match = getelementptr inbounds i8, ptr %data, i64 %write.out.index
  call void @llvm.memcpy.p0.p0.i64(ptr %write.dst.match, ptr %new, i64 %new.len, i1 false)
  %write.match.next.src = add i64 %write.src.index, %old.len
  %write.match.next.out = add i64 %write.out.index, %new.len
  br label %write.step
write.char.body:
  %write.src.ptr = getelementptr inbounds i8, ptr %src, i64 %write.src.index
  %write.ch = load i8, ptr %write.src.ptr
  %write.dst.char = getelementptr inbounds i8, ptr %data, i64 %write.out.index
  store i8 %write.ch, ptr %write.dst.char
  %write.char.next.src = add i64 %write.src.index, 1
  %write.char.next.out = add i64 %write.out.index, 1
  br label %write.step
write.step:
  %write.next.src.index = phi i64 [%write.match.next.src, %write.match.body], [%write.char.next.src, %write.char.body]
  %write.next.out.index = phi i64 [%write.match.next.out, %write.match.body], [%write.char.next.out, %write.char.body]
  br label %write.cond
finish:
  %term = getelementptr inbounds i8, ptr %data, i64 %count.out
  store i8 0, ptr %term
  ret ptr %data
}
define private ptr @tb_bootstrap_string_concat(ptr %left, ptr %right) {
entry:
  %left.len = call i64 @strlen(ptr %left)
  %right.len = call i64 @strlen(ptr %right)
  %total.len = add i64 %left.len, %right.len
  %total.bytes = add i64 %total.len, 1
  %xc.old = load i64, ptr @tb_rt_xc
  %xc.new = add i64 %xc.old, 1
  store i64 %xc.new, ptr @tb_rt_xc
  %xb.old = load i64, ptr @tb_rt_xb
  %xb.new = add i64 %xb.old, %total.bytes
  store i64 %xb.new, ptr @tb_rt_xb
  %data = call ptr @tb_string_new(i64 %total.len)
  call void @llvm.memcpy.p0.p0.i64(ptr %data, ptr %left, i64 %left.len, i1 false)
  %right.dst = getelementptr inbounds i8, ptr %data, i64 %left.len
  call void @llvm.memcpy.p0.p0.i64(ptr %right.dst, ptr %right, i64 %right.len, i1 false)
  %term = getelementptr inbounds i8, ptr %data, i64 %total.len
  store i8 0, ptr %term
  ret ptr %data
}
define private ptr @tb_bootstrap_string_append_consume(ptr %left, ptr %right) {
entry:
  %left.len = call i64 @tb_managed_string_length(ptr %left)
  %right.len = call i64 @strlen(ptr %right)
  %total.len = add i64 %left.len, %right.len
  %total.bytes = add i64 %total.len, 1
  %xc.old = load i64, ptr @tb_rt_xc
  %xc.new = add i64 %xc.old, 1
  store i64 %xc.new, ptr @tb_rt_xc
  %xb.old = load i64, ptr @tb_rt_xb
  %xb.new = add i64 %xb.old, %total.bytes
  store i64 %xb.new, ptr @tb_rt_xb
  %header = getelementptr inbounds i8, ptr %left, i64 -24
  %refcount.ptr = getelementptr inbounds %tb_bootstrap_rc_header, ptr %header, i32 0, i32 1
  %refcount = load i64, ptr %refcount.ptr
  %is.unique = icmp eq i64 %refcount, 1
  br i1 %is.unique, label %reuse, label %copy
reuse:
  %total.size = add i64 %total.len, 25
  %realloced = call ptr @realloc(ptr %header, i64 %total.size)
  %data.reuse = getelementptr inbounds i8, ptr %realloced, i64 24
  %length.ptr.reuse = getelementptr inbounds %tb_bootstrap_rc_header, ptr %realloced, i32 0, i32 2
  store i64 %total.len, ptr %length.ptr.reuse
  %right.dst.reuse = getelementptr inbounds i8, ptr %data.reuse, i64 %left.len
  call void @llvm.memcpy.p0.p0.i64(ptr %right.dst.reuse, ptr %right, i64 %right.len, i1 false)
  %term.reuse = getelementptr inbounds i8, ptr %data.reuse, i64 %total.len
  store i8 0, ptr %term.reuse
  ret ptr %data.reuse
copy:
  %data = call ptr @tb_string_new(i64 %total.len)
  call void @llvm.memcpy.p0.p0.i64(ptr %data, ptr %left, i64 %left.len, i1 false)
  %right.dst = getelementptr inbounds i8, ptr %data, i64 %left.len
  call void @llvm.memcpy.p0.p0.i64(ptr %right.dst, ptr %right, i64 %right.len, i1 false)
  %term = getelementptr inbounds i8, ptr %data, i64 %total.len
  store i8 0, ptr %term
  call void @tb_release(ptr %left)
  ret ptr %data
}
define private i64 @tb_bootstrap_to_int(ptr %src) {
entry:
  %value = call i64 @strtoll(ptr %src, ptr null, i32 10)
  ret i64 %value
}
define private ptr @tb_bootstrap_int_to_string(i64 %value) {
entry:
  %len.i32 = call i32 (ptr, i64, ptr, ...) @snprintf(ptr null, i64 0, ptr @.fmt.int.text, i64 %value)
  %len = sext i32 %len.i32 to i64
  %bytes = add i64 %len, 1
  %ic.old = load i64, ptr @tb_rt_ic
  %ic.new = add i64 %ic.old, 1
  store i64 %ic.new, ptr @tb_rt_ic
  %ib.old = load i64, ptr @tb_rt_ib
  %ib.new = add i64 %ib.old, %bytes
  store i64 %ib.new, ptr @tb_rt_ib
  %data = call ptr @tb_string_new(i64 %len)
  %written = call i32 (ptr, i64, ptr, ...) @snprintf(ptr %data, i64 %bytes, ptr @.fmt.int.text, i64 %value)
  ret ptr %data
}
define private i1 @tb_bootstrap_has_flag(ptr %args, ptr %flag) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %args)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %missing
loop.body:
  %arg = call ptr @tb_bootstrap_string_array_get(ptr %args, i32 %index)
  %cmp = call i32 @strcmp(ptr %arg, ptr %flag)
  %matches = icmp eq i32 %cmp, 0
  br i1 %matches, label %found, label %loop.step
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
found:
  ret i1 true
missing:
  ret i1 false
}
define private ptr @tb_bootstrap_option_value(ptr %args, ptr %option) {
entry:
  %len = call i32 @tb_bootstrap_string_array_length(ptr %args)
  %option.len = call i64 @strlen(ptr %option)
  br label %loop.cond
loop.cond:
  %index = phi i32 [0, %entry], [%next.index, %loop.step]
  %keep.loop = icmp slt i32 %index, %len
  br i1 %keep.loop, label %loop.body, label %missing
loop.body:
  %arg = call ptr @tb_bootstrap_string_array_get(ptr %args, i32 %index)
  %cmp = call i32 @strcmp(ptr %arg, ptr %option)
  %exact = icmp eq i32 %cmp, 0
  br i1 %exact, label %exact.match, label %check.inline
exact.match:
  %value.index = add i32 %index, 1
  %has.value = icmp slt i32 %value.index, %len
  br i1 %has.value, label %return.next, label %missing
return.next:
  %value = call ptr @tb_bootstrap_string_array_get(ptr %args, i32 %value.index)
  ret ptr %value
check.inline:
  %arg.len = call i64 @strlen(ptr %arg)
  %long.enough = icmp sgt i64 %arg.len, %option.len
  br i1 %long.enough, label %check.prefix, label %loop.step
check.prefix:
  %prefix = call i1 @tb_bootstrap_starts_with(ptr %arg, ptr %option)
  br i1 %prefix, label %check.equals, label %loop.step
check.equals:
  %equals.ptr = getelementptr inbounds i8, ptr %arg, i64 %option.len
  %equals.byte = load i8, ptr %equals.ptr
  %is.equals = icmp eq i8 %equals.byte, 61
  br i1 %is.equals, label %return.inline, label %loop.step
return.inline:
  %inline.value = getelementptr inbounds i8, ptr %equals.ptr, i64 1
  ret ptr %inline.value
loop.step:
  %next.index = add i32 %index, 1
  br label %loop.cond
missing:
  %empty = call ptr @tb_string_new(i64 0)
  ret ptr %empty
}
define private i64 @tb_bootstrap_hash_string(ptr %value) {
entry:
  br label %loop
loop:
  %index = phi i64 [0, %entry], [%next.index, %body]
  %hash = phi i64 [5381, %entry], [%next.hash, %body]
  %char.ptr = getelementptr inbounds i8, ptr %value, i64 %index
  %char = load i8, ptr %char.ptr
  %done = icmp eq i8 %char, 0
  br i1 %done, label %exit, label %body
body:
  %char.ext = zext i8 %char to i64
  %hash.mul = mul i64 %hash, 33
  %next.hash = add i64 %hash.mul, %char.ext
  %next.index = add i64 %index, 1
  br label %loop
exit:
  ret i64 %hash
}
define private i64 @tb_bootstrap_hash_int(i64 %value) {
entry:
  %mix1.shift = lshr i64 %value, 33
  %mix1 = xor i64 %value, %mix1.shift
  %mix2 = mul i64 %mix1, -49064778989728563
  %mix2.shift = lshr i64 %mix2, 33
  %mix3 = xor i64 %mix2, %mix2.shift
  %mix4 = mul i64 %mix3, -4265267296055464877
  %mix4.shift = lshr i64 %mix4, 33
  %hash = xor i64 %mix4, %mix4.shift
  ret i64 %hash
}
define private ptr @tb_bootstrap_split_char(ptr %src, i8 %sep) {
entry:
  %len = call i64 @strlen(ptr %src)
  br label %count.cond
count.cond:
  %count.index = phi i64 [0, %entry], [%count.next, %count.step]
  %count.parts = phi i64 [1, %entry], [%count.parts.next, %count.step]
  %count.keep = icmp slt i64 %count.index, %len
  br i1 %count.keep, label %count.body, label %count.done
count.body:
  %count.ch.ptr = getelementptr inbounds i8, ptr %src, i64 %count.index
  %count.ch = load i8, ptr %count.ch.ptr
  %count.is.sep = icmp eq i8 %count.ch, %sep
  %count.parts.bump = add i64 %count.parts, 1
  %count.parts.next = select i1 %count.is.sep, i64 %count.parts.bump, i64 %count.parts
  br label %count.step
count.step:
  %count.next = add i64 %count.index, 1
  br label %count.cond
count.done:
  %parts32 = trunc i64 %count.parts to i32
  %array = call ptr @tb_bootstrap_string_array_new(i32 %parts32)
  br label %fill.cond
fill.cond:
  %fill.index = phi i64 [0, %count.done], [%fill.next.char, %fill.step.char], [%fill.next.emit, %fill.step.emit]
  %fill.start = phi i64 [0, %count.done], [%fill.start.keep, %fill.step.char], [%fill.start.bump, %fill.step.emit]
  %fill.out = phi i32 [0, %count.done], [%fill.out.keep, %fill.step.char], [%fill.out.bump, %fill.step.emit]
  %fill.more = icmp ule i64 %fill.index, %len
  br i1 %fill.more, label %fill.body, label %fill.done
fill.body:
  %fill.at.end = icmp eq i64 %fill.index, %len
  br i1 %fill.at.end, label %fill.emit, label %fill.char
fill.char:
  %fill.ch.ptr = getelementptr inbounds i8, ptr %src, i64 %fill.index
  %fill.ch = load i8, ptr %fill.ch.ptr
  %fill.is.sep = icmp eq i8 %fill.ch, %sep
  br i1 %fill.is.sep, label %fill.emit, label %fill.step.char
fill.emit:
  %segment.len = sub i64 %fill.index, %fill.start
  %segment.data = call ptr @tb_string_new(i64 %segment.len)
  %segment.src = getelementptr inbounds i8, ptr %src, i64 %fill.start
  call void @llvm.memcpy.p0.p0.i64(ptr %segment.data, ptr %segment.src, i64 %segment.len, i1 false)
  %segment.term = getelementptr inbounds i8, ptr %segment.data, i64 %segment.len
  store i8 0, ptr %segment.term
  call void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %fill.out, ptr %segment.data, i1 true)
  %fill.out.bump = add i32 %fill.out, 1
  %fill.start.bump = add i64 %fill.index, 1
  br label %fill.step.emit
fill.step.char:
  %fill.next.char = add i64 %fill.index, 1
  %fill.start.keep = add i64 %fill.start, 0
  %fill.out.keep = add i32 %fill.out, 0
  br label %fill.cond
fill.step.emit:
  %fill.next.emit = add i64 %fill.index, 1
  br label %fill.cond
fill.done:
  ret ptr %array
}
define private ptr @tb_bootstrap_split_string(ptr %src, ptr %sep) {
entry:
  %sep.len = call i64 @strlen(ptr %sep)
  %sep.empty = icmp eq i64 %sep.len, 0
  br i1 %sep.empty, label %split.chars, label %check.one
split.chars:
  %chars = call ptr @tb_bootstrap_split_chars(ptr %src)
  ret ptr %chars
check.one:
  %sep.one = icmp eq i64 %sep.len, 1
  br i1 %sep.one, label %split.one, label %generic
split.one:
  %sep.ch = load i8, ptr %sep
  %single = call ptr @tb_bootstrap_split_char(ptr %src, i8 %sep.ch)
  ret ptr %single
generic:
  br label %count.cond
count.cond:
  %count.cursor = phi ptr [%src, %generic], [%count.next.cursor, %count.step]
  %count.parts = phi i64 [1, %generic], [%count.next.parts, %count.step]
  %count.found = call ptr @strstr(ptr %count.cursor, ptr %sep)
  %count.done = icmp eq ptr %count.found, null
  br i1 %count.done, label %count.finish, label %count.step
count.step:
  %count.next.parts = add i64 %count.parts, 1
  %count.next.cursor = getelementptr inbounds i8, ptr %count.found, i64 %sep.len
  br label %count.cond
count.finish:
  %parts32 = trunc i64 %count.parts to i32
  %array = call ptr @tb_bootstrap_string_array_new(i32 %parts32)
  br label %fill.cond
fill.cond:
  %fill.cursor = phi ptr [%src, %count.finish], [%fill.next.cursor, %fill.step]
  %fill.out = phi i32 [0, %count.finish], [%fill.next.out, %fill.step]
  %fill.found = call ptr @strstr(ptr %fill.cursor, ptr %sep)
  %fill.done = icmp eq ptr %fill.found, null
  br i1 %fill.done, label %fill.tail, label %fill.body
fill.body:
  %fill.start.int = ptrtoint ptr %fill.cursor to i64
  %fill.found.int = ptrtoint ptr %fill.found to i64
  %fill.segment.len = sub i64 %fill.found.int, %fill.start.int
  %fill.segment.data = call ptr @tb_string_new(i64 %fill.segment.len)
  call void @llvm.memcpy.p0.p0.i64(ptr %fill.segment.data, ptr %fill.cursor, i64 %fill.segment.len, i1 false)
  %fill.segment.term = getelementptr inbounds i8, ptr %fill.segment.data, i64 %fill.segment.len
  store i8 0, ptr %fill.segment.term
  call void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %fill.out, ptr %fill.segment.data, i1 true)
  %fill.next.cursor = getelementptr inbounds i8, ptr %fill.found, i64 %sep.len
  %fill.next.out = add i32 %fill.out, 1
  br label %fill.step
fill.tail:
  %fill.tail.len = call i64 @strlen(ptr %fill.cursor)
  %fill.tail.data = call ptr @tb_string_new(i64 %fill.tail.len)
  call void @llvm.memcpy.p0.p0.i64(ptr %fill.tail.data, ptr %fill.cursor, i64 %fill.tail.len, i1 false)
  %fill.tail.term = getelementptr inbounds i8, ptr %fill.tail.data, i64 %fill.tail.len
  store i8 0, ptr %fill.tail.term
  call void @tb_bootstrap_string_array_set_owned(ptr %array, i32 %fill.out, ptr %fill.tail.data, i1 true)
  ret ptr %array
fill.step:
  br label %fill.cond
}
