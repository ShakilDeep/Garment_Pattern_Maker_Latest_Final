"""T127: the DXF-AAMA writer's header, units, point classes and exact coordinates."""
from io import StringIO

import ezdxf
import pytest

from app.domain.interchange import InterchangePiece, InterchangeStyle
from app.infrastructure.aama.reader import read_aama
from app.infrastructure.aama.writer import write_aama

SQUARE = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
# A square whose top edge is a shallow arc: its 4 corners turn sharply, the arc vertices do not.
ARC_TOP = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (7.5, 10.4), (5.0, 10.5), (2.5, 10.4), (0.0, 10.0))


def _piece(cut=SQUARE, sew=(), name="Front"):
    return InterchangePiece(name=name, size="M", quantity=2, cut=cut, sew=sew,
                            grain=((5.0, 2.0), (5.0, 8.0)), notches=(((10.0, 5.0),),))


def _style(*pieces):
    return InterchangeStyle(name="Style 1", sample_size="M", pieces=pieces or (_piece(),))


def _block(data):
    doc = ezdxf.read(StringIO(data.decode("utf-8")))
    return doc, doc.blocks[doc.modelspace().query("INSERT")[0].dxf.name]


def _texts(entities):
    return [entity.dxf.text for entity in entities.query("TEXT")]


def test_the_header_and_piece_text_follow_the_aama_layout():
    doc, block = _block(write_aama(_style(), "mm"))
    assert _texts(doc.modelspace()) == [
        "ANSI/AAMA VERSION: 1.0.0", "PRODUCT: Style 1", "SAMPLE SIZE: M", "UNITS: METRIC"]
    assert _texts(block.query('TEXT[layer=="1"]')) == [
        "Piece Name: Front", "Size: M", "Quantity: 2", "Style Name: Style 1"]


@pytest.mark.parametrize(("unit", "flag", "scale"), [("mm", "METRIC", 10.0), ("inch", "ENGLISH", 1 / 2.54)])
def test_units_flag_and_scale(unit, flag, scale):
    data = write_aama(_style(), unit)
    doc, block = _block(data)
    assert f"UNITS: {flag}" in _texts(doc.modelspace())
    cut = block.query('POLYLINE[layer=="1"]')[0]
    xs = [vertex.dxf.location.x for vertex in cut.vertices]
    assert max(xs) == pytest.approx(10.0 * scale)
    assert _same(read_aama(data).pieces[0].cut, SQUARE)


def _same(left, right) -> bool:
    return all(abs(a - b) <= 1e-6 for p, q in zip(left, right, strict=True) for a, b in zip(p, q, strict=True))


def test_corners_are_turn_points_and_arc_vertices_curve_points():
    _, block = _block(write_aama(_style(_piece(cut=ARC_TOP)), "mm"))
    assert len(block.query('POINT[layer=="2"]')) == 4
    assert len(block.query('POINT[layer=="3"]')) == 3


def test_a_piece_without_sew_writes_no_sew_layer_and_one_with_sew_does():
    _, bare = _block(write_aama(_style(), "mm"))
    _, sewn = _block(write_aama(_style(_piece(sew=(SQUARE,))), "mm"))
    assert not bare.query('POLYLINE[layer=="14"]') and len(sewn.query('POLYLINE[layer=="14"]')) == 1


def test_writing_twice_reads_back_the_same_style_exactly():
    style = _style(_piece(cut=ARC_TOP, sew=(SQUARE,)))
    first, second = read_aama(write_aama(style, "mm")), read_aama(write_aama(style, "mm"))
    assert first == second
    assert _same(first.pieces[0].cut, ARC_TOP) and first.pieces[0].notches == (((10.0, 5.0),),)


def test_an_unknown_unit_is_rejected():
    with pytest.raises(ValueError, match="Unsupported AAMA unit 'cm'"):
        write_aama(_style(), "cm")
