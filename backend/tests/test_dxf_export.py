from io import StringIO

import ezdxf
import pytest
from test_integrity import _ready

from app.domain.units import from_cm
from app.infrastructure.dxf_export import export_dxf

INSUNITS = {"cm": 5, "mm": 4, "inch": 1}
SQUARE_SIDE = {"cm": 10, "mm": 100, "inch": 3.937008}


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    client, url = _ready(tmp_path_factory.mktemp("dxf"))
    response = client.post(f"{url}/patterns/generate", json={"size": "L"})
    assert response.status_code == 200, response.text
    return client, url, response.json()


def _read(data: bytes):
    return ezdxf.read(StringIO(data.decode("utf-8")))


@pytest.mark.parametrize("unit", ["cm", "mm", "inch"])
def test_header_declares_the_drawing_unit(generated, unit):
    doc = _read(export_dxf(generated[2], unit))
    assert doc.header["$INSUNITS"] == INSUNITS[unit]
    assert doc.header["$MEASUREMENT"] == (0 if unit == "inch" else 1)


@pytest.mark.parametrize("unit", ["cm", "mm", "inch"])
def test_every_cut_vertex_matches_the_model_at_true_scale(generated, unit):
    pattern = generated[2]
    doc = _read(export_dxf(pattern, unit))
    for piece in pattern["pieces"]:
        cut = [e for e in doc.blocks[piece["id"]] if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT"]
        assert len(cut) == 1 and cut[0].closed
        written = list(cut[0].get_points("xy"))
        expected = [(from_cm(x, unit), -from_cm(y, unit)) for x, y in piece.get("cut_points", piece["points"])]
        assert len(written) == len(expected)
        for (wx, wy), (ex, ey) in zip(written, expected, strict=True):
            assert wx == pytest.approx(ex, abs=1e-6) and wy == pytest.approx(ey, abs=1e-6)
    inserted = {e.dxf.name for e in doc.modelspace().query("INSERT")}
    assert inserted == {p["id"] for p in pattern["pieces"]}


@pytest.mark.parametrize("unit", ["cm", "mm", "inch"])
def test_calibration_square_measures_ten_centimetres(generated, unit):
    doc = _read(export_dxf(generated[2], unit))
    square = doc.modelspace().query('LWPOLYLINE[layer=="CALIBRATION"]').first
    xs, ys = zip(*square.get_points("xy"), strict=True)
    assert max(xs) - min(xs) == pytest.approx(SQUARE_SIDE[unit], abs=1e-6)
    assert max(ys) - min(ys) == pytest.approx(SQUARE_SIDE[unit], abs=1e-6)


def test_unknown_unit_is_rejected_by_the_writer(generated):
    with pytest.raises(ValueError, match="Unsupported unit"):
        export_dxf(generated[2], "ft")


def test_dxf_route_returns_an_autocad_file(generated):
    client, url, _ = generated
    response = client.get(f"{url}/exports/dxf", params={"size": "L", "unit": "mm"})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/dxf")
    assert response.headers["content-disposition"].endswith('.dxf"')
    assert _read(response.content).header["$INSUNITS"] == 4


def test_dxf_route_rejects_an_unknown_unit(generated):
    client, url, _ = generated
    assert client.get(f"{url}/exports/dxf", params={"size": "L", "unit": "ft"}).status_code == 422


def test_dxf_route_refuses_a_stale_pattern(tmp_path):
    client, url = _ready(tmp_path)
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    edit = client.patch(f"{url}/measurements/half_chest", json={"size": "L", "changes": {"half_chest": 59}})
    assert edit.status_code == 200, edit.text
    assert client.get(f"{url}/exports/dxf", params={"size": "L"}).status_code == 409
