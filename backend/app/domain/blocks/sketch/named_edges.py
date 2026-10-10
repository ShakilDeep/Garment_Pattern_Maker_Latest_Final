"""Walk a piece's outline by named points: edge lookup, seam lengths and seam gaps for truing (T129).

Edge lengths come from ``pattern.measure.segment_length`` (curves measured densely, see there).
"""
from collections.abc import Sequence
from itertools import pairwise

from app.domain.blocks.sketch.naming import segment_id
from app.domain.pattern.measure import segment_length
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Segment

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
    return sum(segment_length(piece, edge(piece, start, end)) for start, end in pairwise(names))


def seam_gap(first: SeamPath, second: SeamPath) -> float:
    """first length - second length: 0 for seams that sew together evenly."""
    return path_length(*first) - path_length(*second)
