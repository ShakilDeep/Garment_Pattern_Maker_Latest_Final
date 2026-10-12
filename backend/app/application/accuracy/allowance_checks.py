"""Cut line = sew line + per-edge allowance (spec §7 Finishing): each edge within 0.05 cm of its finishing width.

The cut line is built from the style's own allowances (a CAD edit included); the width it must show is the
block's finishing.json value, measured from the client PDS. As for the PDS itself (``pds/edges.py``), an edge's
offset is the median distance from points on its inner 70 % to the cut line, clear of the corner joins.
"""
from collections.abc import Callable, Mapping, Sequence
from statistics import median

import shapely
from shapely.geometry import LineString

from app.application.accuracy.model import Check, Source
from app.domain.pattern.edges import edge_polylines
from app.domain.pattern.ids import PieceId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.piece_validity import check_cut_geometry

ALLOWANCE_CM = 0.05  # spec §7: cut line = sew line + per-edge value within 0.05 cm
SAMPLES, INNER_START, INNER_END = 15, 0.15, 0.85  # the PDS measurement's samples (infrastructure/pds/edges.py)
FINISHING = Source("pds", "finishing.json: per-edge allowance measured from the client PDS")


def _offset(edge: LineString, cut: LineString) -> float:
    step = (INNER_END - INNER_START) / (SAMPLES - 1)
    samples = shapely.line_interpolate_point(edge, [INNER_START + i * step for i in range(SAMPLES)], normalized=True)
    return float(median(shapely.distance(cut, samples)))


def _piece_checks(piece: Piece, actual: SeamAllowance, expected: SeamAllowance) -> list[Check]:
    ring = check_cut_geometry(piece, actual)
    cut = LineString([(p.x, p.y) for p in (*ring, ring[0])])
    fold = None if piece.fold is None else piece.fold.segment
    checks = []
    for segment, polyline in zip(piece.outline, edge_polylines(piece), strict=True):
        if segment.id == fold:
            continue
        width, edge = expected.width_of(segment.id), f"{segment.start}:{segment.end}"
        offset = _offset(LineString([(p.x, p.y) for p in polyline]), cut)
        checks.append(Check(f"{piece.name} {edge} allowance", offset, f"{width:.3f} ± {ALLOWANCE_CM} cm",
                            abs(offset - width) <= ALLOWANCE_CM, FINISHING, piece=piece.name, edge=edge))
    return checks


def allowance_checks(pieces: Sequence[Piece], actual: Mapping[PieceId, SeamAllowance],
                     expected: Callable[[str], SeamAllowance]) -> list[Check]:
    """Every non-fold edge of ``pieces``: cut with ``actual``, checked against ``expected`` (the block's widths)."""
    return [check for piece in pieces for check in _piece_checks(piece, actual[piece.id], expected(str(piece.id)))]
