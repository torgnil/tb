def main() -> None:
    counts = {i: 0 for i in range(257)}

    for i in range(20001):
        key = (i * 17 + 1) % 257
        counts[key] = counts[key] + 1

    total = 0
    for i in range(257):
        total += counts[i] * (i % 13)

    print(total)


if __name__ == "__main__":
    main()
