"""V6 style commands (PM-05). P1-08 onwards adds the drafting, modifying and garment tools here.

Parameters are checked when a command is created (400 on a bad value); an unknown size, piece or point is
found only when the command is applied (KeyError, 404).
"""

from dataclasses import dataclass, field

from app.application.cad.command import Params, require_params
from app.application.cad.registry import Registry
from app.application.cad.tools_draft import register_draft_tools
from app.application.cad.tools_garment import register_garment_tools
from app.application.cad.tools_modify import register_modify_tools
from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.point import require_finite
from app.domain.pattern.seam import SeamAllowance
from app.domain.pattern.style import Style

MOVE_POINT_PARAMS = ("size", "piece_id", "point_id", "x", "y")
ALLOWANCE_PARAMS = ("piece_id", "default_width", "edge_widths", "corner_styles")


@dataclass(frozen=True)
class MovePoint:
    """Move one point of one size's piece. Its id is kept (PM-02); marks in absolute cm do not follow."""

    size: str
    piece_id: PieceId
    point_id: PointId
    x: float
    y: float
    name: str = field(default="move_point", init=False)

    def apply(self, state: Style) -> Style:
        pieces = state.view(self.size)
        target = next((piece for piece in pieces if piece.id == self.piece_id), None)
        if target is None:
            raise KeyError(f"Unknown piece {self.piece_id}")
        return state.with_piece(self.size, target.move_point(self.point_id, self.x, self.y))


@dataclass(frozen=True)
class SetSeamAllowance:
    """Set one piece's seam allowance (PM-03); it applies to every size of the style."""

    piece_id: PieceId
    allowance: SeamAllowance
    name: str = field(default="set_seam_allowance", init=False)

    def apply(self, state: Style) -> Style:
        return state.with_allowance(self.piece_id, self.allowance)


def _keyed(value: object, what: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{what} must be an object keyed by id")  # noqa: TRY004 - ValueError maps to 400
    return value


def set_seam_allowance(params: Params) -> SetSeamAllowance:
    require_params(params, ALLOWANCE_PARAMS)
    edges = _keyed(params["edge_widths"], "Edge widths")
    corners = _keyed(params["corner_styles"], "Corner styles")
    allowance = SeamAllowance(
        params["default_width"],  # type: ignore[arg-type]
        tuple((SegmentId(key), width) for key, width in edges.items()),
        tuple((PointId(key), style) for key, style in corners.items()),
    )
    return SetSeamAllowance(PieceId(params["piece_id"]), allowance)  # type: ignore[arg-type]  # checked by PieceId


def move_point(params: Params) -> MovePoint:
    require_params(params, MOVE_POINT_PARAMS)
    size, x, y = params["size"], params["x"], params["y"]
    if not isinstance(size, str):
        raise ValueError("The size must be a size label")  # noqa: TRY004 - the API maps ValueError to 400
    require_finite(x, y, what="Point coordinates")
    return MovePoint(size, PieceId(params["piece_id"]), PointId(params["point_id"]), x, y)  # type: ignore[arg-type]


def style_registry() -> Registry[Style]:
    registry: Registry[Style] = Registry()
    registry.register("move_point", move_point)
    registry.register("set_seam_allowance", set_seam_allowance)
    register_draft_tools(registry)
    register_modify_tools(registry)
    register_garment_tools(registry)
    return registry
