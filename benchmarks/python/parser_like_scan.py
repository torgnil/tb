def is_name_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def make_source(repeats: int) -> str:
    parts: list[str] = []
    for i in range(repeats):
        parts.append("record Point(int x, int y);\n")
        parts.append("int add(int left, int right) { return left + right; }\n")
        parts.append(f"if (value_{i} >= 10) {{ print(value_{i}); }}\n")
    return "".join(parts)


def main() -> None:
    source = make_source(81)
    tokens = 0
    numbers = 0
    index = 0

    while index < len(source):
        ch = source[index]
        if ch.isdigit():
            numbers += 1
            while index < len(source) and source[index].isdigit():
                index += 1
            tokens += 1
        elif is_name_char(ch):
            while index < len(source) and is_name_char(source[index]):
                index += 1
            tokens += 1
        else:
            if not ch.isspace():
                tokens += 1
            index += 1

    print(tokens * 1000 + numbers)


if __name__ == "__main__":
    main()
