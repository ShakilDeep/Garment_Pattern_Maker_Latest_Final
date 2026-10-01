"""Boundary segments between pattern points, referenced by point id: line, cubic Bézier and arc (PM-01).

Every shape parameter is relative to the segment's own end points, so moving or grading a point (by id)
carries the segment with it and the segment stays valid.
"""
from dataclasses import dataclass

from app.domain.geom.primitives import Vector2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.point import require_finite


def _require_distinct(segment: "Line | CubicBezier | Arc") -> None:
    if segment.start == segment.end:
        raise ValueError(f"Segment {segment.id} needs distinct start and end points")


@dataclass(frozen=True)
class Line:
    id: SegmentId
    start: PointId
    end: PointId

    def __post_init__(self) -> None:
        _require_distinct(self)


@dataclass(frozen=True)
class CubicBezier:
    """Handles are offsets from their own end point: start + start_handle, end + end_handle."""

    id: SegmentId
    start: PointId
    end: PointId
    start_handle: Vector2D
    end_handle: Vector2D

    def __post_init__(self) -> None:
        _require_distinct(self)
        for handle in (self.start_handle, self.end_handle):
            if not isinstance(handle, Vector2D):
                # ValueError, not TypeError: the API maps ValueError to 400.
                raise ValueError(f"Curve {self.id} handles must be Vector2D offsets")  # noqa: TRY004
            require_finite(handle.x, handle.y, what=f"Curve {self.id} handles")


@dataclass(frozen=True)
class Arc:
    """Circular arc as a DXF bulge.

    bulge = tan(included angle / 4); positive turns counter-clockwise and 1 is a half circle.
    """

    id: SegmentId
    start: PointId
    end: PointId
    bulge: float

    def __post_init__(self) -> None:
        _require_distinct(self)
        require_finite(self.bulge, what=f"Arc {self.id} bulge")
        if self.bulge == 0:
            raise ValueError(f"Arc {self.id} needs a non-zero bulge; use a Line for a straight edge")


Segment = Line | CubicBezier | Arc
