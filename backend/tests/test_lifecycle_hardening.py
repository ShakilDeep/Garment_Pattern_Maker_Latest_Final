"""P0-06 / defect b: document archive/restore respect project archiving, invalidate, and gate readiness."""
from copy import deepcopy

from test_integrity import _ready

from app.application.readiness import check_operation
from app.application.service import Service
from app.application.source_lifecycle import archive_document, restore_document
from app.infrastructure.repository import Repository


def _document(client, url):
    return client.get(url).json()["documents"][0]


def test_restoring_a_document_invalidates_work_done_while_it_was_archived(tmp_path):
    service = Service(Repository(f"sqlite:///{tmp_path}/restore.db"))
    p = service.create("Restore", True)
    p["resolutions"] = {"units": "cm", "review": "confirmed", "profile": "demo_v1", "placket": "workbook"}
    service.generate(p, "L")
    service.grade(p, ["M"])
    pattern, grades = deepcopy(p["pattern"]), deepcopy(p["grades"])
    document_id = p["documents"][0]["id"]
    p = archive_document(service, p, document_id)
    p.update(pattern=pattern, grades=grades)
    restored = restore_document(service, p, document_id)
    assert restored["pattern"]["stale"] is True
    assert restored["grades"] == []
    assert restored["state"] == "MEASUREMENTS_READY"


def test_archiving_moves_to_needs_input_and_repeats_are_no_ops(tmp_path):
    client, url = _ready(tmp_path)
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    assert client.post(f"{url}/grade", json={"sizes": ["M"]}).status_code == 200
    document = _document(client, url)
    assert client.post(f"{url}/documents/{document['id']}/restore").status_code == 200
    assert len(client.get(url).json()["grades"]) == 1
    assert client.post(f"{url}/documents/{document['id']}/archive").status_code == 200
    audit = len(client.get(url).json()["audit"])
    assert client.post(f"{url}/documents/{document['id']}/archive").status_code == 200
    project = client.get(url).json()
    assert project["state"] == "NEEDS_INPUT"
    assert len(project["audit"]) == audit


def test_archived_project_documents_cannot_change(tmp_path):
    client, url = _ready(tmp_path)
    document = _document(client, url)
    assert client.post(f"{url}/archive").status_code == 200
    for action in ("archive", "restore"):
        response = client.post(f"{url}/documents/{document['id']}/{action}")
        assert response.status_code == 409
        assert "archived" in response.json()["message"]
    assert client.get(url).json()["documents"][0].get("active", True) is True


def test_export_readiness_reports_archived_sources(tmp_path):
    client, url = _ready(tmp_path)
    assert client.post(f"{url}/patterns/generate", json={"size": "L"}).status_code == 200
    document = _document(client, url)
    project = client.get(url).json()
    project["documents"][0]["active"] = False
    for operation in ("validate", "marker", "export"):
        check = check_operation(project, operation, "L", 150, {"L": 1}, "vertical")
        assert f"source:{document['id']}" in [item["key"] for item in check["blockers"]]
    assert check_operation(client.get(url).json(), "export", "L")["ready"] is True
