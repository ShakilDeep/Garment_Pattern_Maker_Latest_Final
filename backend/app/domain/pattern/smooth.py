"""Smooth (CAD-02): make the outline tangent-continuous (G1) at a point by turning the Bézier handles there.

A line or arc meeting the point keeps its direction, and the curve's handle aligns to it; where two curves
meet, both handles align to the bisector of their tangents. Handle lengths are kept, so only the angles
change.
"""

from dataclasses import replace

from app.domain.geom.lines import unit
from app.domain.geom.primitives import Vector2D
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import CubicBezier, Segment
from app.domain.pattern.tangents import end_tangents
from app.domain.tolerances import COORDINATE


def _scaled(direction: Vector2D, length: float) -> Vector2D:
    return Vector2D(direction.x * length, direction.y * length)


def _joint_direction(incoming: Segment, outgoing: Segment, piece: Piece) -> Vector2D:
    positions = {p.id: p.position for p in piece.points}

    def tangents(segment: Segment) -> tuple[Vector2D, Vector2D]:
        curve = resolve_segment(segment, positions)
        return end_tangents(curve, positions[segment.start], positions[segment.end])

    arriving, leaving = tangents(incoming)[1], tangents(outgoing)[0]
    if not isinstance(incoming, CubicBezier):
        return arriving
    if not isinstance(outgoing, CubicBezier):
        return leaving
    middle = Vector2D(arriving.x + leaving.x, arriving.y + leaving.y)
    if middle.length <= COORDINATE:
        raise ValueError("The outline turns straight back at this point, so it cannot be smoothed")
    return unit(middle)


def smooth_at(piece: Piece, point_id: PointId) -> Piece:
    piece.point(point_id)
    incoming = next((s for s in piece.outline if s.end == point_id), None)
    outgoing = next((s for s in piece.outline if s.start == point_id), None)
    if incoming is None or outgoing is None:
        raise ValueError(f"Point {point_id} is not on the outline")
    if not isinstance(incoming, CubicBezier) and not isinstance(outgoing, CubicBezier):
        # ValueError, not TypeError: the API maps ValueError to 400.
        message = f"Smoothing needs a curve at point {point_id}; both edges there are straight or arcs"
        raise ValueError(message)  # noqa: TRY004
    flat = [s.id for s, handle in ((incoming, "end_handle"), (outgoing, "start_handle"))
            if isinstance(s, CubicBezier) and getattr(s, handle).length <= COORDINATE]
    if flat:
        raise ValueError(f"Curve {flat[0]} has no handle at point {point_id}; give it one before smoothing")
    direction = _joint_direction(incoming, outgoing, piece)

    def smoothed(segment: Segment) -> Segment:
        if segment == incoming and isinstance(segment, CubicBezier):
            segment = replace(segment, end_handle=_scaled(direction, -segment.end_handle.length))
        if segment == outgoing and isinstance(segment, CubicBezier):
            segment = replace(segment, start_handle=_scaled(direction, segment.start_handle.length))
        return segment

    return replace(piece, outline=tuple(smoothed(s) for s in piece.outline))
