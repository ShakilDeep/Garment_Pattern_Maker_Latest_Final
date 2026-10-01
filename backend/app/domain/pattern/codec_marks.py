"""Memento codecs for piece marks: internal lines, notches, drill holes and labels."""

from typing import TYPE_CHECKING

from app.domain.pattern.annotation import DrillHole, InternalLine, Label, Notch
from app.domain.pattern.codec_values import point_at, xy
from app.domain.pattern.ids import AnnotationId, SegmentId
from app.domain.pattern.point import quantize

if TYPE_CHECKING:
    from app.domain.pattern.piece import Piece


def encode_marks(piece: "Piece") -> dict:
    return {
        "internal_lines": [
            {"id": str(m.id), "points": [xy(p) for p in m.points]} for m in piece.internal_lines
        ],
        "notches": [{"id": str(m.id), "segment": str(m.segment), "t": m.t} for m in piece.notches],
        "drills": [
            {"id": str(m.id), "at": xy(m.position), "diameter": quantize(m.diameter)} for m in piece.drills
        ],
        "labels": [
            {"id": str(m.id), "text": m.text, "at": xy(m.position), "rotation": quantize(m.rotation_degrees)}
            for m in piece.labels
        ],
    }


def decode_marks(data: dict) -> dict:
    lines = data["internal_lines"]
    return {
        "internal_lines": tuple(
            InternalLine(AnnotationId(m["id"]), tuple(map(point_at, m["points"]))) for m in lines
        ),
        "notches": tuple(
            Notch(AnnotationId(m["id"]), SegmentId(m["segment"]), m["t"]) for m in data["notches"]
        ),
        "drills": tuple(
            DrillHole(AnnotationId(m["id"]), point_at(m["at"]), m["diameter"]) for m in data["drills"]
        ),
        "labels": tuple(
            Label(AnnotationId(m["id"]), m["text"], point_at(m["at"]), m["rotation"]) for m in data["labels"]
        ),
    }
