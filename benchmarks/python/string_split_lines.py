def make_text(repeats: int) -> str:
    parts: list[str] = []
    for i in range(repeats):
        parts.append(f"line-{i}-value-{i % 17}\n")
    return "".join(parts)


def main() -> None:
    text = make_text(4001)
    lines = text.splitlines()
    total = 0

    for line in lines:
        total += len(line)
        total += line.index("-")

    print(total + len(lines))


if __name__ == "__main__":
    main()
