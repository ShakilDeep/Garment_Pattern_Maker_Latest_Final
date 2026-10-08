"""T126b / P1-18: a project's size list is data from its chart; sizes outside it are rejected (422)."""
import pytest
from fastapi.testclient import TestClient
from pom_workbooks import CL1086464

from app.api.main import create_app

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PANT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/sizes.db")) as test_client:
        yield test_client


def project(client, *, demo=False, workbook=None, filename="chart.xlsx"):
    created = client.post("/api/v1/projects", json={"name": "Sizes", "demo": demo}).json()
    base = f"/api/v1/projects/{created['id']}"
    if workbook is not None:
        response = client.post(base + "/documents", files={"file": (filename, workbook, XLSX)})
        assert response.status_code == 200, response.text
    return base


@pytest.fixture
def pant(client):
    return project(client, workbook=CL1086464.read_bytes(), filename="CL1086464.xlsx")


def test_the_pant_project_takes_its_sizes_and_base_from_the_chart(client, pant):
    chart = client.get(pant).json()["chart"]
    assert chart["sizes"] == PANT_SIZES
    assert chart["base_size"] == "S"
    assert chart["meta"]["description"] == "pant"


def test_a_size_from_the_chart_can_be_edited(client, pant):
    response = client.patch(pant + "/measurements", json={"size": "XS", "changes": {"half_waist": 33.5}})
    assert response.status_code == 200, response.text
    waist = next(row for row in response.json()["measurements"] if row["key"] == "half_waist")
    assert waist["values"]["XS"]["value"] == 33.5


def test_a_chart_size_reaches_the_requirements_instead_of_failing_validation(client, pant):
    assert client.get(pant + "/requirements", params={"size": "XS"}).status_code == 200
    response = client.post(pant + "/patterns/generate", json={"size": "XS"})
    assert response.status_code == 409, response.text


@pytest.mark.parametrize(("method", "path", "body"), [
    ("patch", "/measurements", {"size": "4XL", "changes": {"half_waist": 30}}),
    ("post", "/patterns/generate", {"size": "4XL"}),
    ("post", "/grade", {"sizes": ["XS", "4XL"]}),
    ("post", "/requirements/check", {"target_operation": "generate", "size": "4XL"}),
    ("get", "/requirements?size=4XL", None),
    ("get", "/requirements/queue?size=4XL", None),
])
def test_sizes_outside_the_chart_are_rejected(client, pant, method, path, body):
    response = getattr(client, method)(pant + path, **({"json": body} if body is not None else {}))
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "SIZE_UNKNOWN"
    assert "XS, S, M, L, XL, XXL" in response.json()["message"]


def test_the_demo_project_keeps_s_to_3xl(client):
    demo = project(client, demo=True)
    assert client.get(demo).json()["chart"]["sizes"] == ["S", "M", "L", "XL", "XXL", "3XL"]
    response = client.post(demo + "/patterns/generate", json={"size": "XS"})
    assert (response.status_code, response.json()["code"]) == (422, "SIZE_UNKNOWN")


def test_a_project_without_a_chart_falls_back_to_the_demo_sizes(client):
    blank = project(client)
    assert client.get(blank).json().get("chart") is None
    assert client.get(blank + "/requirements", params={"size": "3XL"}).status_code == 200
    assert client.get(blank + "/requirements", params={"size": "XS"}).status_code == 422
