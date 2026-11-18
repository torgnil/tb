import argparse
from pathlib import Path
import re


TARGET = 'target triple = "x86_64-w64-windows-gnu"'
SETJMP = re.compile(r"@setjmp\(ptr ([^,)]+)\)")
JUMP_BUFFER = re.compile(r"(\b(?:alloca|getelementptr(?: inbounds)?) )\[192 x i8\]")
CRT_SYMBOLS = re.compile(r"@(gettimeofday|getline)\(")
NUM_SUBMIT = re.compile(r"@(tb_thread_pool_submit_num(?:_num|_i64|_int_array)?)\(ptr ([^,]+), ptr (@[^, )]+)")
NUM_TYPE = "%tb_bootstrap_num"
NUM_RESULT = f"ptr sret({NUM_TYPE}) align 8"
NUM_CALLBACK_ARGS = {
    "tb_thread_pool_submit_num": ("", ""),
    "tb_thread_pool_submit_num_num": (", ptr %arg", f"{NUM_TYPE} %value"),
    "tb_thread_pool_submit_num_i64": (", i64 %arg", "i64 %arg"),
    "tb_thread_pool_submit_num_int_array": (", ptr %arg", "ptr %arg"),
}


def num_callback(name, symbol, bridge):
    # Windows C passes a 16-byte num by address and returns it through sret.
    # Preserve the compiler's aggregate ABI on the tb side of the bridge.
    parameters, arguments = NUM_CALLBACK_ARGS[name]
    load = ""
    if name == "tb_thread_pool_submit_num_num":
        load = f"  %value = load {NUM_TYPE}, ptr %arg, align 8\n"
    return (
        f"\ndefine private void {bridge}({NUM_RESULT} %out{parameters}) {{\n"
        f"{load}  %result = call {NUM_TYPE} {symbol}({arguments})\n"
        f"  store {NUM_TYPE} %result, ptr %out, align 8\n"
        "  ret void\n}\n"
    )


def target_ir(source, output):
    callbacks = {}

    def adapt_submit(match):
        name, pool, symbol = match.groups()
        key = (name, symbol)
        if key not in callbacks:
            bridge = f"@tb.windows.num.callback.{len(callbacks)}"
            callbacks[key] = (bridge, num_callback(name, symbol, bridge))
        bridge, _ = callbacks[key]
        if name == "tb_thread_pool_submit_num_num":
            name = "tb_windows_submit_num_num"
        return f"@{name}(ptr {pool}, ptr {bridge}"

    with source.open(encoding="utf-8") as ir, output.open(
        "w", encoding="utf-8", newline="\n"
    ) as windows_ir:
        windows_ir.write(f"{TARGET}\n")
        for line in ir:
            if line.startswith("target triple") or line.startswith("target datalayout"):
                raise ValueError("Expected LLVM IR without target metadata")
            if line == "declare i32 @setjmp(ptr) returns_twice\n":
                line = "declare i32 @_setjmp(ptr, ptr) returns_twice\n"
            elif line == f"declare ptr @tb_thread_pool_submit_num_num(ptr, ptr, {NUM_TYPE})\n":
                line = (
                    "declare ptr @tb_thread_pool_submit_num_num(ptr, ptr, ptr)\n"
                    f"define private ptr @tb_windows_submit_num_num(ptr %pool, ptr %fn, {NUM_TYPE} %arg) {{\n"
                    f"  %input = alloca {NUM_TYPE}, align 8\n"
                    f"  store {NUM_TYPE} %arg, ptr %input, align 8\n"
                    "  %future = call ptr @tb_thread_pool_submit_num_num(ptr %pool, ptr %fn, ptr %input)\n"
                    "  ret ptr %future\n}\n"
                )
            elif line == f"declare {NUM_TYPE} @tb_future_num_await(ptr)\n":
                line = (
                    f"declare void @tb_future_num_await({NUM_RESULT}, ptr)\n"
                    f"define private {NUM_TYPE} @tb_windows_future_num_await(ptr %future) {{\n"
                    f"  %output = alloca {NUM_TYPE}, align 8\n"
                    f"  call void @tb_future_num_await({NUM_RESULT} %output, ptr %future)\n"
                    f"  %result = load {NUM_TYPE}, ptr %output, align 8\n"
                    f"  ret {NUM_TYPE} %result\n}}\n"
                )
            # Embedded LLVM templates are string constants. Only adapt real instructions.
            elif line.startswith((" ", "\t")):
                # A null frame requests a jump without Windows SEH unwinding.
                line = SETJMP.sub(r"@_setjmp(ptr \1, ptr null)", line)
                if "alloca [192 x i8]" in line:
                    line = line.rstrip("\n").split(", align", 1)[0] + ", align 16\n"
                line = JUMP_BUFFER.sub(r"\1[256 x i8]", line)
                line = NUM_SUBMIT.sub(adapt_submit, line)
                line = line.replace(f"call {NUM_TYPE} @tb_future_num_await(",
                                    f"call {NUM_TYPE} @tb_windows_future_num_await(")
            if line.startswith(("declare ", " ", "\t")):
                line = CRT_SYMBOLS.sub(r"@tb_windows_\1(", line)
            windows_ir.write(line)
        for _, definition in callbacks.values():
            windows_ir.write(definition)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Target tb 0.5.0 LLVM IR at Windows x64")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    target_ir(args.source, args.output)
