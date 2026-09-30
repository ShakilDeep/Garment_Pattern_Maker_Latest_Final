"""Pattern generate/grade/nest commands."""
from uuid import uuid4

from app.application.errors import NotReady
from app.application.requirements import requirements
from app.application.state import ALLOWED, transition
from app.domain.drafting import draft
from app.infrastructure.geometry_adapter import apply_allowance, validate
from app.infrastructure.marker import marker_batch


def build(p, size, allowance=0):
    check = requirements(p, size)
    if not check["ready"]:
        raise NotReady("Resolve required inputs: " + ", ".join(i["name"] for i in check["blockers"]))
    values = {
        r["key"]: r["values"][size]["value"]
        for r in p["measurements"]
        if r["values"].get(size, {}).get("value") is not None
    }
    if p["resolutions"].get("placket") == "techpack":
        values["front_placket_width"] = p["techpack"]["placket_cm"]
    pattern = draft(values, size, p["resolutions"].get("profile", "demo_v1"))
    pattern["id"] = str(uuid4())
    pattern["sources"] = p["documents"]
    pattern["resolutions"] = dict(p["resolutions"])
    pattern["validation"] = validate(pattern)
    apply_allowance(pattern, allowance)
    pattern["stale"] = False
    if any(i["severity"] == "ERROR" for i in pattern["validation"]):
        raise ValueError("Generated geometry failed structural validation")
    return pattern


def clear(service, p):
    """Remove current pattern/grades/marker so the studio canvas is empty."""
    service._ensure_active(p)
    if p.get("pattern"):
        p.setdefault("pattern_history", []).append(p["pattern"])
    p["pattern"] = None
    p["grades"] = []
    p["marker"] = None
    p["previous_marker"] = None
    if "MEASUREMENTS_READY" in ALLOWED.get(p.get("state", "CREATED"), set()):
        transition(p, "MEASUREMENTS_READY", "pattern_cleared")
    service.repo.save(p, "pattern_cleared")
    return p


def generate(service, p, size, allowance=0):
    service._ensure_active(p)
    pattern = build(p, size, allowance)
    if p.get("state") == "NEEDS_INPUT":
        transition(p, "MEASUREMENTS_READY", "requirements_satisfied")
    if p["pattern"]:
        p["pattern_history"].append(p["pattern"])
    p["pattern"] = pattern
    p["grades"] = []
    p["marker"] = None
    p["previous_marker"] = None
    transition(p, "PATTERN_NEEDS_REVIEW", "pattern_generated")
    service.repo.save(p, "pattern_generated", {"id": pattern["id"], "size": size})
    return pattern


def grade(service, p, sizes, allowance=None):
    service._ensure_active(p)
    seam = allowance if allowance is not None else (p["pattern"]["seam_allowance"] if p["pattern"] else 0)
    results = [build(p, selected, seam) for selected in sizes]
    p["grades"] = results
    p["marker"] = None
    p["previous_marker"] = None
    transition(p, "GRADING_READY", "sizes_generated")
    service.repo.save(p, "sizes_generated", sizes)
    return results


def nest(service, p, size, width, quantity, gap, quantities=None, seed=0, time_budget_ms=250,
         iterations=1, grain_policy="vertical"):
    service._ensure_active(p)
    if not p["pattern"] or p["pattern"].get("stale"):
        raise NotReady("Generate a current pattern before nesting")
    quantities = quantities if quantities is not None else {size: quantity}
    patterns = {item["size"]: item for item in [p["pattern"], *p["grades"]]}
    for selected in quantities:
        pattern = patterns.get(selected)
        if not pattern or pattern.get("stale"):
            raise NotReady(f"Generate size {selected} before nesting")
        if any(i["severity"] == "ERROR" for i in pattern["validation"]):
            raise NotReady(f"Resolve validation errors for size {selected} before nesting")
    result = marker_batch(patterns, width, quantities, gap, seed, time_budget_ms, iterations, grain_policy)
    p["previous_marker"] = p["marker"]
    p["marker"] = result
    transition(p, "MARKER_READY", "marker_generated")
    service.repo.save(p, "marker_generated", {"width": width, "gap": gap, "quantities": quantities,
                                              "pattern_ids": result["pattern_ids"]})
    return result
