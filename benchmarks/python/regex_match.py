import re


def main() -> None:
    pattern = re.compile(rb"([a-z]+|[0-9]+)", re.ASCII)
    samples = (b"alpha", b"12345", b"ab!cd", b"---", b"----------------------------------------")
    full = 0
    for _ in range(1000):
        for sample in samples:
            full += pattern.fullmatch(sample) is not None
    print(full)


if __name__ == "__main__":
    main()
