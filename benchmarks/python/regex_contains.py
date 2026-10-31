import re


def main() -> None:
    pattern = re.compile(rb"([a-z]+|[0-9]+)", re.ASCII)
    samples = (b"alpha", b"12345", b"ab!cd", b"---", b"----------------------------------------")
    contains = 0
    for _ in range(1000):
        for sample in samples:
            contains += pattern.search(sample) is not None
    print(contains)


if __name__ == "__main__":
    main()
