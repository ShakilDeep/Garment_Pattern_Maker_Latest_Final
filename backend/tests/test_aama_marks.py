"""T144: a style piece's labels export as layer-15 annotations and its drill holes as layer-13 points."""
from dataclasses import replace

import pytest

from app.application.cad.style_from_block import style_from_block
from app.domain.geom.primitives import Point2D
from app.domain.interchange import InterchangeStyle
from app.domain.pattern.annotation import DrillHole
from app.domain.pattern.ids import AnnotationId
from app.infrastructure.aama.from_style import piece_to_interchange
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.aama.writer import write_aama

DRILL = Point2D(20.0, -15.0)


@pytest.fixture(scope="module")
def exported():
    style = style_from_block("shirt_1078375")
    front = next(piece for piece in style.view("L") if piece.name == "FRT")
    drilled = replace(front, drills=(DrillHole(AnnotationId("pocket_drill"), DRILL, 0.3),))
    piece = piece_to_interchange(drilled, "L", style.allowances[front.id])
    return piece, read_aama(write_aama(InterchangeStyle("1078375", "L", (piece,)), "mm")).pieces[0]


def test_the_label_is_a_layer_15_annotation(exported):
    piece, back = exported
    assert piece.annotations == ("FRT · cut 2 (1 mirrored pair)",)
    assert back.annotations == piece.annotations


def test_drill_holes_round_trip_on_layer_13(exported):
    piece, back = exported
    assert piece.drills == ((DRILL.x, DRILL.y),)
    assert len(back.drills) == 1 and back.drills[0] == pytest.approx(piece.drills[0])


def test_a_piece_without_drills_exports_none():
    style = style_from_block("shirt_1078375")
    back = next(piece for piece in style.view("L") if piece.name == "back")
    assert piece_to_interchange(back, "L", style.allowances[back.id]).drills == ()
