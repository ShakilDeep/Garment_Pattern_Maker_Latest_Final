"""P1-07 acceptance (CAD-07): pieces are edited by Commands over HTTP; an invalid result is 422, never saved."""

import pytest
from test_integrity import _ready


@pytest.fixture(scope="module")
def styled(tmp_path_factory):
    client, url = _ready(tmp_path_factory.mktemp("cad"))
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    assert client.post(f"{url}/grade", json={"sizes": ["S", "M"]}).status_code == 200
    response = client.post("/api/v1/styles", json={"project_id": url.rsplit("/", 1)[1]})
    assert response.status_code == 200, response.text
    return client, response.json()


def _piece_url(summary):
    return f"/api/v1/styles/{summary['id']}/pieces/{summary['piece_ids'][0]}"


def test_a_style_is_created_from_the_project_pattern_and_grades(styled):
    _, summary = styled
    assert summary["sizes"] == ["S", "M", "L", "XL", "XXL", "3XL"] and summary["base_size"] == "L"
    assert summary["graded_sizes"] == ["S", "M", "L"] and summary["version"] == 1
    assert len(summary["piece_ids"]) == 8 and summary["undo_steps"] == 0


def test_get_piece_returns_the_typed_piece_and_its_cut_outline(styled):
    client, summary = styled
    piece = client.get(_piece_url(summary), params={"size": "M"}).json()
    assert piece["size"] == "M" and piece["outline"][0]["type"] == "line"
    assert {"id", "x", "y", "grade_rule"} <= set(piece["points"][0])
    assert piece["seam_allowance"]["default_width"] == 0 and len(piece["cut_outline"]) >= 3
    assert client.get(_piece_url(summary), params={"size": "XL"}).json()["code"] == "INPUT_INVALID"


def test_a_valid_command_is_saved_and_can_be_undone(styled):
    client, summary = styled
    before = client.get(_piece_url(summary), params={"size": "L"}).json()
    x, y = before["points"][0]["x"] + 0.5, before["points"][0]["y"]
    body = {"command": "move_point", "params": {"size": "L", "point_id": "p0", "x": x, "y": y}}
    result = client.post(f"{_piece_url(summary)}/commands", json=body).json()
    assert result["piece"]["points"][0]["x"] == x and result["style"]["undo_steps"] == 1
    undone = client.post(f"/api/v1/styles/{summary['id']}/undo").json()
    assert undone["redo_steps"] == 1
    assert client.get(_piece_url(summary), params={"size": "L"}).json() == before
    redone = client.post(f"/api/v1/styles/{summary['id']}/redo").json()
    assert (redone["undo_steps"], redone["redo_steps"]) == (1, 0)
    assert client.get(_piece_url(summary), params={"size": "L"}).json() == result["piece"]


def test_an_invalid_result_is_refused_with_422_and_nothing_is_saved(styled):
    client, summary = styled
    before = client.get(f"/api/v1/styles/{summary['id']}").json()
    piece = client.get(_piece_url(summary), params={"size": "L"}).json()
    crossing = {"x": piece["points"][2]["x"], "y": piece["points"][2]["y"]}
    body = {"command": "move_point", "params": {"size": "L", "point_id": "p0", **crossing}}
    response = client.post(f"{_piece_url(summary)}/commands", json=body)
    assert response.status_code == 422 and response.json()["code"] == "GEOMETRY_INVALID"
    assert response.json()["details"][0]["piece_id"] == summary["piece_ids"][0]
    assert client.get(f"/api/v1/styles/{summary['id']}").json() == before
    assert client.get(_piece_url(summary), params={"size": "L"}).json() == piece
