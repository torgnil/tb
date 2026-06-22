def main() -> None:
    values: list[int] = []
    seed = 1
    for i in range(30000):
        values.append((i * 31 + seed) % 997)

    total = 0
    for i, value in enumerate(values):
        total += value * (i % 13)

    print(total)


if __name__ == "__main__":
    main()
