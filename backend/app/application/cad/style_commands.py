"""V6 style commands (PM-05). P1-08 onwards adds the drafting, modifying and garment tools here.

Parameters are checked when a command is created (400 on a bad value); an unknown size, piece or point is
found only when the command is applied (KeyError, 404).
"""

from dataclasses import dataclass, field

from app.application.cad.command import Params, require_params
from app.application.cad.registry import Registry
from app.domain.pattern.ids import PieceId, PointId
from app.domain.pattern.point import require_finite
from app.domain.pattern.style import Style

MOVE_POINT_PARAMS = ("size", "piece_id", "point_id", "x", "y")


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
    return registry
