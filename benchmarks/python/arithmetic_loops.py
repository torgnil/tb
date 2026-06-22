MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63


def i64(value: int) -> int:
    value &= MASK64
    if value >= SIGN64:
        return value - (1 << 64)
    return value


def mix(value: int, index: int) -> int:
    value = i64(value + i64(index * 17))
    value = i64(value ^ i64(index << 2))
    value = i64(value - (index % 11))
    return i64(value & 1048575)


def main() -> None:
    result = 1
    for i in range(200000):
        result = mix(result, i)
    print(result)


if __name__ == "__main__":
    main()
