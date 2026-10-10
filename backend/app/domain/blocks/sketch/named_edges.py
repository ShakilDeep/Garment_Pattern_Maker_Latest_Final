"""Walk a piece's outline by named points: edge lookup, seam lengths and seam gaps for truing (T129).

Curves are measured on a dense sampling (LENGTH_STEPS), not the 24-step display sampling: on the 1078375
front armhole and sleeve cap the display polyline is 0.005-0.007 cm short per curve, which a seam of several
curves would add into the 0.1 cm truing budget; at 2048 steps the shortfall is below 1e-5 cm.
"""
from collections.abc import Sequence
from itertools import pairwise

from app.domain.blocks.sketch.naming import segment_id
from app.domain.geom.polyline_ops import length
from app.domain.geom.primitives import LineSegment
from app.domain.pattern.piece import Piece
from app.domain.pattern.resolve import resolve_segment
from app.domain.pattern.segment import Segment

LENGTH_STEPS = 2048
MIN_PATH_POINTS = 2

SeamPath = tuple[Piece, Sequence[str]]


def edge(piece: Piece, start: str, end: str) -> Segment:
    """The outline segment drawn from ``start`` to ``end`` (outline order); KeyError when there is none."""
    wanted = segment_id(start, end)
    found = next((segment for segment in piece.outline if segment.id == wanted), None)
    if found is None:
        raise KeyError(f"No edge {start} to {end} on {piece.name}")
    return found


def path_length(piece: Piece, names: Sequence[str]) -> float:
    """Length of the outline walked through consecutive named points, e.g. ("UA", "SP") for an armhole."""
    if len(names) < MIN_PATH_POINTS:
        raise ValueError("A seam path needs at least two named points")
    positions = {point.id: point.position for point in piece.points}
    total = 0.0
    for start, end in pairwise(names):
        curve = resolve_segment(edge(piece, start, end), positions)
        if isinstance(curve, LineSegment):
            total += curve.length
        else:
            total += length([(p.x, p.y) for p in curve.sample(LENGTH_STEPS)])
    return total


def seam_gap(first: SeamPath, second: SeamPath) -> float:
    """first length - second length: 0 for seams that sew together evenly."""
    return path_length(*first) - path_length(*second)
