import argparse
from pathlib import Path
import re


TARGET = 'target triple = "x86_64-w64-windows-gnu"'
SETJMP = re.compile(r"@setjmp\(ptr ([^,)]+)\)")
JUMP_BUFFER = re.compile(r"(\b(?:alloca|getelementptr(?: inbounds)?) )\[192 x i8\]")
CRT_SYMBOLS = re.compile(r"@(gettimeofday|getline)\(")


def target_ir(source, output):
    with source.open(encoding="utf-8") as ir, output.open(
        "w", encoding="utf-8", newline="\n"
    ) as windows_ir:
        windows_ir.write(f"{TARGET}\n")
        for line in ir:
            if line.startswith("target triple") or line.startswith("target datalayout"):
                raise ValueError("Expected LLVM IR without target metadata")
            if line == "declare i32 @setjmp(ptr) returns_twice\n":
                line = "declare i32 @_setjmp(ptr, ptr) returns_twice\n"
            # Embedded LLVM templates are string constants. Only adapt real instructions.
            elif line.startswith((" ", "\t")):
                # A null frame requests a jump without Windows SEH unwinding.
                line = SETJMP.sub(r"@_setjmp(ptr \1, ptr null)", line)
                if "alloca [192 x i8]" in line:
                    line = line.rstrip("\n").split(", align", 1)[0] + ", align 16\n"
                line = JUMP_BUFFER.sub(r"\1[256 x i8]", line)
            if line.startswith(("declare ", " ", "\t")):
                line = CRT_SYMBOLS.sub(r"@tb_windows_\1(", line)
            windows_ir.write(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Target tb 0.5.0 LLVM IR at Windows x64")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    target_ir(args.source, args.output)
