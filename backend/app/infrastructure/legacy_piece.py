"""The adapter's carrier: a Piece plus the V5-only fields of the dict it came from (P1-03)."""

import json
from dataclasses import dataclass

from app.domain.pattern.piece import Piece

MODEL_FIELDS = ("id", "name", "points", "quantity", "grainline", "notches")
DERIVED_FIELDS = ("width", "height", "area", "perimeter")


def _reject_constant(name: str) -> None:
    raise ValueError(f"Legacy extras must not contain {name}")


@dataclass(frozen=True)
class LegacyPiece:
    """A Piece plus the V5-only fields, kept as JSON object text so the carrier stays immutable and exact."""

    piece: Piece
    extras: str

    def __post_init__(self) -> None:
        if not isinstance(self.piece, Piece) or not isinstance(self.extras, str):
            # ValueError, not TypeError: the API maps ValueError to 400.
            raise ValueError("A legacy piece needs a Piece and extras as JSON text")  # noqa: TRY004
        try:
            fields = json.loads(self.extras, parse_constant=_reject_constant)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Legacy extras must be JSON object text") from exc
        if not isinstance(fields, dict) or set(fields) & {*MODEL_FIELDS, *DERIVED_FIELDS}:
            raise ValueError("Legacy extras must be a JSON object without model or derived fields")

    def extra_fields(self) -> dict:
        return json.loads(self.extras)


def encode_extras(data: dict) -> str:
    extras = {k: v for k, v in data.items() if k not in (*MODEL_FIELDS, *DERIVED_FIELDS)}
    try:
        return json.dumps(extras, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"Invalid V5 piece: V5-only fields must be finite JSON values ({exc})") from exc
