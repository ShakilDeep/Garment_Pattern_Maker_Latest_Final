"""Adapter: one V6 piece -> the V5 piece dict (T141b).

`points` is the sew line (curves sampled) and `cut_points` the validated per-edge cut line, both closed
rings opened across the fold for a piece cut on the fold, as V5 draws them. Coordinates are moved so the sew line starts
at (0, 0), as V5 `make_piece` does, and quantized to the model's 1e-6 cm. Nothing is invented: the
grainline, notches and quantity are the piece's own.
"""
from app.domain.geom.primitives import Point2D
from app.domain.pattern.edges import stitch_ring
from app.domain.pattern.notch_position import notch_position
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import quantize
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.legacy_outline import derived_metrics
from app.infrastructure.piece_validity import check_cut_geometry
from app.infrastructure.v5_view.unfold import mirrored, unfold_ring

Ring = list[Point2D]


def _opened(piece: Piece, sew: Ring, cut: Ring, notches: Ring) -> tuple[Ring, Ring, Ring]:
    if piece.fold is None:
        return sew, cut, notches
    positions = {point.id: point.position for point in piece.points}
    edge = next(segment for segment in piece.outline if segment.id == piece.fold.segment)
    start, end = positions[edge.start], positions[edge.end]
    return unfold_ring(sew, start, end), unfold_ring(cut, start, end), mirrored(notches, start, end)


def piece_view(piece: Piece, allowance: SeamAllowance) -> dict:
    notches = [notch_position(piece, notch) for notch in piece.notches]
    sew, cut, marks = _opened(piece, list(stitch_ring(piece)), list(check_cut_geometry(piece, allowance)), notches)
    left, top = min(p.x for p in sew), min(p.y for p in sew)

    def xy(point: Point2D) -> list[float]:
        return [quantize(point.x - left), quantize(point.y - top)]

    points = [xy(point) for point in (*sew, sew[0])]  # V5 rings are closed: the first point repeats
    grain = piece.grainline
    return {
        "id": piece.id.value, "name": piece.name, "points": points,
        "cut_points": [xy(point) for point in (*cut, cut[0])], "notches": [xy(point) for point in marks],
        "grainline": None if grain is None else [xy(grain.start), xy(grain.end)],
        "quantity": piece.cut.total, "cut_on_fold": piece.fold is not None,
        **{key: quantize(value) for key, value in derived_metrics(points).items()},
    }
