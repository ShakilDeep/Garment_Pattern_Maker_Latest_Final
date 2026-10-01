"""Command guards: measurement edits target known keys, stay in scope and inside each measurement's range."""
from app.application.errors import Unprocessable
from app.domain.catalog import MAPPING
from app.domain.measurement_bounds import accepts, plausible_range

CATALOG_KEYS = frozenset(MAPPING.values())
# The 422 message names at most this many unknown keys, each cut to a readable length.
MAX_ECHOED_KEYS = 5
MAX_ECHOED_KEY_LENGTH = 40


def _range_message(key, low, high):
    if low == 0:
        return f"Measurement {key} must be greater than 0 and at most {high:.2f} cm"
    return f"Measurement {key} must be between {low:.2f} and {high:.2f} cm"


def bound_changes(p, changes):
    """Guard: every changed key is known and every value lies inside that measurement's plausible range."""
    rows = {row["key"]: row for row in p["measurements"]}
    unknown = sorted(set(changes) - set(rows) - CATALOG_KEYS)
    if unknown:
        named = ", ".join(key[:MAX_ECHOED_KEY_LENGTH] for key in unknown[:MAX_ECHOED_KEYS])
        raise Unprocessable("MEASUREMENT_UNKNOWN", f"Unknown measurement keys ({len(unknown)}): {named}")
    for key, value in changes.items():
        row = rows.get(key, {"key": key, "values": {}})
        if not accepts(row, value):
            low, high = plausible_range(row)
            raise ValueError(_range_message(key[:MAX_ECHOED_KEY_LENGTH], low, high))


def scoped_changes(measurement_id, changes):
    if set(changes) != {measurement_id}:
        raise ValueError("Measurement updates must target only the selected measurement")
    return changes
