def main() -> None:
    seen: set[int] = set()

    for i in range(25001):
        seen.add((i * 29 + 1) % 8192)

    total = 0
    for i in range(12000):
        if ((i * 7) % 8192) in seen:
            total += i % 41

    print(total + len(seen))


if __name__ == "__main__":
    main()
