"""Local keyword classification. Labels only; no measurements or geometry."""

LABELS = {
    "garment": ("LONG SLEEVE SHIRT", "shirt"),
    "document": ("TECH PACK", "tech_pack"),
}


def classify_text(text: str) -> dict:
    upper = text.upper()
    garment = "shirt" if LABELS["garment"][0] in upper else "unclassified"
    document = "tech_pack" if LABELS["document"][0] in upper else "unclassified"
    known = garment != "unclassified" or document != "unclassified"
    return {
        "garment": garment,
        "document": document,
        "confidence": 0.6 if known else 0.2,
        "evidence": "local-keyword",
    }


class LocalDocumentClassifier:
    def classify(self, text, filename):
        return classify_text(text)
