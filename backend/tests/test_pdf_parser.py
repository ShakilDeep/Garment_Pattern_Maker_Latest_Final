"""PDF parser replacement, unreadable files, and document confidence."""
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from app.api.main import create_app
from app.infrastructure.parsers import parse_pdf

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "references" / "1078983(5).pdf"
UNREADABLE = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _text_pdf(text: str) -> bytes:
    buffer = BytesIO()
    page = Canvas(buffer)
    page.drawString(72, 720, text)
    page.save()
    return buffer.getvalue()


def test_techpack_reports_document_confidence():
    tech = parse_pdf(PDF.read_bytes(), "tech.pdf")
    assert 0 < tech["confidence"] <= 1
    assert all(0 <= item["confidence"] <= 1 for item in tech["attributes"])


def test_unreadable_pdf_raises_value_error():
    with pytest.raises(ValueError, match="searchable|valid|unencrypted|readable"):
        parse_pdf(UNREADABLE, "broken.pdf")


def test_pdf_replace_keeps_prior_techpack_version(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/pdf.db"))
    pid = client.post("/api/v1/projects", json={"name": "Pdf", "demo": True}).json()["id"]
    url = f"/api/v1/projects/{pid}/documents"
    blocked = client.post(
        url, files={"file": ("again.pdf", PDF.read_bytes(), "application/pdf")}
    )
    assert blocked.status_code == 409
    replaced = client.post(
        url,
        params={"replace": True},
        files={"file": ("again.pdf", PDF.read_bytes(), "application/pdf")},
    )
    project = client.get(f"/api/v1/projects/{pid}").json()
    parse = client.get(f"/api/v1/projects/{pid}/parse").json()
    assert replaced.status_code == 200
    assert len(project["techpack_versions"]) == 1
    assert project["techpack"]["confidence"] > 0
    assert parse["techpack_confidence"] == project["techpack"]["confidence"]
    assert "issues" in parse


def test_missing_construction_fields_emit_issues_not_geometry():
    tech = parse_pdf(_text_pdf("LONG SLEEVE SHIRT"), "notes.pdf")
    assert tech["placket_cm"] is None
    keys = {item["key"] for item in tech["issues"]}
    assert "placket_width" in keys
    assert "fabric_category" in keys
    assert all(item.get("why") and item.get("source") == "notes.pdf" for item in tech["issues"])


def test_parse_status_includes_techpack_issues(tmp_path):
    client = TestClient(create_app(f"sqlite:///{tmp_path}/issues.db"))
    pid = client.post("/api/v1/projects", json={"name": "Issues"}).json()["id"]
    upload = client.post(
        f"/api/v1/projects/{pid}/documents",
        files={"file": ("notes.pdf", _text_pdf("LONG SLEEVE SHIRT"), "application/pdf")},
    )
    parse = client.get(f"/api/v1/projects/{pid}/parse").json()
    assert upload.status_code == 200
    assert any("placket_width" in str(item) for item in parse["issues"])


def test_local_extractor_is_attribute_extractor_strategy():
    from app.infrastructure.tech_attributes import LocalTextExtractor
    from app.ports.attribute_extractor import AttributeExtractor

    assert isinstance(LocalTextExtractor(), AttributeExtractor)
