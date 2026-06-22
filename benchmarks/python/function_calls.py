def step_a(value: int) -> int:
    return (value * 3 + 7) % 1000003


def step_b(value: int, index: int) -> int:
    return step_a(value + index) ^ (index & 255)


def step_c(value: int, index: int) -> int:
    return step_b(value, index) + step_a(index)


def main() -> None:
    result = 1
    for i in range(120000):
        result = step_c(result, i) % 1000003
    print(result)


if __name__ == "__main__":
    main()
