"""P1-05 acceptance (PM-04): a style of 200 pieces x 30 sizes loads, serializes and shows a size in under 3 s."""

import json
from math import cos, pi, sin
from time import perf_counter

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import Notch
from app.domain.pattern.cutting import CutQuantity, Grainline
from app.domain.pattern.ids import AnnotationId, PieceId, PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import PatternPoint
from app.domain.pattern.segment import Line
from app.domain.pattern.serialize import piece_to_data
from app.domain.pattern.style_codec import style_from_json, style_to_json

PIECES = 200
SIZES = 30
VERTICES = 60  # the V5 shirt body pieces have 51-102 outline points
BUDGET_SECONDS = 3


def _ring_piece() -> dict:
    points = tuple(
        PatternPoint(PointId(f"p{i}"), Point2D(30 * cos(2 * pi * i / VERTICES), 40 * sin(2 * pi * i / VERTICES)))
        for i in range(VERTICES)
    )
    outline = tuple(
        Line(SegmentId(f"s{i}"), points[i].id, points[(i + 1) % VERTICES].id) for i in range(VERTICES)
    )
    notches = tuple(Notch(AnnotationId(f"n{i}"), SegmentId(f"s{i * 10}"), 0.5) for i in range(4))
    grain = Grainline(Point2D(0, -20), Point2D(0, 20))
    piece = Piece(PieceId("ring"), "Ring", points, outline, CutQuantity(1, 0, 0), grain, notches=notches)
    return piece_to_data(piece)


def _document() -> str:
    template = _ring_piece()
    sizes = [f"S{n}" for n in range(SIZES)]

    def sized(size_index: int, piece_index: int) -> dict:
        shift = size_index * 0.5 + piece_index
        points = [{**p, "x": p["x"] + shift} for p in template["points"]]
        return {**template, "id": f"pc{piece_index}", "name": f"Piece {piece_index}", "points": points}

    geometry = [
        {"size": size, "pieces": [sized(s, i) for i in range(PIECES)]} for s, size in enumerate(sizes)
    ]
    style = {"schema_version": 1, "id": "big", "name": "Big", "sizes": sizes, "base_size": "S0"}
    return json.dumps({**style, "geometry": geometry})


def test_200_pieces_by_30_sizes_load_serialize_and_view_within_budget():
    text = _document()
    started = perf_counter()
    style = style_from_json(text)
    serialized = style_to_json(style)
    viewed = style.view("S29")
    elapsed = perf_counter() - started
    assert elapsed < BUDGET_SECONDS, f"load + serialize + one size view took {elapsed:.2f} s"
    assert len(style.sizes) == SIZES and len(style.piece_ids) == PIECES
    assert json.loads(serialized) == json.loads(text)
    assert len(viewed) == PIECES and viewed[-1].point(PointId("p0")).position.x == 30 + 14.5 + 199
