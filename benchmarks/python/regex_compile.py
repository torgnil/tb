import re


def main() -> None:
    compiled = 0
    for i in range(1000):
        pattern = f"[a-z]+[0-9]+x{i}".encode("ascii")
        re.compile(pattern, re.ASCII)
        compiled += 1
    print(compiled)


if __name__ == "__main__":
    main()
