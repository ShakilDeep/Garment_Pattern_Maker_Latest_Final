"""Memento (PM-01): a piece as deterministic JSON-ready data and back; loading re-runs every invariant."""

from app.domain.pattern.codec_marks import decode_marks, encode_marks
from app.domain.pattern.codec_values import (
    decode_point,
    decode_segment,
    encode_point,
    encode_segment,
    pair_of,
    point_at,
    xy,
)
from app.domain.pattern.cutting import CutQuantity, FoldLine, Grainline
from app.domain.pattern.ids import PieceId, SegmentId
from app.domain.pattern.piece import Piece

SCHEMA_VERSION = 1


def piece_to_data(piece: Piece) -> dict:
    grain = piece.grainline
    return {
        "schema_version": SCHEMA_VERSION,
        "id": str(piece.id),
        "name": piece.name,
        "points": [encode_point(p) for p in piece.points],
        "outline": [encode_segment(s) for s in piece.outline],
        "cut": {
            "single": piece.cut.single,
            "mirrored_pairs": piece.cut.mirrored_pairs,
            "on_fold": piece.cut.on_fold,
        },
        "grainline": [xy(grain.start), xy(grain.end)] if grain else None,
        "fold": str(piece.fold.segment) if piece.fold else None,
        **encode_marks(piece),
    }


def piece_from_data(data: dict) -> Piece:
    """Rebuild a piece; malformed data raises ValueError naming the problem (never KeyError/TypeError)."""
    try:
        version = data["schema_version"]
        if type(version) is not int or version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported pattern schema version {version!r}")
        cut = data["cut"]
        grain = data["grainline"]
        return Piece(
            id=PieceId(data["id"]),
            name=data["name"],
            points=tuple(decode_point(p) for p in data["points"]),
            outline=tuple(decode_segment(s) for s in data["outline"]),
            cut=CutQuantity(cut["single"], cut["mirrored_pairs"], cut["on_fold"]),
            grainline=Grainline(*map(point_at, pair_of(grain))) if grain is not None else None,
            fold=FoldLine(SegmentId(data["fold"])) if data["fold"] is not None else None,
            **decode_marks(data),
        )
    except KeyError as exc:
        raise ValueError(f"Invalid pattern data: missing field {exc.args[0]!r}") from exc
    except (TypeError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError(f"Invalid pattern data: {exc}") from exc
