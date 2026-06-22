from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int
    z: int


def next_point(point: Point, index: int) -> Point:
    return Point(
        point.x + index % 7,
        point.y + index % 11,
        point.z + index % 13,
    )


def score(point: Point) -> int:
    return point.x * 3 + point.y * 5 + point.z * 7


def main() -> None:
    point = Point(1, 2, 3)
    total = 0
    for i in range(50000):
        point = next_point(point, i)
        total += score(point) % 1009
    print(total)


if __name__ == "__main__":
    main()
