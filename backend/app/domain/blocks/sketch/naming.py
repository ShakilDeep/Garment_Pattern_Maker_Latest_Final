"""Drafting names for block points (build plan: "every drafted point has a name", e.g. CF_neck, side_waist).

A name is letters and digits in words joined by single underscores, starting with a letter. Adapter ids
(p0, s1, n2…) are refused, so a named block can never pass off a converted V5 outline as drafted. Edges
take the ids of their end points ("SP:HPS"), so a name is at most 31 characters to keep within ids' 64.
"""
import re

from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece

POINT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*")
ADAPTER_ID = re.compile(r"[psn][0-9]+")
MAX_NAME = 31


def is_named(name: object) -> bool:
    return (isinstance(name, str) and len(name) <= MAX_NAME and POINT_NAME.fullmatch(name) is not None
            and ADAPTER_ID.fullmatch(name) is None)


def point_name(name: str) -> PointId:
    if not is_named(name):
        raise ValueError(f"Point {name!r} must be a drafting name such as CF_neck: up to {MAX_NAME} letters "
                         "and digits in words joined by single '_', not an adapter id like p3")
    return PointId(name)


def segment_id(start: str, end: str) -> SegmentId:
    return SegmentId(f"{start}:{end}")


def check_named(piece: Piece) -> None:
    """Every point of a block's piece has a drafting name; raise listing the ones that do not."""
    unnamed = [str(point.id) for point in piece.points if not is_named(str(point.id))]
    if unnamed:
        raise ValueError(f"{piece.name} has unnamed points: {', '.join(unnamed)}")
