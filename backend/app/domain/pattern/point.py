"""Pattern points: finite positions with a stable id and an optional grade-rule reference (PM-02).

Every stored number is quantized to the coordinate tolerance on construction, so a piece in memory equals its
serialized (Memento) form exactly and every invariant sees the same values before and after a round trip.
"""

from dataclasses import dataclass, replace
from math import isfinite

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.ids import GradeRuleId, PointId
from app.domain.tolerances import MODEL_DECIMALS


def is_real(value: object) -> bool:
    """A finite int or float; bools, strings, NaN, infinities and overflow-sized ints are not coordinates."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def require_finite(*values: object, what: str) -> None:
    if not all(is_real(value) for value in values):
        raise ValueError(f"{what} must use finite numbers")


def quantize(value: float, decimals: int = MODEL_DECIMALS) -> float:
    """Canonical number: rounded (1e-6 cm by default); -0.0 folds into 0.0 so serialized text is stable."""
    return round(float(value), decimals) + 0.0


def finite_point(x: object, y: object) -> Point2D:
    require_finite(x, y, what="Pattern coordinates")
    return Point2D(quantize(x), quantize(y))  # type: ignore[arg-type]


def require_point(point: object, what: str) -> Point2D:
    """Validate a Point2D and return its quantized form."""
    if not isinstance(point, Point2D):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"{what} must be a Point2D")  # noqa: TRY004
    require_finite(point.x, point.y, what=what)
    return Point2D(quantize(point.x), quantize(point.y))


def require_vector(vector: object, what: str) -> Vector2D:
    """Validate a Vector2D and return its quantized form."""
    if not isinstance(vector, Vector2D):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError(f"{what} must be a Vector2D offset")  # noqa: TRY004
    require_finite(vector.x, vector.y, what=what)
    return Vector2D(quantize(vector.x), quantize(vector.y))


@dataclass(frozen=True)
class PatternPoint:
    id: PointId
    position: Point2D
    grade_rule: GradeRuleId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "position", require_point(self.position, f"Point {self.id}"))
        if self.grade_rule is not None and not isinstance(self.grade_rule, GradeRuleId):
            raise ValueError(f"Point {self.id} grade rule must be a GradeRuleId or None")

    def moved_to(self, x: object, y: object) -> "PatternPoint":
        return replace(self, position=finite_point(x, y))
