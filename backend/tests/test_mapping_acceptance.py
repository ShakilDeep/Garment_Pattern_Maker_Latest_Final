"""The assistant's accept_mapping needs confirmation and then confirms the unmapped row it names (T126c).

Regression: it used to write an ``accepted_mappings`` dict that nothing read, so the row stayed unmapped.
"""
from test_mapping_routes import UNKNOWN, XLSX, client  # noqa: F401 -- shared fixture


def _propose(client, base, prompt):  # noqa: F811
    return client.post(base + "/assistant/propose", json={"prompt": prompt, "size": "S"}).json()


def _execute(client, base, action, confirmed=True):  # noqa: F811
    return client.post(base + "/assistant/execute", json={"proposal_id": action["id"], "confirmed": confirmed})


def _base(client):  # noqa: F811
    pid = client.post("/api/v1/projects", json={"name": "Map"}).json()["id"]
    base = f"/api/v1/projects/{pid}"
    client.post(base + "/documents", files={"file": ("c.xlsx", UNKNOWN, XLSX)})
    return base


def test_accept_mapping_requires_confirmation_then_maps_the_row(client):  # noqa: F811
    base = _base(client)
    action = _propose(client, base, 'Accept mapping of "1/2 hips" as half_seat')
    assert (action["intent"], action["requires_confirmation"]) == ("accept_mapping", True)
    assert action["parameters"] == {"source_label": "1/2 hips", "canonical_key": "half_seat"}
    assert _execute(client, base, action, confirmed=False).status_code == 409
    done = _execute(client, base, action)
    assert done.status_code == 200, done.text
    row = next(r for r in done.json()["project"]["measurements"] if r["row"] == 3)
    assert (row["key"], row["mapping_status"], row["values"]["S"]["value"]) == ("half_seat", "confirmed", 48)
    assert done.json()["validation"]["status"] == "INPUTS_INVALIDATED"
    assert "accepted_mappings" not in done.json()["project"]


def test_accept_mapping_of_a_label_with_no_unmapped_row_is_rejected(client):  # noqa: F811
    base = _base(client)
    action = _propose(client, base, 'Accept mapping of "shoulder breadth" as shoulder_point_to_point')
    response = _execute(client, base, action)
    assert response.status_code == 400
    assert "No unmapped row" in response.json()["message"]


def test_accept_mapping_accepts_any_canonical_key_not_only_shirt_codes(client):  # noqa: F811
    action = _propose(client, _base(client), 'Accept mapping of "1/2 hips" as inseam')
    assert action["parameters"]["canonical_key"] == "inseam"
