from dataclasses import dataclass


@dataclass(slots=True)
class Point:
    x: int
    y: int


def main() -> None:
    points: list[Point] = []
    for i in range(5000):
        points.append(Point(i + 1, (i * 3) % 31))

    total = 0
    for point in points:
        total += point.x + point.y * 2

    print(total)


if __name__ == "__main__":
    main()
