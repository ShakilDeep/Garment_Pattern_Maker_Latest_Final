"""Shared fixture for the P1-10 garment tool tests: a two-size bodice block and seam-length measurement."""

from itertools import pairwise

from app.application.cad.history import History
from app.domain.geom.primitives import LineSegment, Point2D, Vector2D
from app.domain.pattern.annotation import Label, Notch
from app.domain.pattern.cutting import CutQuantity, Grainline
from app.domain.pattern.ids import AnnotationId, PieceId, PointId, SegmentId, StyleId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import CubicBezier, Line
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style

DENSE = 4000
CORNERS = {"a": (0, 0), "b": (40, 0), "c": (40, 50), "d": (0, 50)}


def bodice(scale=1.0):
    points = tuple(PatternPoint(PointId(k), Point2D(x * scale, y * scale)) for k, (x, y) in CORNERS.items())
    top = CubicBezier(SegmentId("s3"), PointId("c"), PointId("d"), Vector2D(-10, 4), Vector2D(10, 4))
    outline = (Line(SegmentId("s1"), PointId("a"), PointId("b")), Line(SegmentId("s2"), PointId("b"), PointId("c")),
               top, Line(SegmentId("s4"), PointId("d"), PointId("a")))
    return Piece(PieceId("bodice"), "Bodice", points, outline, CutQuantity(1, 0, 0),
                 grainline=Grainline(Point2D(5, 10), Point2D(5, 40)),
                 notches=(Notch(AnnotationId("n1"), SegmentId("s2"), 0.2),),
                 labels=(Label(AnnotationId("l1"), "Bodice", Point2D(8, 30)),))


def bodice_style():
    sizes = {"S": SizePieces.from_pieces((bodice(0.9),)), "M": SizePieces.from_pieces((bodice(),))}
    return Style(StyleId("block"), "Block", ("S", "M"), "M", sizes)


def run(bus, style, command, **params):
    return bus.dispatch(style, History(), command, {"piece_id": "bodice", **params})[0]


def piece_of(style, size="M"):
    return style.view(size)[0]


def segment_length(piece, segment):
    curve = resolve_segment(segment, {p.id: p.position for p in piece.points})
    points = (curve.start, curve.end) if isinstance(curve, LineSegment) else curve.sample(DENSE)
    return sum(Vector2D.between(p, q).length for p, q in pairwise(points))


def seam_length(piece, skip=()):
    """Outline length in cm, leaving out the named segments (dart legs are not seams)."""
    return sum(segment_length(piece, s) for s in piece.outline if str(s.id) not in skip)


def position(piece, point):
    return piece.point(PointId(point)).position


def distance(first, second=None):
    """Distance between two points, or along a two-point mark given as one tuple."""
    first, second = (first, second) if second is not None else first
    return Vector2D.between(first, second).length
