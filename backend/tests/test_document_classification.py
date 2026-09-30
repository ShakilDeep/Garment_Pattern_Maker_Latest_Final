"""Document/garment classification is an injectable Strategy; never invents measurements."""
from app.infrastructure.parsers import parse_pdf
from tests.test_pdf_parser import _text_pdf


def test_injected_classifier_does_not_change_extracted_fields():
    class FixedClassifier:
        def classify(self, text, filename):
            return {
                "garment": "unclassified",
                "document": "tech_pack",
                "confidence": 0.4,
                "evidence": "injected",
            }

    tech = parse_pdf(_text_pdf("LONG SLEEVE SHIRT"), "notes.pdf", classifier=FixedClassifier())
    assert tech["classification"]["evidence"] == "injected"
    assert tech["classification"]["garment"] == "unclassified"
    assert tech["placket_cm"] is None
    assert tech["garment"] == "Men's long-sleeve shirt"


def test_unknown_text_is_unclassified_not_a_shirt():
    from app.infrastructure.document_classifier import LocalDocumentClassifier

    result = LocalDocumentClassifier().classify("invoice 42", "inv.pdf")
    assert result["garment"] == "unclassified"
    assert result["document"] == "unclassified"
    assert result["confidence"] < 0.5


def test_local_classifier_is_document_classifier_strategy():
    from app.infrastructure.document_classifier import LocalDocumentClassifier
    from app.ports.document_classifier import DocumentClassifier

    assert isinstance(LocalDocumentClassifier(), DocumentClassifier)
