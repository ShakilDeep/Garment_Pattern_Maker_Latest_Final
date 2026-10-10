"""The 1078375 measurement set (size L), derived from the client PDS because the tech pack has no chart.

Each value names its source on the PDS sew line (``data/measurements_1078375_L.json``). When the client sends
the 1078375 measurement chart, it replaces these through Missing Information.
"""
import json
from functools import cache
from pathlib import Path

MEASUREMENTS_FILE = Path(__file__).parents[2] / "data" / "measurements_1078375_L.json"
GRADED_FILE = Path(__file__).parents[2] / "data" / "measurements_1078375_graded.json"


@cache
def _values() -> tuple[tuple[str, float], ...]:
    data = json.loads(MEASUREMENTS_FILE.read_text(encoding="utf-8"))
    return tuple((name, float(entry["value_cm"])) for name, entry in data["measurements"].items())


def reference_measurements() -> dict[str, float]:
    """A fresh copy, so a caller can change a value without touching the cached set."""
    return dict(_values())


@cache
def _graded() -> dict[str, tuple[tuple[str, float], ...]]:
    data = json.loads(GRADED_FILE.read_text(encoding="utf-8"))
    return {size: tuple(values.items()) for size, values in data["sizes"].items()}


def graded_sizes() -> tuple[str, ...]:
    """The PDS size range, S to 3XL, in order (docs/grading/shirt.md)."""
    return tuple(_graded())


def graded_measurements(size: str) -> dict[str, float]:
    """One size's graded measurement set; KeyError for a size the PDS does not have."""
    if size not in _graded():
        raise KeyError(f"The 1078375 grading has no size {size}")
    return dict(_graded()[size])
