from dataclasses import dataclass


@dataclass(slots=True)
class Stat:
    count: int
    total: int


def make_rows(repeats: int) -> list[str]:
    return [f"cat{i % 9},{10 + (i % 23)}" for i in range(repeats)]


def main() -> None:
    rows = make_rows(5001)
    stats: dict[str, Stat] = {}

    for row in rows:
        key, value_text = row.split(",")
        value = int(value_text)
        current = stats.get(key, Stat(0, 0))
        stats[key] = Stat(current.count + 1, current.total + value)

    total = 0
    for i in range(9):
        current = stats[f"cat{i}"]
        total += current.count * current.total

    print(total)


if __name__ == "__main__":
    main()
