"""The 1078375 measurement set (size L), derived from the client PDS because the tech pack has no chart.

Each value names its source on the PDS sew line (``data/measurements_1078375_L.json``). When the client sends
the 1078375 measurement chart, it replaces these through Missing Information.
"""
import json
from functools import cache
from pathlib import Path

MEASUREMENTS_FILE = Path(__file__).parents[2] / "data" / "measurements_1078375_L.json"


@cache
def _values() -> tuple[tuple[str, float], ...]:
    data = json.loads(MEASUREMENTS_FILE.read_text(encoding="utf-8"))
    return tuple((name, float(entry["value_cm"])) for name, entry in data["measurements"].items())


def reference_measurements() -> dict[str, float]:
    """A fresh copy, so a caller can change a value without touching the cached set."""
    return dict(_values())
