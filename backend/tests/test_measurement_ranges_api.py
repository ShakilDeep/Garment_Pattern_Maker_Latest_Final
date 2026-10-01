"""P0-07: every measurement write path enforces per-measurement ranges and rejects unknown keys."""
import pytest
from test_ai_trust import proposal, setup_client
from test_integrity import _ready

from app.application.service import Service
from app.infrastructure.repository import Repository

SIZES = ("S", "M", "L", "XL", "XXL", "3XL")


def _sleeve(client, url, size="L"):
    rows = client.get(url).json()["measurements"]
    return next(row for row in rows if row["key"] == "sleeve_length")["values"][size]["value"]


@pytest.mark.parametrize(("route", "value", "status"), [
    ("", -3, 400), ("/sleeve_length", -3, 400), ("", 20, 400), ("/sleeve_length", 105, 400),
    ("", 32, 200), ("/sleeve_length", 104, 200),
], ids=["bulk-negative", "scoped-negative", "bulk-too-short", "scoped-too-long", "bulk-lower-edge",
        "scoped-upper-edge"])
def test_sleeve_writes_respect_its_source_range(tmp_path, route, value, status):
    client, url = _ready(tmp_path)
    before = _sleeve(client, url)
    response = client.patch(f"{url}/measurements{route}", json={"size": "L", "changes": {"sleeve_length": value}})
    assert response.status_code == status
    assert _sleeve(client, url) == (value if status == 200 else before)
    if status == 400:
        assert response.json()["code"] == "MEASUREMENT_INVALID"
        assert "32.0" in response.json()["message"]


def test_bulk_route_rejects_unknown_keys_without_creating_rows(tmp_path):
    client, url = _ready(tmp_path)
    keys = {row["key"] for row in client.get(url).json()["measurements"]}
    body = {"size": "L", "changes": {"sleeve_length": 66, "made_up_key": 10}}
    response = client.patch(f"{url}/measurements", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "MEASUREMENT_UNKNOWN"
    assert {row["key"] for row in client.get(url).json()["measurements"]} == keys


def test_bounds_stay_anchored_to_the_source_after_an_override(tmp_path):
    client, url = _ready(tmp_path)
    for value, status in ((100, 200), (31, 400), (33, 200)):
        response = client.patch(f"{url}/measurements", json={"size": "L", "changes": {"sleeve_length": value}})
        assert response.status_code == status


def test_assistant_adjustment_out_of_range_is_rejected(tmp_path):
    params = {"measurement": "sleeve_length", "delta": -40, "size": "L"}
    client, url, _ = setup_client(tmp_path, proposal(parameters=params))
    action = client.post(f"{url}/assistant/propose", json={"prompt": "edit"}).json()
    before = client.get(url).json()
    response = client.post(f"{url}/assistant/execute", json={"proposal_id": action["id"], "confirmed": True})
    assert response.status_code == 400
    assert response.json()["code"] == "MEASUREMENT_INVALID"
    assert client.get(url).json() == before


def _patch(client, url, size, key, value):
    return client.patch(f"{url}/measurements", json={"size": size, "changes": {key: value}}).status_code


def test_overriding_formula_sizes_does_not_move_or_drop_the_range(tmp_path):
    client, url = _ready(tmp_path)
    assert _patch(client, url, "3XL", "sleeve_length", 69.5) == 200
    assert _patch(client, url, "L", "sleeve_length", 104) == 200
    for size in SIZES:
        assert _patch(client, url, size, "collar_band_width_cb", 3.3) == 200
    assert _patch(client, url, "L", "collar_band_width_cb", 300) == 400


def test_missing_catalog_measurement_can_be_entered_with_the_blanket_bound(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/manual.db"))
    p = service.create("Manual", True)
    p["measurements"] = [row for row in p["measurements"] if row["key"] != "sleeve_length"]
    with pytest.raises(ValueError, match="at most 500.00 cm"):
        service.update_measurements(p, {"sleeve_length": 600}, "L")
    saved = service.update_measurements(p, {"sleeve_length": 300}, "L")
    row = next(row for row in saved["measurements"] if row["key"] == "sleeve_length")
    assert (row["source"], row["values"]["L"]["value"]) == ("Manual entry", 300)
