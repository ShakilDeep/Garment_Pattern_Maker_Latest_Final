"""Parameter readers shared by the garment tools (CAD-03); a bad value is a ValueError (400) naming it."""

from collections.abc import Callable

from app.application.cad.command import Params
from app.application.cad.tools_draft.params import number, positive, text
from app.domain.pattern.garment.allowance import followed
from app.domain.pattern.garment.names import Cut, SpreadNames
from app.domain.pattern.garment.spread import Spread
from app.domain.pattern.ids import PieceId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance

Follow = Callable[[SeamAllowance, Piece], SeamAllowance]
HALF_TURN_DEGREES = 180.0
SPREAD_PARAMS = ("piece_id", "from_segment", "from_t", "to_segment", "to_t", "slash_id")


def piece_id(params: Params) -> PieceId:
    return PieceId(text(params, "piece_id"))


def cut(params: Params, segment: str = "segment_id", t: str = "t") -> Cut:
    return Cut(SegmentId(text(params, segment)), number(params, t))


def spread_angle(params: Params, name: str) -> float:
    """A turn that opens a slash: past a half turn it would fold the part back over the rest."""
    value = number(params, name)
    if not 0 < value < HALF_TURN_DEGREES:
        raise ValueError(f"{name} must be more than 0 and less than {HALF_TURN_DEGREES:g} degrees")
    return value


def spread(params: Params, amount: str) -> Spread:
    return Spread(cut(params, "from_segment", "from_t"), cut(params, "to_segment", "to_t"), positive(params, amount))


def spread_follow(spreading: Spread, names: SpreadNames) -> Follow:
    sources = {names.e1: spreading.start.segment, names.b1: spreading.start.segment,
               names.e2: spreading.end.segment, names.b2: spreading.end.segment}

    def follow(allowance: SeamAllowance, _piece: Piece) -> SeamAllowance:
        return followed(allowance, sources)

    return follow
