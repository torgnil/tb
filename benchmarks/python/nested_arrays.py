def make_row(row: int, width: int) -> list[int]:
    result: list[int] = []
    for col in range(width):
        result.append((row * 17 + col * 31) % 101)
    return result


def main() -> None:
    grid: list[list[int]] = []
    height = 121
    width = 80

    for row in range(height):
        grid.append(make_row(row, width))

    total = 0
    for row, values in enumerate(grid):
        for col, value in enumerate(values):
            total += value * ((row + col) % 9)

    print(total)


if __name__ == "__main__":
    main()
