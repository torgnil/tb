def make_grid(size: int) -> list[list[int]]:
    rows: list[list[int]] = []
    for r in range(size):
        row: list[int] = []
        for c in range(size):
            row.append((r * 7 + c * 11) % 23)
        rows.append(row)
    return rows


def main() -> None:
    grid = make_grid(73)
    total = 0

    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            total += value * (r + 1) - c

    print(total)


if __name__ == "__main__":
    main()
