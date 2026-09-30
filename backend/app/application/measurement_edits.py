"""Measurement edit and undo/redo commands."""
import copy

from app.application.errors import NotReady
from app.application.state import transition


def update_measurements(service, p, changes, size):
    service._ensure_active(p)
    before = copy.deepcopy(p["measurements"])
    rows = {r["key"]: r for r in p["measurements"]}
    for key, value in changes.items():
        if key not in rows:
            rows[key] = {
                "key": key, "code": key, "label": key.replace("_", " ").title(),
                "unit": "cm", "tolerance": None, "source": "Manual entry",
                "sheet": "", "row": 0, "values": {},
            }
            p["measurements"].append(rows[key])
        cell = rows[key]["values"].setdefault(
            size, {"raw": None, "formula": None, "cell": "manual", "issue": None}
        )
        cell.update(value=value, override=True, issue=None)
    p["undo"].append(before)
    p["undo"] = p["undo"][-20:]
    p["redo"] = []
    p["resolutions"].pop("review", None)
    service.invalidate(p)
    transition(p, "NEEDS_INPUT", "measurements_changed")
    return service.repo.save(p, "measurements_changed", {"size": size, "changes": changes})


def history(service, p, direction):
    source, target = ("undo", "redo") if direction == "undo" else ("redo", "undo")
    if not p[source]:
        raise NotReady(f"Nothing to {direction}")
    p[target].append(p["measurements"])
    p["measurements"] = p[source].pop()
    p["resolutions"].pop("review", None)
    service.invalidate(p)
    transition(p, "NEEDS_INPUT", f"measurements_{direction}")
    return service.repo.save(p, direction)
