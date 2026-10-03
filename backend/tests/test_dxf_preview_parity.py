"""The AutoCAD DXF must draw the same shapes as the app's Pattern Preview (the Sleeve twice)."""
from collections import Counter
from io import StringIO

import ezdxf
import pytest
from test_integrity import _ready

from app.infrastructure.dxf_export import export_dxf
from app.infrastructure.piece_layout import drawn_pieces


@pytest.fixture(scope="module")
def pattern(tmp_path_factory):
    client, url = _ready(tmp_path_factory.mktemp("dxf-parity"))
    response = client.post(f"{url}/patterns/generate", json={"size": "M"})
    assert response.status_code == 200, response.text
    return response.json()


def test_dxf_draws_the_same_shapes_as_the_preview(pattern):
    doc = ezdxf.read(StringIO(export_dxf(pattern, "cm").decode("utf-8")))
    inserts = list(doc.modelspace().query("INSERT"))
    assert len(inserts) == len(pattern["pieces"]) + 1 == 9
    sleeve = next(p["id"] for p in pattern["pieces"] if p["name"] == "Sleeve")
    counts = Counter(e.dxf.name for e in inserts)
    assert counts.pop(sleeve) == 2
    assert set(counts.values()) == {1}
    sleeve_spots = {tuple(e.dxf.insert)[:2] for e in inserts if e.dxf.name == sleeve}
    assert len(sleeve_spots) == 2


def test_drawn_pieces_repeats_only_the_sleeve(pattern):
    drawn = drawn_pieces(pattern["pieces"])
    assert len(drawn) == 9
    assert [p["name"] for p in drawn].count("Sleeve") == 2


def test_drawn_pieces_without_a_sleeve_is_unchanged():
    front = {"id": "front", "name": "Front"}
    assert drawn_pieces([front]) == [front]
    assert drawn_pieces([]) == []
