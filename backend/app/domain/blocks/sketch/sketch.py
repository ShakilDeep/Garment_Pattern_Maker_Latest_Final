"""PieceSketch (Builder): a block draws a piece's outline point by named point, then builds a V6 ``Piece``.

Straight edges are ``Line``s and curves are cubic Béziers whose handles are offsets from their own end point
(as ``pattern.segment.CubicBezier`` stores them), so grading a named point carries its curves with it. Every
geometric rule stays in ``Piece`` itself; the sketch only adds the naming rules and drawing order.
"""
from dataclasses import dataclass

from app.domain.blocks.sketch.naming import point_name, segment_id
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.annotation import Notch
from app.domain.pattern.cutting import CutQuantity, FoldLine, Grainline
from app.domain.pattern.ids import AnnotationId, PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint, finite_point
from app.domain.pattern.segment import CubicBezier, Line, Segment

Handles = tuple[Vector2D, Vector2D]


@dataclass(frozen=True)
class PieceSpec:
    id: str
    name: str
    cut: CutQuantity


class PieceSketch:
    def __init__(self) -> None:
        self._points: list[PatternPoint] = []
        self._edges: list[Segment] = []
        self._notches: list[Notch] = []
        self._fold: FoldLine | None = None
        self._grain: Grainline | None = None
        self._closed = False

    def start(self, name: str, x: float, y: float) -> "PieceSketch":
        if self._points:
            raise ValueError("The outline has already started")
        self._points.append(PatternPoint(point_name(name), finite_point(x, y)))
        return self

    def line_to(self, name: str, x: float, y: float) -> "PieceSketch":
        return self._draw(name, (x, y), None)

    def curve_to(self, name: str, at: tuple[float, float], handles: Handles) -> "PieceSketch":
        """A cubic Bézier from the last point to ``at``: (offset from the last point, offset from ``at``)."""
        return self._draw(name, at, handles)

    def close(self, handles: Handles | None = None) -> "PieceSketch":
        self._require_open("Start the outline before closing it")
        self._edges.append(_edge(self._points[-1].id, self._points[0].id, handles))
        self._closed = True
        return self

    def notch(self, name: str, start: str, end: str, t: float) -> "PieceSketch":
        self._notches.append(Notch(AnnotationId(name), self._drawn(start, end), t))
        return self

    def fold(self, start: str, end: str) -> "PieceSketch":
        self._fold = FoldLine(self._drawn(start, end))
        return self

    def grain(self, start: Point2D, end: Point2D) -> "PieceSketch":
        self._grain = Grainline(start, end)
        return self

    def build(self, spec: PieceSpec) -> Piece:
        if not self._closed:
            raise ValueError(f"Close the outline of {spec.name} before building it")
        return Piece(PieceId(spec.id), spec.name, tuple(self._points), tuple(self._edges), spec.cut,
                     self._grain, self._fold, notches=tuple(self._notches))

    def _draw(self, name: str, at: tuple[float, float], handles: Handles | None) -> "PieceSketch":
        self._require_open(f"Start the outline before drawing to {name}")
        point = PatternPoint(point_name(name), finite_point(*at))
        if any(drawn.id == point.id for drawn in self._points):
            raise ValueError(f"Point {name} is already drawn")
        self._edges.append(_edge(self._points[-1].id, point.id, handles))
        self._points.append(point)
        return self

    def _require_open(self, not_started: str) -> None:
        if not self._points:
            raise ValueError(not_started)
        if self._closed:
            raise ValueError("The outline is closed")

    def _drawn(self, start: str, end: str) -> SegmentId:
        wanted = segment_id(start, end)
        if not any(edge.id == wanted for edge in self._edges):
            raise ValueError(f"No edge {start} to {end} in this sketch")
        return wanted


def _edge(start: PointId, end: PointId, handles: Handles | None) -> Segment:
    ident = segment_id(str(start), str(end))
    return Line(ident, start, end) if handles is None else CubicBezier(ident, start, end, *handles)
