"""Shape constants of the 1078375 block, derived from the PDS (``data/shirt_1078375_shape.json``).

Per piece: each point's offset from its measurement formula, each curve's handles as fractions of its chord
(so a curve keeps its shape when its end points move), and each notch's curve parameter. Chord fractions:
a handle h on the chord c = end - start is a·c + b·c⊥ with c⊥ = (-c.y, c.x).
"""
import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app.domain.geom.primitives import Point2D, Vector2D

SHAPE_FILE = Path(__file__).parents[2] / "data" / "shirt_1078375_shape.json"
Fractions = tuple[float, float, float, float]  # start handle (a, b), end handle (a, b)


@dataclass(frozen=True)
class PieceShape:
    offsets: Mapping[str, tuple[float, float]]
    handles: Mapping[str, Fractions]
    notches: Mapping[str, float]


def _piece(raw: dict) -> PieceShape:
    offsets = {name: (float(x), float(y)) for name, (x, y) in raw["offsets"].items()}
    handles = {edge: (float(a), float(b), float(c), float(d)) for edge, (a, b, c, d) in raw["handles"].items()}
    return PieceShape(offsets, handles, {name: float(t) for name, t in raw["notches"].items()})


@cache
def shape() -> Mapping[str, PieceShape]:
    data = json.loads(SHAPE_FILE.read_text(encoding="utf-8"))
    return {piece_id: _piece(raw) for piece_id, raw in data["pieces"].items()}


def _from_fraction(chord: Vector2D, a: float, b: float) -> Vector2D:
    return Vector2D(a * chord.x - b * chord.y, a * chord.y + b * chord.x)


def _to_fraction(chord: Vector2D, handle: Vector2D) -> tuple[float, float]:
    square = chord.x * chord.x + chord.y * chord.y
    return ((handle.x * chord.x + handle.y * chord.y) / square, (handle.y * chord.x - handle.x * chord.y) / square)


def chord_handles(start: Point2D, end: Point2D, fractions: Fractions) -> tuple[Vector2D, Vector2D]:
    chord = Vector2D.between(start, end)
    return _from_fraction(chord, *fractions[:2]), _from_fraction(chord, *fractions[2:])


def chord_fractions(start: Point2D, end: Point2D, handles: tuple[Vector2D, Vector2D]) -> Fractions:
    chord = Vector2D.between(start, end)
    return (*_to_fraction(chord, handles[0]), *_to_fraction(chord, handles[1]))
