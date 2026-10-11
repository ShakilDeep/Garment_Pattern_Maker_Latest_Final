"""Pattern generate/grade/nest commands."""
from uuid import uuid4

from app.application.block_inputs import draft_values
from app.application.drafting_engine import Draft, draft
from app.application.errors import NotReady
from app.application.pattern_inputs import snapshot_inputs
from app.application.pattern_validation import validate_draft
from app.application.project_style import keep_named_drafts
from app.application.requirements import requirements
from app.application.state import ALLOWED, transition
from app.domain.blocks.registry import demo_block, installed
from app.infrastructure.geometry_adapter import apply_allowance
from app.infrastructure.marker import marker_batch


def build_draft(p, size, allowance=0) -> Draft:
    """Draft one size through the engine. A dict block's V5 cut uses the uniform allowance; a named
    block's pieces carry their own per-edge allowances, so its view already holds the cut line."""
    check = requirements(p, size)
    if not check["ready"]:
        raise NotReady("Resolve required inputs: " + ", ".join(i["name"] for i in check["blockers"]))
    block = installed().get(p["resolutions"].get("profile", demo_block().id))
    values, sources = draft_values(p, block, size)
    result = draft(block, values, size, p.get("style_options", {}))
    pattern = result.pattern
    if sources is not None:
        pattern["input_sources"] = dict(sources)  # the From-block list the accuracy report reads
    pattern["id"] = str(uuid4())
    pattern["sources"] = p["documents"]
    pattern["resolutions"] = dict(p["resolutions"])
    pattern["validation"] = validate_draft(result)
    if not result.allowances:
        apply_allowance(pattern, allowance)
    pattern["stale"] = False
    if any(i["severity"] == "ERROR" for i in pattern["validation"]):
        raise ValueError("Generated geometry failed structural validation")
    return result


def build(p, size, allowance=0):
    return build_draft(p, size, allowance).pattern


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
    result = build_draft(p, size, allowance)
    pattern = result.pattern
    pattern["inputs"] = snapshot_inputs(p)
    keep_named_drafts(p, {size: result}, size)
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
