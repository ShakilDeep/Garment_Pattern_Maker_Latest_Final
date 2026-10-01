"""Pattern points: finite positions with a stable id and an optional grade-rule reference (PM-02)."""
from dataclasses import dataclass, replace
from math import isfinite

from app.domain.geom.primitives import Point2D
from app.domain.pattern.ids import GradeRuleId, PointId


def is_real(value: object) -> bool:
    """A finite int or float; bools, strings, NaN and infinities are not coordinates."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def require_finite(*values: object, what: str) -> None:
    if not all(is_real(value) for value in values):
        raise ValueError(f"{what} must use finite numbers")


def finite_point(x: object, y: object) -> Point2D:
    require_finite(x, y, what="Pattern coordinates")
    return Point2D(float(x), float(y))  # type: ignore[arg-type]


def require_point(point: object, what: str) -> None:
    if not isinstance(point, Point2D):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"{what} must be a Point2D")  # noqa: TRY004
    require_finite(point.x, point.y, what=what)


@dataclass(frozen=True)
class PatternPoint:
    id: PointId
    position: Point2D
    grade_rule: GradeRuleId | None = None

    def __post_init__(self) -> None:
        require_point(self.position, f"Point {self.id}")

    def moved_to(self, x: object, y: object) -> "PatternPoint":
        return replace(self, position=finite_point(x, y))
