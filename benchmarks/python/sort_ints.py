def compare_up(left: int, right: int) -> int:
    return left - right


def build_value(round_: int, index: int) -> int:
    return (round_ * 17 + index * 31 + index * index) % 257


def main() -> None:
    total = 0
    for round_ in range(1500):
        values: list[int] = []
        for index in range(64):
            values.append(build_value(round_ + 1, index))
        values.sort(key=None)
        total += values[0] + values[31] + values[63]
    print(total)


if __name__ == "__main__":
    main()
