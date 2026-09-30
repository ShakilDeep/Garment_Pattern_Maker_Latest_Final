from pathlib import Path

import pytest

from app.infrastructure.parsers import parse_xlsx


@pytest.fixture(scope="module")
def rows():
    root = Path(__file__).resolve().parents[2]
    return parse_xlsx((root / "references/Book2(4).xlsx").read_bytes(), "Book2(4).xlsx")
