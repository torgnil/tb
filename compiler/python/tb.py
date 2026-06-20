from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[2]
repo_root_str = str(repo_root)
if sys.path:
    sys.path[0] = repo_root_str
else:
    sys.path.insert(0, repo_root_str)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from compiler.python.main import main


if __name__ == "__main__":
    raise SystemExit(main())
