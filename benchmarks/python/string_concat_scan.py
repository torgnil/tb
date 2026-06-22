def make_chunk(index: int) -> str:
    rem = index % 5
    if rem == 0:
        return "alpha"
    if rem == 1:
        return "beta"
    if rem == 2:
        return "gamma"
    if rem == 3:
        return "delta"
    return "omega"


def main() -> None:
    parts: list[str] = []
    for i in range(900):
        parts.append(make_chunk(i + 1))
        parts.append(",")
    text = "".join(parts)

    score = 0
    for i, ch in enumerate(text):
        if ch == "a":
            score += i % 17
        if ch == ",":
            score += 1

    print(score)


if __name__ == "__main__":
    main()
