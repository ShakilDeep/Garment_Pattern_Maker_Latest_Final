"""P1-10 over HTTP (CAD-07): garment tools are Commands; an invalid result is 422 and nothing is saved."""

from test_cad_routes import styled  # noqa: F401 - module fixture: a style made from a demo project

POCKET = {"piece_id": "pocket", "name": "Pocket", "x": 0, "y": 0, "width": 12, "height": 14, "quantity": 1}
DART = {"segment_id": "s0", "t_start": 0.4, "t_end": 0.6, "length": 5, "dart_id": "d1"}


def _pocket(client, summary, piece_id):
    """A fresh rectangle piece per test, so no test depends on another's edits."""
    url = f"/api/v1/styles/{summary['id']}"
    params = {**POCKET, "piece_id": piece_id}
    assert client.post(f"{url}/commands", json={"command": "add_rectangle", "params": params}).status_code == 200
    return f"{url}/pieces/{piece_id}/commands"


def test_a_dart_is_added_over_http_and_undone(styled):  # noqa: F811
    client, summary = styled
    url = _pocket(client, summary, "pocket")
    result = client.post(url, json={"command": "create_dart", "params": DART})
    assert result.status_code == 200, result.text
    outline = [segment["id"] for segment in result.json()["piece"]["outline"]]
    assert outline[:4] == ["s0", "d1.leg1", "d1.leg2", "d1.edge"]
    undone = client.post(f"/api/v1/styles/{summary['id']}/undo")
    assert undone.status_code == 200 and undone.json()["redo_steps"] == 1


def test_a_dart_reaching_out_of_the_piece_is_422_and_not_saved(styled):  # noqa: F811
    client, summary = styled
    url = _pocket(client, summary, "flap")
    before = client.get(f"/api/v1/styles/{summary['id']}").json()["version"]
    response = client.post(url, json={"command": "create_dart", "params": {**DART, "length": 30}})
    assert (response.status_code, response.json()["code"]) == (422, "GEOMETRY_INVALID")
    assert response.json()["details"][0]["piece_id"] == "flap"
    assert client.get(f"/api/v1/styles/{summary['id']}").json()["version"] == before


def test_a_garment_command_missing_a_parameter_is_400(styled):  # noqa: F811
    client, summary = styled
    url = f"/api/v1/styles/{summary['id']}/pieces/pocket/commands"
    response = client.post(url, json={"command": "rotate_dart", "params": {"apex_id": "d1.apex"}})
    assert (response.status_code, response.json()["code"]) == (400, "INPUT_INVALID")
    assert "missing parameter" in response.json()["message"]
