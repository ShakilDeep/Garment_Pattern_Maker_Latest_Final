"""A V6 style from a V5 project's current pattern and its grades (Strangler Fig, via the P1-03 adapter).

Nothing is invented: the size range is V5's catalog range, and sizes the project has not graded stay empty.
Every piece gets the pattern's own uniform seam allowance with mitred corners. V5 cuts with Shapely's mitre
buffer, whose default mitre limit (5) clips very sharp corners; V6 mitres run to the meeting point, so a cut
can differ from V5's `cut_points` at acute corners. Only grades drafted from the current pattern
(`graded_from` unset or its id) and not stale are used; V5 trusts `graded_from` the same way. The project
is not changed, and V5-only piece fields (seams, marks, cut points, ...) are not carried into the style.
"""

from dataclasses import replace
from uuid import uuid4

from app.application.errors import NotReady
from app.domain.catalog import SIZES
from app.domain.pattern.ids import StyleId
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style
from app.infrastructure.legacy_pattern_adapter import piece_from_v5

STYLE_ID_HEX = 12


def _current_patterns(project: dict) -> dict[str, dict]:
    pattern = project.get("pattern")
    if project.get("archived") or project.get("state") == "ARCHIVED":
        raise NotReady("Project is archived; restore it before creating a style")
    if not pattern or pattern.get("stale"):
        raise NotReady("Generate a current pattern before creating a style")
    grades = [
        grade for grade in project.get("grades", [])
        if grade.get("graded_from") in (None, pattern["id"]) and not grade.get("stale")
    ]
    return {**{grade["size"]: grade for grade in grades}, pattern["size"]: pattern}


def style_from_project(project: dict) -> Style:
    patterns = _current_patterns(project)
    base = project["pattern"]
    geometry = {
        size: SizePieces.from_pieces(legacy.piece for legacy in map(piece_from_v5, patterns[size]["pieces"]))
        for size in SIZES
        if size in patterns
    }
    allowance = SeamAllowance(base.get("seam_allowance", 0))
    style_id = StyleId(f"style-{uuid4().hex[:STYLE_ID_HEX]}")
    style = Style(style_id, project["name"], SIZES, base["size"], geometry)
    return replace(style, allowances={piece: allowance for piece in style.piece_ids})
