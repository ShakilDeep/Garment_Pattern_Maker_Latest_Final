"""Modify tools (CAD-02): one Command per tool, registered by name on the style command registry."""

from app.application.cad.registry import Factory, Registry
from app.application.cad.tools_modify.smooth import smooth_point
from app.application.cad.tools_modify.split_join import join_edges, split_edge_tool
from app.application.cad.tools_modify.transform import mirror_piece, move_piece, rotate_piece
from app.application.cad.tools_modify.trim_extend import extend_line, trim_line
from app.domain.pattern.style import Style

MODIFY_TOOLS: dict[str, Factory[Style]] = {
    "move_piece": move_piece,
    "rotate_piece": rotate_piece,
    "mirror_piece": mirror_piece,
    "split_edge": split_edge_tool,
    "join_edges": join_edges,
    "trim_line": trim_line,
    "extend_line": extend_line,
    "smooth_point": smooth_point,
}


def register_modify_tools(registry: Registry[Style]) -> None:
    for name, factory in MODIFY_TOOLS.items():
        registry.register(name, factory)
