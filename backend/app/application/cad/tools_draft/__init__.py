"""Draft tools (CAD-01): one Command per tool, registered by name on the style command registry."""

from app.application.cad.registry import Factory, Registry
from app.application.cad.tools_draft.construct import offset_line, parallel_line, perpendicular_line
from app.application.cad.tools_draft.curve import curve_edge
from app.application.cad.tools_draft.intersect import intersection_point
from app.application.cad.tools_draft.line import add_line
from app.application.cad.tools_draft.point import add_point
from app.application.cad.tools_draft.shape import add_circle, add_rectangle
from app.domain.pattern.style import Style

DRAFT_TOOLS: dict[str, Factory[Style]] = {
    "add_point": add_point,
    "add_line": add_line,
    "curve_edge": curve_edge,
    "add_rectangle": add_rectangle,
    "add_circle": add_circle,
    "offset_edge": offset_line,
    "parallel_line": parallel_line,
    "perpendicular_line": perpendicular_line,
    "intersection_point": intersection_point,
}


def register_draft_tools(registry: Registry[Style]) -> None:
    for name, factory in DRAFT_TOOLS.items():
        registry.register(name, factory)
