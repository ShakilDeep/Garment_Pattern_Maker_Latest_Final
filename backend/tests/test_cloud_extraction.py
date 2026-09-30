"""Optional cloud extraction must be injected, mocked, and must not invent values."""
import pytest

from app.infrastructure.ai_provider import LocalAIProvider
from app.infrastructure.cloud_extractor import CloudAttributeExtractor
from app.infrastructure.parsers import parse_pdf
from app.infrastructure.provider_factory import get_ai_provider
from tests.test_pdf_parser import _text_pdf


class _Client:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.payload


def test_cloud_extractor_keeps_only_values_present_in_source_text():
    pages = [{"page": 1, "text": "GARMENT WEIGHT: 228 GR"}]
    client = _Client({
        "attributes": [
            {"key": "garment_weight", "value": "228 GR"},
            {"key": "chest", "value": "99.0"},
        ]
    })
    extractor = CloudAttributeExtractor(client, "secret", "https://example.test/extract")
    attributes, issues = extractor.extract(pages, "pack.pdf")
    assert [item["value"] for item in attributes] == ["228 GR"]
    assert any("chest" in item["why"] for item in issues)
    assert "99.0" not in str(attributes)
    assert client.calls[0]["headers"]["Authorization"] == "Bearer secret"


def test_cloud_extractor_requires_configuration():
    with pytest.raises(ValueError, match="not configured"):
        CloudAttributeExtractor(_Client({}), "", "https://example.test/extract")


def test_parse_pdf_uses_injected_cloud_extractor_without_network():
    client = _Client({"attributes": [{"key": "sleeve_type", "value": "LONG SLEEVE"}]})
    extractor = CloudAttributeExtractor(client, "k", "https://example.test/extract")
    tech = parse_pdf(_text_pdf("LONG SLEEVE SHIRT"), "notes.pdf", extractor=extractor)
    assert any(item["key"] == "sleeve_type" for item in tech["attributes"])
    assert client.calls


def test_provider_factory_stays_local_without_cloud_credentials(monkeypatch):
    monkeypatch.delenv("GARMENT_CLOUD_AI_KEY", raising=False)
    assert isinstance(get_ai_provider(), LocalAIProvider)
