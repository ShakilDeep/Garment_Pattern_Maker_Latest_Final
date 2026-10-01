"""What a V5 piece dict cannot hold: export refuses such pieces instead of silently dropping or changing data."""

from app.domain.pattern.cutting import Grainline
from app.domain.pattern.piece import Piece
from app.domain.pattern.segment import Line


def _unsupported(piece: Piece) -> list[str]:
    outline_ids = {i for s in piece.outline for i in (s.start, s.end)}
    checks = [
        (piece.fold is not None or piece.cut.on_fold > 0, "a fold edge (V5 outlines are unfolded)"),
        (piece.cut.mirrored_pairs > 0, "mirrored pairs (V5 has no mirror flag)"),
        (not all(isinstance(s, Line) for s in piece.outline), "curved segments (they need sampling first)"),
        (piece.grainline is None, "a missing grainline"),
        (bool(piece.internal_lines or piece.drills or piece.labels), "internal lines, drill holes or labels"),
        (any(p.grade_rule is not None for p in piece.points), "grade rules on points"),
        (any(p.id not in outline_ids for p in piece.points), "construction points off the outline"),
    ]
    return [reason for failed, reason in checks if failed]


def check_v5_expressible(piece: Piece) -> Grainline:
    """Refuse a piece V5 cannot hold; otherwise return its grainline, which V5 requires."""
    reasons = _unsupported(piece)
    if reasons or piece.grainline is None:
        raise ValueError(f"{piece.name}: a V5 piece cannot hold " + "; ".join(reasons))
    return piece.grainline
