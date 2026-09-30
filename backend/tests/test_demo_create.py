"""Demo project creation must find shipped workbook/PDF assets."""

from pathlib import Path

import pytest
from app.application.service import demo_source_path


def test_demo_workbook_and_techpack_are_shipped():
    workbook = demo_source_path("Book2(4).xlsx")
    techpack = demo_source_path("1078983(5).pdf")
    assert workbook.is_file()
    assert techpack.is_file()
    assert workbook.stat().st_size > 1000
    assert techpack.stat().st_size > 1000
    assert "references" not in workbook.parts
    assert "demo_sources" in workbook.parts


def test_demo_create_imports_both_sources(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.main import create_app

    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("DEMO_SOURCES_DIR", str(root / "fixtures" / "demo_sources"))
    with TestClient(create_app(f"sqlite:///{tmp_path}/demo.db")) as client:
        response = client.post("/api/v1/projects", json={"name": "Demo", "demo": True})
    assert response.status_code == 200
    project = response.json()
    names = {d["filename"] for d in project["documents"]}
    assert "Book2(4).xlsx" in names
    assert "1078983(5).pdf" in names
    assert project["measurements"]
    assert project["techpack"]


def test_demo_source_path_ignores_references_folder(monkeypatch, tmp_path):
    fixtures = tmp_path / "fixtures" / "demo_sources"
    fixtures.mkdir(parents=True)
    (fixtures / "Book2(4).xlsx").write_bytes(b"fixture" * 400)
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "Book2(4).xlsx").write_bytes(b"reference-only" * 400)
    monkeypatch.delenv("DEMO_SOURCES_DIR", raising=False)
    monkeypatch.setattr("app.application.service.ROOT", tmp_path)
    path = demo_source_path("Book2(4).xlsx")
    assert path == fixtures / "Book2(4).xlsx"
    assert "references" not in path.parts


def test_demo_source_path_does_not_fall_back_to_references(monkeypatch, tmp_path):
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "Book2(4).xlsx").write_bytes(b"reference-only" * 400)
    monkeypatch.delenv("DEMO_SOURCES_DIR", raising=False)
    monkeypatch.setattr("app.application.service.ROOT", tmp_path)
    with pytest.raises(FileNotFoundError, match="fixtures/demo_sources"):
        demo_source_path("Book2(4).xlsx")
