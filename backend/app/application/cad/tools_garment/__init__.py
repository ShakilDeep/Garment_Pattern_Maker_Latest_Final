"""Garment tools (CAD-03): one Command per tool, registered by name on the style command registry."""

from app.application.cad.registry import Factory, Registry
from app.application.cad.tools_garment.dart import close_dart_tool, create_dart_tool, rotate_dart_tool
from app.application.cad.tools_garment.fold import fold_piece, unfold_piece
from app.application.cad.tools_garment.pleat_tuck import pleat_tool, tuck_tool
from app.application.cad.tools_garment.slash_spread import add_fullness_tool, slash_spread_tool
from app.domain.pattern.style import Style

GARMENT_TOOLS: dict[str, Factory[Style]] = {
    "create_dart": create_dart_tool,
    "rotate_dart": rotate_dart_tool,
    "close_dart": close_dart_tool,
    "pleat": pleat_tool,
    "tuck": tuck_tool,
    "slash_spread": slash_spread_tool,
    "add_fullness": add_fullness_tool,
    "unfold_piece": unfold_piece,
    "fold_piece": fold_piece,
}


def register_garment_tools(registry: Registry[Style]) -> None:
    for name, factory in GARMENT_TOOLS.items():
        registry.register(name, factory)
