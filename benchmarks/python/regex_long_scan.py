import re

pattern = re.compile(r"(ab|ac|ad|ae|af|ag|ah|a)+z")
full_text = "a" * 8192
search_text = "b" * 4096 + "ab" * 2048 + "z"
full_matches = 0
search_matches = 0

for _ in range(1000):
    full_matches += pattern.fullmatch(full_text) is not None
    search_matches += pattern.search(search_text) is not None

print(full_matches)
print(search_matches)
