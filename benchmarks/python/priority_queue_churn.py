import heapq


def build_value(round_: int, index: int) -> int:
    return (round_ * 17 + index * 31 + index * index) % 997


def main() -> None:
    total = 0
    for round_ in range(1200):
        values = [-build_value(round_ + 1, index) for index in range(64)]
        heapq.heapify(values)
        for index in range(8):
            heapq.heappush(values, -build_value(round_ + 53, index + 71))
        for position in range(1, 73):
            total += -heapq.heappop(values) * position
    print(total)


if __name__ == "__main__":
    main()
