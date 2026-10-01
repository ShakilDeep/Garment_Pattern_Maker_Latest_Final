"""Stable hash of a piece: SHA-256 of its canonical Memento JSON (undo history, grading).

Scope: everything the Memento stores, including the piece name, label text and ids, so a rename changes it.
Equal hashes mean equal after quantization to 1e-6 cm (the model stores quantized values), not "within
tolerance"; text is hashed as given (no Unicode normalization).
"""

import json
from hashlib import sha256

from app.domain.pattern.piece import Piece
from app.domain.pattern.serialize import piece_to_data


def canonical_json(piece: Piece) -> str:
    return json.dumps(piece_to_data(piece), sort_keys=True, separators=(",", ":"), allow_nan=False)


def geometry_hash(piece: Piece) -> str:
    return sha256(canonical_json(piece).encode("utf-8")).hexdigest()
