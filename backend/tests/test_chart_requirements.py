"""T126b: unmapped POMs and an unknown base size go to Missing Information; nothing is guessed."""
from pom_workbooks import CL1086464, workbook_bytes
from test_project_sizes import client, pant, project  # noqa: F401 -- shared fixtures

from app.application.pattern_inputs import drafting_values

UNKNOWN = workbook_bytes(("Chart", [
    ["Codes", "MEASUREMENTS POINTS", "S", "M"],
    ["A1", "1/2 WAIST", 35, 37],
    ["Z9", "MYSTERY POINT", 1, 2],
]))


def _items(client, base, size="S"):  # noqa: F811
    return {item["key"]: item for item in client.get(base + "/requirements", params={"size": size}).json()["items"]}


def test_an_unmapped_pom_is_listed_but_does_not_block(client):  # noqa: F811
    items = _items(client, project(client, workbook=UNKNOWN))
    item = items["mapping:3"]
    assert (item["status"], item["blocking"], item["category"]) == ("MISSING", False, "Measurements")
    assert "MYSTERY POINT" in item["why"]
    assert "mapping:2" not in items


def test_an_unknown_base_size_is_asked_for(client):  # noqa: F811
    base = project(client, workbook=UNKNOWN)
    item = _items(client, base)["base_size"]
    assert (item["status"], item["blocking"], item["options"]) == ("AMBIGUOUS", False, ["S", "M"])
    assert client.post(base + "/requirements/base_size/resolve", json={"value": "4XL"}).status_code == 400
    assert client.post(base + "/requirements/base_size/resolve", json={"value": "M"}).status_code == 200
    assert _items(client, base)["base_size"]["resolved"] is True


def test_a_fully_mapped_chart_with_a_base_adds_no_items(client, pant):  # noqa: F811
    items = _items(client, pant)
    assert not [key for key in items if key.startswith("mapping:") or key == "base_size"]


def test_clearing_sources_removes_the_chart(client, pant):  # noqa: F811
    assert client.post(pant + "/sources/clear").json()["chart"] is None
    assert client.post(pant + "/documents", files={"file": ("CL1086464.xlsx", CL1086464.read_bytes(),
                       "application/octet-stream")}).json()["chart"]["sizes"][0] == "XS"


def test_unmapped_rows_never_reach_drafting():
    project_data = {"measurements": [
        {"key": "Z9", "mapping_status": "unmapped", "values": {"S": {"value": 1}}},
        {"key": "half_chest", "mapping_status": "catalog", "values": {"S": {"value": 50}}},
        {"key": "manual_entry", "values": {"S": {"value": 2}}},
        {"key": "half_waist", "mapping_status": "synonym", "values": {"S": {"value": None}}},
    ]}
    assert drafting_values(project_data, "S") == {"half_chest": 50, "manual_entry": 2}


def test_the_users_base_size_choice_wins_over_the_detected_one():
    from app.application.project_sizes import base_size

    chart = {"sizes": ["S", "M"], "base_size": "S"}
    assert base_size({"chart": chart, "resolutions": {}}) == "S"
    assert base_size({"chart": chart, "resolutions": {"base_size": "M"}}) == "M"


def test_grade_readiness_does_not_need_a_single_size(client):  # noqa: F811
    kids = workbook_bytes(("Chart", [["Codes", "MEASUREMENTS POINTS", 4, "4½"], ["A1", "1/2 WAIST", 30, 31]]))
    base = project(client, workbook=kids)
    response = client.post(base + "/requirements/check", json={"target_operation": "grade"})
    assert response.status_code == 200, response.text
