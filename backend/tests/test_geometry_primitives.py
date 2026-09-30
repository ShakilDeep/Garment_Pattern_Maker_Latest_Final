from math import pi

import pytest

from app.domain.geometry import (
    Arc,
    BoundingBox,
    ClosedPath,
    CubicBezier,
    LineSegment,
    Point2D,
    Polyline,
    Transform2D,
    Vector2D,
)
from app.domain.tolerances import CURVE_STEPS


def test_primitives_sample_transform_and_serialize_deterministically():
    a, b = Point2D(0, 0), Point2D(3, 4)
    assert Vector2D.between(a, b).length == 5
    assert LineSegment(a, b).length == 5
    assert Polyline((a, b)).to_data() == [[0, 0], [3, 4]]
    assert BoundingBox.from_points((a, b)).width == 3
    assert Transform2D.translation(2, 1).apply(a) == Point2D(2, 1)
    assert Arc(a, 2, 0, pi).sample(2)[1].y == pytest.approx(2)
    assert ClosedPath((a, Point2D(2, 0), Point2D(0, 2))).to_data()[-1] == [0, 0]
    curve = CubicBezier(a, Point2D(1, 0), Point2D(2, 4), b)
    assert curve.sample(4)[0] == a and curve.sample(4)[-1] == b
    assert len(curve.sample()) == CURVE_STEPS + 1
    arc = Arc(Point2D(0, 0), 2, 0, pi)
    assert arc.sample(2)[1].y == pytest.approx(2)
    moved = Transform2D.translation(2, 3).apply(b)
    assert moved == Point2D(5, 7)


def test_closed_path_and_bounds_reject_invalid_shape():
    path = ClosedPath((Point2D(0, 0), Point2D(2, 0), Point2D(2, 1), Point2D(0, 1)))
    assert path.points[0] == path.points[-1]
    assert path.bounds == BoundingBox(0, 0, 2, 1)
    with pytest.raises(ValueError):
        ClosedPath((Point2D(0, 0), Point2D(1, 0)))
