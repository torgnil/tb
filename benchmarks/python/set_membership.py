def main() -> None:
    seen: set[int] = set()
    seed = 1

    for i in range(20000):
        seen.add((i * 37 + seed) % 4096)

    total = 0
    for i in range(4096):
        if i in seen:
            total += i % 97

    print(total + len(seen))


if __name__ == "__main__":
    main()
