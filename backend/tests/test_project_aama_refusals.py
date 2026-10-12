"""T146 (shirt): the project Optitex export needs every size graded; other exports are unchanged."""
from fastapi.testclient import TestClient
from named_project import shirt_project
from test_integrity import _ready

from app.api.main import create_app


def test_an_ungraded_project_is_refused_naming_the_missing_sizes(tmp_path):
    _, project = shirt_project(tmp_path, graded=False)
    client = TestClient(create_app(f"sqlite:///{tmp_path}/named.db"))
    response = client.get(f"/api/v1/projects/{project['id']}/exports/aama-graded")
    body = response.json()
    assert response.status_code == 409 and body["code"] == "REQUIREMENTS_NOT_READY"
    assert "Grade every size before the Optitex export; missing S, M, XL, XXL, 3XL" in body["message"]


def test_a_project_without_a_pattern_is_refused(tmp_path):
    client, url = _ready(tmp_path)
    response = client.get(f"{url}/exports/aama-graded")
    assert response.status_code == 409
    assert response.json()["message"] == "Generate a current pattern before the Optitex export"


def test_the_post_route_accepts_the_new_kind_and_single_size_aama_is_unchanged(tmp_path):
    client, url = _ready(tmp_path)
    client.post(f"{url}/patterns/generate", json={"size": "L"})
    assert client.post(f"{url}/exports", json={"kind": "aama-graded"}).status_code == 409  # demo: L only
    assert client.get(f"{url}/exports/dxf-aama").status_code == 200
