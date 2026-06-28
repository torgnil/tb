def main() -> None:
    parts: list[str] = []
    for i in range(3501):
        parts.append("item")
        parts.append(str(i))
        parts.append("-")
        parts.append(str(i % 19))
        parts.append("|")

    print(len("".join(parts)))


if __name__ == "__main__":
    main()
