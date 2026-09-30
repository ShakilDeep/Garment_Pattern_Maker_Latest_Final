"""Fail when any source file exceeds the per-file line budget.

Usage: python scripts/check_lines.py [root ...]
With no arguments, the project's source roots are checked.
"""
import sys
from pathlib import Path

LINE_LIMIT = 100
SOURCE_SUFFIXES = frozenset({".py", ".ts", ".tsx"})
SKIPPED_DIRS = frozenset({"node_modules", "__pycache__", "dist", ".venv", "test-results"})
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = ("backend/app", "backend/tests", "frontend/src", "frontend/e2e", "scripts")


def _source_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative_parts = path.relative_to(root).parts
        if path.suffix in SOURCE_SUFFIXES and path.is_file() and not SKIPPED_DIRS.intersection(relative_parts):
            yield path


def _line_count(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def oversized(roots, limit: int = LINE_LIMIT) -> list[tuple[Path, int]]:
    """Return (path, line_count) for every source file longer than ``limit``."""
    offenders = []
    for root in roots:
        for path in _source_files(Path(root)):
            count = _line_count(path)
            if count > limit:
                offenders.append((path, count))
    return offenders


def main(argv: list[str]) -> int:
    roots = [Path(arg) for arg in argv] or [PROJECT_ROOT / root for root in DEFAULT_ROOTS]
    offenders = oversized(roots)
    for path, count in offenders:
        print(f"{path}: {count} lines (limit {LINE_LIMIT})")
    return 1 if offenders else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
