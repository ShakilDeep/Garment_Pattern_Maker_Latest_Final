"""The geometry at one corner V, where edge A's cut line (in) meets edge B's (out)."""

from dataclasses import dataclass

from app.domain.geom.lines import along, intersect
from app.domain.geom.primitives import Point2D, Vector2D


def _ahead(start: Point2D, end: Point2D, direction: Vector2D) -> bool:
    gap = Vector2D.between(start, end)
    return gap.x * direction.x + gap.y * direction.y > 0


@dataclass(frozen=True)
class CornerJoin:
    """A corner V: unit edge tangents at V, the cut-line points opposite V, and the two allowance widths."""

    vertex: Point2D
    in_dir: Vector2D
    out_dir: Vector2D
    in_end: Point2D
    out_start: Point2D
    in_width: float
    out_width: float

    def meet(self) -> Point2D | None:
        return intersect(self.in_end, self.in_dir, self.out_start, self.out_dir)

    def reaches(self, met: Point2D) -> tuple[float, float]:
        """How far A' runs past its end and B' starts before its start to reach the meeting point."""
        past_a, before_b = Vector2D.between(self.in_end, met), Vector2D.between(met, self.out_start)
        return (
            past_a.x * self.in_dir.x + past_a.y * self.in_dir.y,
            before_b.x * self.out_dir.x + before_b.y * self.out_dir.y,
        )

    def step(self) -> tuple[Point2D, ...]:
        """Keep each edge's full allowance and join the two cut-line ends directly."""
        return (self.in_end, self.out_start)

    def through_vertex(self) -> tuple[Point2D, ...]:
        """An inside corner: both cut lines run back to V; the cut envelope keeps where the bands overlap."""
        return (self.in_end, self.vertex, self.out_start)

    def framed(self, points: tuple[Point2D, ...], curved: tuple[bool, bool]) -> tuple[Point2D, ...]:
        """Pass through the cut-line end points beside a curved edge, wherever that runs forwards.

        They lie on the tangent cut lines, so the shape is unchanged; the cut then meets the curve's own
        offset exactly at the corner instead of cutting straight across to the first sampled join.
        """
        lead = curved[0] and _ahead(self.in_end, points[0], self.in_dir)
        tail = curved[1] and _ahead(points[-1], self.out_start, self.out_dir)
        return (*((self.in_end,) if lead else ()), *points, *((self.out_start,) if tail else ()))

    def boxed(self) -> tuple[Point2D, ...]:
        past_a = along(self.in_end, self.in_dir, self.out_width)
        before_b = along(self.out_start, self.out_dir, -self.in_width)
        return (past_a, before_b)
