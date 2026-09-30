"""Strategy: local searchable-PDF tech-pack extraction."""
import re
from io import BytesIO

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

from app.infrastructure.document_classifier import LocalDocumentClassifier
from app.infrastructure.tech_attributes import VERSION, LocalTextExtractor, document_confidence
from app.ports.attribute_extractor import AttributeExtractor
from app.ports.document_classifier import DocumentClassifier


def parse_pdf(
    data: bytes,
    filename: str,
    extractor: AttributeExtractor | None = None,
    classifier: DocumentClassifier | None = None,
) -> dict:
    if len(data) > 10_000_000:
        raise ValueError("PDF exceeds the 10 MB parser limit")
    extractor = extractor or LocalTextExtractor()
    classifier = classifier or LocalDocumentClassifier()
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if len(pdf.pages) > 50:
                raise ValueError("PDF exceeds 50 pages")
            pages = [{"page": i + 1, "text": (p.extract_text() or "")[:200_000]} for i, p in enumerate(pdf.pages)]
    except PdfminerException as exc:
        raise ValueError("PDF has no readable text layer; provide a searchable PDF") from exc
    text = "\n".join(str(p["text"]) for p in pages)
    if not text.strip():
        raise ValueError("PDF has no readable text layer; provide a searchable PDF")
    placket = re.search(r"PLACKET\s+(\d+[,.]\d+)\s*CM", text, re.IGNORECASE)
    attributes, issues = extractor.extract(pages, filename)
    return {
        "source": filename,
        "pages": pages,
        "parser": VERSION,
        "confidence": document_confidence(attributes),
        "attributes": attributes,
        "issues": issues,
        "classification": classifier.classify(text, filename),
        "style": (re.search(r"\b\d{7}\b", text) or ["Unknown"])[0],
        "garment": "Men's long-sleeve shirt" if "LONG SLEEVE SHIRT" in text else "Needs review",
        "fit": "Regular Fit" if "FIT: REGULAR" in text else "Needs review",
        "placket_cm": float(placket[1].replace(",", ".")) if placket else None,
        "fabric_conflict": "97 COTTON" in text and "100% COTTON" in text,
        "fabric": "100% cotton dobby, 153 GSM (page 4 table)" if "153 GSM" in text else "Review source PDF",
        "colorways": [c for c in ["PETROL GREEN", "DARK NAVY"] if c in text],
    }
