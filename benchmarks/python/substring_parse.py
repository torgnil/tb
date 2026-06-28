def make_rows(repeats: int) -> list[str]:
    return [f"L{1000 + i}:{2000 + (i % 97)}" for i in range(repeats)]


def main() -> None:
    rows = make_rows(3001)
    total = 0

    for row in rows:
        split = row.index(":")
        left = int(row[1:split])
        right = int(row[split + 1 :])
        total += left - right

    print(total)


if __name__ == "__main__":
    main()
