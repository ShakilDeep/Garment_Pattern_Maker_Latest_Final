"""Corner styles (PM-03): one Strategy per style joins edge A's cut line (in) to edge B's (out) at a corner.

Definitions approved by the user on 2026-10-02 (doc 108); A and B follow the stored outline order:
- mitre: the two cut lines extend until they meet.
- square: each cut line extends past the corner by the other edge's allowance and a straight edge joins
  them (a box corner); at obtuse corners the lines meet before that and stop there, as a mitre.
- fold_back: A's allowance end is A's mirror image of B's cut line (a hem turned up along A lies on B').
- reverse: B's allowance end is B's mirror image of A's cut line (B folded back along B lies on A').
Cut lines are only ever extended: where meeting would shorten one into its neighbour's band the corner
steps between the two cut-line ends (fold-back and reverse fall back to the mitre). Inside corners run both
cut lines back to the corner for the cut envelope to trim; corners beside the fold end on the fold line.
"""

from collections.abc import Callable
from enum import Enum
from math import radians, sin

from app.domain.geom.lines import cross, intersect, reflect, reflect_direction
from app.domain.geom.primitives import Point2D
from app.domain.pattern.corner_join import CornerJoin
from app.domain.tolerances import ANGLE_DEGREES

# Edges turning by less than the project angle tolerance are a straight continuation (a step, not a mitre).
TURN = sin(radians(ANGLE_DEGREES))


class CornerStyle(str, Enum):
    MITRE = "mitre"
    SQUARE = "square"
    REVERSE = "reverse"
    FOLD_BACK = "fold_back"


def _mitre(join: CornerJoin) -> tuple[Point2D, ...]:
    met = join.meet()
    if met is None or min(join.reaches(met)) < 0:
        return join.step()
    return (met,)


def _square(join: CornerJoin) -> tuple[Point2D, ...]:
    met = join.meet()
    if met is None or min(join.reaches(met)) < 0:
        return join.step()
    a_reach, b_reach = join.reaches(met)
    if a_reach <= join.out_width or b_reach <= join.in_width:
        return (met,)
    return join.boxed()


def _fold_back(join: CornerJoin) -> tuple[Point2D, ...]:
    mirror_start = reflect(join.out_start, join.vertex, join.in_dir)
    mirror_dir = reflect_direction(join.out_dir, join.in_dir)
    hem_end = intersect(join.in_end, join.in_dir, mirror_start, mirror_dir)
    on_axis = intersect(join.out_start, join.out_dir, join.vertex, join.in_dir)
    if hem_end is None or on_axis is None or join.reaches(on_axis)[1] < 0:  # B' would be shortened
        return _mitre(join)
    return (hem_end, on_axis)


def _reverse(join: CornerJoin) -> tuple[Point2D, ...]:
    mirror_end = reflect(join.in_end, join.vertex, join.out_dir)
    mirror_dir = reflect_direction(join.in_dir, join.out_dir)
    on_axis = intersect(join.in_end, join.in_dir, join.vertex, join.out_dir)
    side_start = intersect(join.out_start, join.out_dir, mirror_end, mirror_dir)
    if on_axis is None or side_start is None or join.reaches(on_axis)[0] < 0:  # A' would be shortened
        return _mitre(join)
    return (on_axis, side_start)


STRATEGIES: dict[CornerStyle, Callable[[CornerJoin], tuple[Point2D, ...]]] = {
    CornerStyle.MITRE: _mitre,
    CornerStyle.SQUARE: _square,
    CornerStyle.REVERSE: _reverse,
    CornerStyle.FOLD_BACK: _fold_back,
}


def join_fold(join: CornerJoin, orientation: int) -> tuple[Point2D, ...]:
    """A corner beside the fold edge ends on the fold line whatever its style, so the fold stays straight."""
    if cross(join.in_dir, join.out_dir) * orientation < 0:
        return join.through_vertex()
    met = join.meet()
    return join.step() if met is None else (met,)


def join_corner(join: CornerJoin, style: CornerStyle, orientation: int) -> tuple[Point2D, ...]:
    """Cut-outline points at a corner; orientation is +1 for a counter-clockwise outline, -1 for clockwise."""
    turn = cross(join.in_dir, join.out_dir)
    ahead = join.in_dir.x * join.out_dir.x + join.in_dir.y * join.out_dir.y
    if abs(turn) <= TURN and ahead < 0:
        raise ValueError(
            f"The outline doubles back on itself at {join.vertex}; a needle point takes no allowance"
        )
    if abs(turn) <= TURN:
        return join.step()
    if turn * orientation < 0:
        return join.through_vertex()
    return STRATEGIES[style](join)
