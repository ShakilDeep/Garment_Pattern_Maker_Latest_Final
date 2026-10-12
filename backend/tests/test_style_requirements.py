"""T147: a confirmed sleeve or pocket the drafting block has no source for is Missing Information; nothing is drafted
for it and nothing fills it in (no client file gives short-sleeve POMs for shirt_v2 or any shirt pocket)."""
import pytest
from test_project_sizes import client  # noqa: F401 -- shared fixture

SHIRT = {"garment": "shirt", "fit": "regular"}


@pytest.fixture
def demo(client):  # noqa: F811
    pid = client.post("/api/v1/projects", json={"name": "Style", "demo": True}).json()["id"]
    return f"/api/v1/projects/{pid}"


def _confirm(client, base, **options):  # noqa: F811
    response = client.post(base + "/style/choices", json={**SHIRT, "options": options})
    assert response.status_code == 200, response.text


def _style_items(client, base):  # noqa: F811
    body = client.get(base + "/requirements").json()
    return body, {item["key"]: item for item in body["items"] if item["key"].startswith("style:")}


@pytest.mark.parametrize(("option", "value"), [("sleeve", "short"), ("pockets", "patch")])
def test_an_undrafted_variant_blocks_as_missing_information(client, demo, option, value):  # noqa: F811
    _confirm(client, demo, **{option: value})
    body, items = _style_items(client, demo)
    item = items[f"style:{option}"]
    assert (item["status"], item["blocking"], item["options"]) == ("MISSING", True, [])
    assert value in item["why"] and "shirt_v2" in item["why"]
    assert body["ready"] is False


@pytest.mark.parametrize("options", [{}, {"sleeve": "long", "pockets": "none"}, {"sleeve": "unknown"}])
def test_a_drafted_or_unknown_variant_adds_nothing(client, demo, options):  # noqa: F811
    _confirm(client, demo, **options)
    assert _style_items(client, demo)[1] == {}


def test_without_a_confirmed_style_there_is_no_item(client, demo):  # noqa: F811
    assert _style_items(client, demo)[1] == {}


def test_the_item_cannot_be_resolved_by_hand(client, demo):  # noqa: F811
    _confirm(client, demo, pockets="patch")
    response = client.post(demo + "/requirements/style:pockets/resolve", json={"value": "omit"})
    assert response.status_code == 400
    assert "style:pockets" in _style_items(client, demo)[1]
