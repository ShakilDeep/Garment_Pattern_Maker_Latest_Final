"""T130: a style drafted from the 1078375 block over HTTP, with measure, walk and add_notch (P1-11)."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app

CAP = [{"piece_id": "Sleeve", "points": ["UA_back", "cap_crown", "UA_front"]}]
NOTCH = {"size": "L", "notch_id": "n1", "segment": "SP:UA", "t": 0.5}
ARMHOLE = [{"piece_id": "FRT", "points": ["SP", "UA"]}, {"piece_id": "back", "points": ["yoke_armhole", "UA"]},
           {"piece_id": "back_YK", "points": ["SP", "yoke_armhole"]}]


@pytest.fixture(scope="module")
def drafted(tmp_path_factory):
    client = TestClient(create_app(f"sqlite:///{tmp_path_factory.mktemp('blockstyle')}/s.db"))
    response = client.post("/api/v1/styles/from-block", json={"block_id": "shirt_1078375"})
    assert response.status_code == 200, response.text
    return client, response.json()


def test_the_style_has_the_seven_pieces_in_every_size_with_allowances(drafted):
    client, summary = drafted
    assert (summary["sizes"], summary["base_size"], summary["project_id"]) == (
        ["S", "M", "L", "XL", "XXL", "3XL"], "L", None)
    assert summary["graded_sizes"] == summary["sizes"]
    assert summary["piece_ids"] == ["FRT", "back", "back_YK", "CLR", "BND_TOP", "BND_IN", "Sleeve"]
    piece = client.get(f"/api/v1/styles/{summary['id']}/pieces/back_YK", params={"size": "L"}).json()
    assert piece["points"][1]["id"] == "HPS" and piece["cut_outline"]
    assert [m["id"] for m in piece["notch_marks"]] == ["shoulder_notch"]
    mark = piece["notch_marks"][0]
    assert ((mark["tip"][0] - mark["at"][0]) ** 2 + (mark["tip"][1] - mark["at"][1]) ** 2) ** 0.5 == pytest.approx(0.7)


@pytest.mark.parametrize(("body", "value", "unit", "tolerance"), [  # FRT at L against the PDS sew line
    ({"kind": "distance", "points": ["HPS", "SP"]}, 17.48, "cm", 0.01),
    ({"kind": "path", "edges": ["HPS:SP"]}, 17.48, "cm", 0.01),
    ({"kind": "angle", "point": "CF_top"}, 90.0, "deg", 1e-6),
    ({"kind": "area", "outline": "sew"}, 2250.0, "cm2", 0.005 * 2250.0),  # PDS SEW_AREA 0.225 m2, 0.5 %
    ({"kind": "perimeter", "outline": "sew"}, 209.1049, "cm", 0.1),  # PDS SEW_PERIMETER
])
def test_measure_returns_backend_values(drafted, body, value, unit, tolerance):
    client, summary = drafted
    response = client.post(f"/api/v1/styles/{summary['id']}/measure", json={"size": "L", "piece_id": "FRT", **body})
    assert response.status_code == 200, response.text
    assert response.json()["unit"] == unit and response.json()["value"] == pytest.approx(value, abs=tolerance)


def test_walk_shows_the_cap_ease(drafted):
    client, summary = drafted
    body = {"size": "L", "first": CAP, "second": ARMHOLE, "at_cm": 10}
    result = client.post(f"/api/v1/styles/{summary['id']}/walk", json=body).json()
    assert result["difference_cm"] == pytest.approx(3.929, abs=0.1)  # PDS ease, within shirt.md Q4
    assert result["at"][0]["segment"] == "UA_back:cap_crown"


def test_add_notch_is_a_command_with_undo(drafted):
    client, summary = drafted
    url = f"/api/v1/styles/{summary['id']}"
    params = {"size": "L", "notch_id": "walk_1", "segment": "SP:UA", "t": 0.5}
    response = client.post(f"{url}/pieces/FRT/commands", json={"command": "add_notch", "params": params})
    assert response.status_code == 200, response.text
    assert [n["id"] for n in response.json()["piece"]["notches"]] == ["walk_1"]
    assert client.post(f"{url}/undo").status_code == 200
    assert client.get(f"{url}/pieces/FRT", params={"size": "L"}).json()["notches"] == []


def test_the_graded_aama_export_downloads_as_one_zip(drafted):
    client, summary = drafted
    response = client.get(f"/api/v1/styles/{summary['id']}/export/aama", params={"unit": "mm"})
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    assert f'filename="{summary["id"]}_aama.zip"' in response.headers["content-disposition"]
    assert client.get(f"/api/v1/styles/{summary['id']}/export/aama", params={"unit": "cm"}).status_code == 422
    assert client.get("/api/v1/styles/style-unknown/export/aama").status_code == 404


@pytest.mark.parametrize(("path", "body", "status"), [
    ("/api/v1/styles/from-block", {"block_id": "tee_v9"}, 400),
    ("/api/v1/styles/from-block", {"block_id": "demo_v1"}, 400),
    ("{style}/measure", {"size": "L", "piece_id": "pocket", "kind": "area", "outline": "sew"}, 404),
    ("{style}/measure", {"size": "L", "piece_id": "FRT", "kind": "volume"}, 422),
    ("{style}/walk", {"size": "L", "first": [{"piece_id": "FRT", "points": ["UA", "SP"]}], "second": ARMHOLE}, 404),
    ("{style}/measure", {"size": "L", "piece_id": "FRT", "kind": "distance", "points": ["HPS"]}, 400),
    ("{style}/measure", {"size": "L", "piece_id": "FRT", "kind": "angle"}, 400),
    ("{style}/pieces/FRT/commands", {"command": "add_notch", "params": NOTCH | {"segment": "UA:SP"}}, 400),
    ("{style}/pieces/FRT/commands", {"command": "add_notch", "params": NOTCH | {"t": 1.5}}, 400),
])
def test_bad_requests_are_refused(drafted, path, body, status):
    client, summary = drafted
    response = client.post(path.format(style=f"/api/v1/styles/{summary['id']}"), json=body)
    assert response.status_code == status, response.text
