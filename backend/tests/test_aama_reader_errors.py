"""T127: the DXF-AAMA reader refuses files it cannot read faithfully, naming what is missing."""
from io import StringIO

import ezdxf
import pytest

from app.infrastructure.aama.reader import read_aama


def _bytes(doc) -> bytes:
    stream = StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def _aama_doc(*, cut=True, version="R12"):
    doc = ezdxf.new(version)
    msp = doc.modelspace()
    for text in ("ANSI/AAMA VERSION: 1.0.0", "PRODUCT: S", "SAMPLE SIZE: M", "UNITS: METRIC"):
        msp.add_text(text, dxfattribs={"layer": "1"})
    block = doc.blocks.new(name="P1")
    block.add_text("Piece Name: Front", dxfattribs={"layer": "1"})
    if cut:
        block.add_polyline2d([(0, 0), (100, 0), (100, 50)], close=True, dxfattribs={"layer": "1"})
    msp.add_blockref("P1", (0, 0))
    return doc


def test_a_valid_minimal_file_reads():
    style = read_aama(_bytes(_aama_doc()))
    assert (style.name, style.sample_size, style.pieces[0].cut[1]) == ("S", "M", (10.0, 0.0))


@pytest.mark.parametrize(("data", "message"), [
    (b"not a dxf at all", "not a readable DXF"),
    (_bytes(ezdxf.new("R12")), "no AAMA header"),
    (_bytes(_aama_doc(version="R2010")), "must be DXF R12"),
    (_bytes(_aama_doc(cut=False)), "Front has no layer-1 cut line"),
])
def test_unreadable_files_raise_a_specific_error(data, message):
    with pytest.raises(ValueError, match=message):
        read_aama(data)


def test_an_unknown_units_flag_is_rejected():
    doc = _aama_doc()
    next(t for t in doc.modelspace().query("TEXT") if t.dxf.text.startswith("UNITS")).dxf.text = "UNITS: PARSECS"
    with pytest.raises(ValueError, match="Unsupported AAMA units 'PARSECS'"):
        read_aama(_bytes(doc))


def test_a_missing_units_header_says_so():
    doc = _aama_doc()
    next(t for t in doc.modelspace().query("TEXT") if t.dxf.text.startswith("UNITS")).destroy()
    with pytest.raises(ValueError, match="The AAMA header has no UNITS"):
        read_aama(_bytes(doc))
