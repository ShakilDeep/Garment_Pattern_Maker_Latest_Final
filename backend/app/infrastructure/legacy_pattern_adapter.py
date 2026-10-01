"""Strangler Fig adapter (P1-03): V5 piece dicts <-> pattern Pieces, so V5 SVG/PDF/marker code keeps its dicts.

Round trips:
- Piece -> V5 -> Piece is exact (equal pieces, equal hash) for pieces in the adapter's canonical form, i.e.
  every piece piece_from_v5 builds: V5 has no element ids, so ids come back as p0.., s0.., n0...
- Anything V5 cannot hold (pairs, folds, curves, marks, grade rules) is refused, never dropped (legacy_limits).
- V5 -> Piece -> V5 is exact on every field except the grainline, which moves only by its 1e-6 cm
  quantization; notches are emitted on the same 1e-6 cm grid V5 drafts them on (doc 108).

V5 has no mirror or fold-edge data, and its outlines are already unfolded. So quantity maps to single cuts,
and cut_on_fold travels with the other V5-only fields (seams, marks, cut_points, ...) in `extras`.
"""

from copy import deepcopy
from dataclasses import replace

from app.domain.drafting import draft
from app.domain.pattern.codec_values import pair_of, point_at, xy
from app.domain.pattern.cutting import CutQuantity, Grainline
from app.domain.pattern.ids import PieceId
from app.domain.pattern.piece import Piece
from app.infrastructure.legacy_limits import check_v5_expressible
from app.infrastructure.legacy_outline import (
    derived_metrics,
    notch_on_outline,
    notch_positions,
    outline_from_ring,
    ring_of,
)
from app.infrastructure.legacy_piece import LegacyPiece, encode_extras


def piece_from_v5(data: dict) -> LegacyPiece:
    """Adapt one V5 piece dict; malformed data raises ValueError naming the problem (never KeyError/TypeError)."""
    if not isinstance(data, dict):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError("A V5 piece must be an object")  # noqa: TRY004
    try:
        points, outline = outline_from_ring(data["points"])
        bare = Piece(
            id=PieceId(data["id"]),
            name=data["name"],
            points=points,
            outline=outline,
            cut=CutQuantity(data["quantity"], 0, 0),
            grainline=Grainline(*map(point_at, pair_of(data["grainline"]))),
        )
        notches = tuple(notch_on_outline(i, raw, points, outline) for i, raw in enumerate(data["notches"]))
        piece = replace(bare, notches=notches)
    except KeyError as exc:
        raise ValueError(f"Invalid V5 piece: missing field {exc.args[0]!r}") from exc
    except (TypeError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError(f"Invalid V5 piece: {exc}") from exc
    return LegacyPiece(piece, encode_extras(data))


def piece_to_v5(legacy: LegacyPiece) -> dict:
    piece = legacy.piece
    grainline = check_v5_expressible(piece)
    ring = ring_of(piece)
    grain = [xy(grainline.start), xy(grainline.end)]
    base = {"id": str(piece.id), "name": piece.name, "points": ring, "quantity": piece.cut.total}
    return {**base, **derived_metrics(ring), "grainline": grain, "notches": notch_positions(piece),
            **legacy.extra_fields()}


def draft_pieces(values: dict[str, float], size: str, profile_id: str = "demo_v1") -> tuple[LegacyPiece, ...]:
    """V5 `draft()` wrapped: the same drafting, returned as pattern Pieces."""
    return tuple(piece_from_v5(piece) for piece in draft(values, size, profile_id)["pieces"])


def pattern_with_pieces(pattern: dict, pieces: tuple[LegacyPiece, ...]) -> dict:
    """A copy of a V5 pattern dict whose pieces are rendered from Pieces (the dict API V5 exporters read)."""
    if [str(p.piece.id) for p in pieces] != [p["id"] for p in pattern["pieces"]]:
        raise ValueError("Pieces must match the pattern's piece ids, in order")
    rest = deepcopy({k: v for k, v in pattern.items() if k != "pieces"})
    return {**rest, "pieces": [piece_to_v5(piece) for piece in pieces]}
