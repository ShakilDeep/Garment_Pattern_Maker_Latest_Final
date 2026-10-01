"""Memento codecs for points and segments. The model stores quantized values, so encoding is exact."""

from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.ids import GradeRuleId, PointId, SegmentId
from app.domain.pattern.point import PatternPoint, finite_point, quantize
from app.domain.pattern.segment import Arc, CubicBezier, Line, Segment

PAIR_LENGTH = 2


def xy(value: Point2D | Vector2D) -> list[float]:
    return [quantize(value.x), quantize(value.y)]


def pair_of(value: object) -> list:
    if not isinstance(value, list) or len(value) != PAIR_LENGTH:
        raise ValueError(f"Invalid pattern data: expected an [x, y] pair, got {value!r}")
    return value


def point_at(value: object) -> Point2D:
    x, y = pair_of(value)
    return finite_point(x, y)


def vector_at(value: object) -> Vector2D:
    point = point_at(value)
    return Vector2D(point.x, point.y)


def encode_point(point: PatternPoint) -> dict:
    x, y = xy(point.position)
    rule = None if point.grade_rule is None else str(point.grade_rule)
    return {"id": str(point.id), "x": x, "y": y, "grade_rule": rule}


def decode_point(data: dict) -> PatternPoint:
    rule = data["grade_rule"]
    grade_rule = None if rule is None else GradeRuleId(rule)
    return PatternPoint(PointId(data["id"]), finite_point(data["x"], data["y"]), grade_rule)


def encode_segment(segment: Segment) -> dict:
    ends = {"id": str(segment.id), "start": str(segment.start), "end": str(segment.end)}
    if isinstance(segment, Line):
        return {"type": "line", **ends}
    if isinstance(segment, CubicBezier):
        handles = {"start_handle": xy(segment.start_handle), "end_handle": xy(segment.end_handle)}
        return {"type": "cubic", **ends, **handles}
    return {"type": "arc", **ends, "bulge": quantize(segment.bulge)}


def decode_segment(data: dict) -> Segment:
    ids = (SegmentId(data["id"]), PointId(data["start"]), PointId(data["end"]))
    if data["type"] == "line":
        return Line(*ids)
    if data["type"] == "cubic":
        return CubicBezier(*ids, vector_at(data["start_handle"]), vector_at(data["end_handle"]))
    if data["type"] == "arc":
        return Arc(*ids, data["bulge"])
    raise ValueError(f"Unknown segment type {data['type']!r}")
