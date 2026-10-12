"""T143: accuracy errors block the geometry exports (409 ACCURACY_ERRORS); the JSON backup still downloads."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from named_project import shirt_project

from app.api.main import create_app
from app.application.project_style import project_style
from app.domain.pattern.style_codec import style_to_json


def _client(path) -> TestClient:
    return TestClient(create_app(f"sqlite:///{path}/named.db"))


def _corrupt(service, project) -> None:
    """Store the 3XL pieces as size S, as a size drafted from the wrong measurements would be."""
    style = project_style(project)
    project["style"] = style_to_json(replace(style, geometry={**style.geometry, "S": style.geometry["3XL"]}))
    service.repo.save(project, "test_corrupt_style")


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    path = tmp_path_factory.mktemp("clean")
    _, project = shirt_project(path)
    return _client(path), f"/api/v1/projects/{project['id']}", project["id"]


@pytest.fixture(scope="module")
def broken(tmp_path_factory):
    path = tmp_path_factory.mktemp("broken")
    service, project = shirt_project(path)
    _corrupt(service, project)
    return _client(path), f"/api/v1/projects/{project['id']}", project["id"]


def test_the_report_lists_the_errors(broken):
    client, url, _ = broken
    report = client.get(f"{url}/accuracy").json()
    assert report["status"] == "errors" and report["error_count"] > 0
    failed = {check["name"] for check in report["checks"] if check["gate"] and not check["passed"]}
    assert {"S SUM_AREA", "areas grow size to size"} <= failed


@pytest.mark.parametrize("kind", ["dxf-aama", "svg", "pdf", "dxf"])
def test_geometry_exports_are_refused_with_the_failed_checks(broken, kind):
    client, url, _ = broken
    response = client.get(f"{url}/exports/{kind}")
    body = response.json()
    assert (response.status_code, body["code"]) == (409, "ACCURACY_ERRORS")
    assert "S SUM_AREA" in {item["name"] for item in body["details"]}


def test_the_json_backup_still_exports(broken):
    client, url, _ = broken
    assert client.get(f"{url}/exports/json").status_code == 200


def test_the_optitex_zip_is_refused(broken):
    client, _, pid = broken
    style_id = client.post("/api/v1/styles", json={"project_id": pid}).json()["id"]
    response = client.get(f"/api/v1/styles/{style_id}/export/aama")
    assert (response.status_code, response.json()["code"]) == (409, "ACCURACY_ERRORS")


def test_readiness_names_the_accuracy_blocker(broken):
    client, url, _ = broken
    check = client.post(f"{url}/requirements/check", json={"target_operation": "export", "size": "L"}).json()
    assert "accuracy" in {item["key"] for item in check["blockers"]}


def test_an_accurate_project_exports(clean):
    client, url, pid = clean
    assert client.get(f"{url}/exports/dxf-aama").status_code == 200
    style_id = client.post("/api/v1/styles", json={"project_id": pid}).json()["id"]
    assert client.get(f"/api/v1/styles/{style_id}/export/aama").status_code == 200
    check = client.post(f"{url}/requirements/check", json={"target_operation": "export", "size": "L"}).json()
    assert check["ready"], check["blockers"]
