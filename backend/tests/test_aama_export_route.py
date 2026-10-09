"""T127: the app's own pattern downloads as DXF-AAMA beside the unchanged AutoCAD DXF."""
from io import StringIO

import ezdxf
import pytest
from test_integrity import _ready

from app.infrastructure.aama.reader import read_aama


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    client, url = _ready(tmp_path_factory.mktemp("aama"))
    response = client.post(f"{url}/patterns/generate", json={"size": "L"})
    assert response.status_code == 200, response.text
    return client, url, response.json()


def test_the_pattern_exports_as_aama_with_every_piece_and_its_grain(generated):
    client, url, pattern = generated
    response = client.get(f"{url}/exports/dxf-aama")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/dxf")
    assert response.headers["content-disposition"].endswith('_L_demo_aama.dxf"')
    style = read_aama(response.content)
    assert [piece.name for piece in style.pieces] == [piece["name"] for piece in pattern["pieces"]]
    assert all(piece.size == "L" and piece.grain is not None for piece in style.pieces)
    assert "UNITS: METRIC" in response.text
    doc = ezdxf.read(StringIO(response.text))
    assert doc.dxfversion == "AC1009"


def test_inch_exports_are_english_and_the_audit_records_the_unit(generated):
    client, url, _ = generated
    response = client.post(f"{url}/exports", json={"kind": "dxf-aama", "unit": "inch"})
    assert response.status_code == 200 and "UNITS: ENGLISH" in response.text
    record = client.get(url).json()["export_records"][-1]
    assert (record["kind"], record["unit"]) == ("dxf-aama", "inch")


def test_the_autocad_dxf_is_unchanged(generated):
    client, url, _ = generated
    response = client.get(f"{url}/exports/dxf")
    assert response.status_code == 200 and "AC1024" in response.text  # R2010, not R12


def test_a_project_without_a_pattern_cannot_export_aama(tmp_path):
    client, url = _ready(tmp_path)
    response = client.get(f"{url}/exports/dxf-aama")
    assert (response.status_code, response.json()["code"]) == (409, "REQUIREMENTS_NOT_READY")


def test_cut_and_sew_lines_round_trip_exactly(generated):
    client, url, pattern = generated
    style = read_aama(client.get(f"{url}/exports/dxf-aama").content)
    for source, piece in zip(pattern["pieces"], style.pieces, strict=True):
        cut = source.get("cut_points", source["points"])[:-1]
        assert [c for p in piece.cut for c in p] == pytest.approx([v for x, y in cut for v in (x, -y)], abs=1e-6)
        assert piece.quantity == source["quantity"] and len(piece.notches) == len(source["notches"])
