"""Piece marks: internal lines, notches anchored on outline segments, drill holes and labels (PM-01)."""

from dataclasses import dataclass

from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import AnnotationId, SegmentId
from app.domain.pattern.point import is_real, quantize, require_finite, require_point

MIN_LINE_POINTS = 2


@dataclass(frozen=True)
class InternalLine:
    id: AnnotationId
    points: tuple[Point2D, ...]

    def __post_init__(self) -> None:
        points = tuple(self.points)
        if len(points) < MIN_LINE_POINTS:
            raise ValueError(f"Internal line {self.id} needs at least two points")
        object.__setattr__(
            self, "points", tuple(require_point(p, f"Internal line {self.id}") for p in points)
        )


@dataclass(frozen=True)
class Notch:
    """A notch sits on an outline segment at the segment's own curve parameter t (0 = start, 1 = end).

    t is the curve parameter, not a fraction of arc length: on a Bézier the two differ, and the parameter
    is what stays attached to the same place when the end points are graded.
    """

    id: AnnotationId
    segment: SegmentId
    t: float

    def __post_init__(self) -> None:
        if not is_real(self.t) or not 0 <= quantize(self.t) <= 1:
            raise ValueError(f"Notch {self.id} needs a segment parameter t between 0 and 1")
        object.__setattr__(self, "t", quantize(self.t))


@dataclass(frozen=True)
class DrillHole:
    id: AnnotationId
    position: Point2D
    diameter: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", require_point(self.position, f"Drill hole {self.id}"))
        if not is_real(self.diameter) or quantize(self.diameter) <= 0:
            raise ValueError(f"Drill hole {self.id} needs a positive diameter")
        object.__setattr__(self, "diameter", quantize(self.diameter))


@dataclass(frozen=True)
class Label:
    id: AnnotationId
    text: str
    position: Point2D
    rotation_degrees: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError(f"Label {self.id} needs text")
        object.__setattr__(self, "position", require_point(self.position, f"Label {self.id}"))
        require_finite(self.rotation_degrees, what=f"Label {self.id} rotation")
        object.__setattr__(self, "rotation_degrees", quantize(self.rotation_degrees))
