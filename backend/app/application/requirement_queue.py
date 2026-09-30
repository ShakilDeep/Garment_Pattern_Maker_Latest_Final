"""Specification: order unresolved blockers into a guided next-item queue."""
from app.application.requirements import requirements

RANK = {"MISSING": 0, "CONFLICTING": 1, "AMBIGUOUS": 2, "DEMO_DEFAULT_AVAILABLE": 3}


def guided_queue(project, size="L"):
    blockers = requirements(project, size)["blockers"]
    items = sorted(blockers, key=lambda item: (RANK.get(item["status"], 9), item["name"]))
    return {"items": items, "next": items[0] if items else None, "remaining": len(items)}
