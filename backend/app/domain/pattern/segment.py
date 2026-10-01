"""Boundary segments between pattern points, referenced by point id: line, cubic Bézier and arc (PM-01).

Every shape parameter is relative to the segment's own end points, so moving or grading a point (by id)
carries the segment with it and the segment stays valid.
"""

from dataclasses import dataclass

from app.domain.geom.primitives import Vector2D
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.point import quantize, require_finite, require_vector

# |bulge| = 1000 is an arc of about 359.5 degrees; larger values overflow when the arc is resolved.
MAX_BULGE = 1000.0


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
        for name in ("start_handle", "end_handle"):
            handle = require_vector(getattr(self, name), f"Curve {self.id} handles")
            object.__setattr__(self, name, handle)


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
        object.__setattr__(self, "bulge", quantize(self.bulge))
        if abs(self.bulge) > MAX_BULGE:
            raise ValueError(
                f"Arc {self.id} bulge must be at most {MAX_BULGE:g} in size (an almost full circle)"
            )
        if self.bulge == 0:
            raise ValueError(f"Arc {self.id} needs a non-zero bulge; use a Line for a straight edge")


Segment = Line | CubicBezier | Arc
