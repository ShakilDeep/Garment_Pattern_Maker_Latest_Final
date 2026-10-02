"""P1-07: CAD route failures get specific status codes and stable error codes."""

import pytest
from test_cad_routes import (  # noqa: F401 - module fixture: a style made from a demo project
    _piece_url,
    styled,
)

from app.application.errors import StyleConflict
from app.infrastructure.style_repository import StyleRepository


@pytest.mark.parametrize(
    ("path", "body", "status", "code"),
    [
        ("/api/v1/styles/nope", None, 404, "NOT_FOUND"),
        ("{piece}/commands", {"command": "explode", "params": {}}, 400, "INPUT_INVALID"),
        ("{piece}/commands", {"command": "move_point", "params": {"piece_id": "x"}}, 400, "INPUT_INVALID"),
        ("/api/v1/styles", {"project_id": "missing"}, 404, "NOT_FOUND"),
    ],
)
def test_bad_requests_get_specific_errors(styled, path, body, status, code):  # noqa: F811
    client, summary = styled
    path = path.format(piece=_piece_url(summary), style=summary["id"])
    response = client.get(path) if body is None else client.post(path, json=body)
    assert (response.status_code, response.json()["code"]) == (status, code)


def test_a_style_conflict_from_the_store_maps_to_409(styled, monkeypatch):  # noqa: F811
    client, summary = styled

    def stale(self, style, history, expected_version):
        raise StyleConflict(f"Style {style.id} changed since it was loaded; reload it and try again")

    monkeypatch.setattr(StyleRepository, "save", stale)
    body = {"command": "set_seam_allowance",
            "params": {"default_width": 1, "edge_widths": {}, "corner_styles": {}}}
    response = client.post(f"{_piece_url(summary)}/commands", json=body)
    assert (response.status_code, response.json()["code"]) == (409, "STYLE_CONFLICT")


def test_a_fresh_style_has_nothing_to_undo_or_redo(styled):  # noqa: F811
    client, summary = styled
    fresh = client.post("/api/v1/styles", json={"project_id": summary["project_id"]}).json()
    for direction in ("undo", "redo"):
        response = client.post(f"/api/v1/styles/{fresh['id']}/{direction}")
        assert (response.status_code, response.json()["code"]) == (409, f"NOTHING_TO_{direction.upper()}")
