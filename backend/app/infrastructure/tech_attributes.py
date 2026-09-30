"""Strategy: local text candidates with source evidence, never inferred geometry."""
import re

VERSION = "local_text_v2"
REQUIRED_KEYS = ("garment_weight", "fabric_category", "sleeve_type", "placket_width")
FIELDS = {
    "garment_weight": r"GARMENT WEIGHT:\s*(\d+\s*GR)",
    "fabric_category": r"FABRIC:\s*(WOVEN|KNITTED|KNIT)",
    "wash": r"WASH:\s*([^\n]+)",
    "sleeve_type": r"(LONG SLEEVE)",
    "collar_code": r"(CL\d+\s+CODE)",
    "placket_width": r"PLACKET\s+(\d+[,.]\d+\s*CM)",
}


def document_confidence(attributes):
    if not attributes:
        return 0.4
    return round(sum(item["confidence"] for item in attributes) / len(attributes), 3)


class LocalTextExtractor:
    """Concrete AttributeExtractor; regex candidates only."""

    def extract(self, pages, filename):
        attributes = []

        def add(category, key, value, raw, page, confidence):
            attributes.append({
                "category": category, "key": key, "value": value, "raw": raw, "page": page,
                "source": filename, "parser_version": VERSION, "confidence": confidence,
                "status": "NEEDS_REVIEW",
            })

        for page in pages:
            text = page["text"]
            for key, expression in FIELDS.items():
                for match in re.finditer(expression, text, re.IGNORECASE):
                    kind = "construction" if key in ("collar_code", "placket_width") else "garment"
                    add(kind, key, match[1], match[0], page["page"], 0.92)
            _collect_line_notes(page, add)
        found = {item["key"] for item in attributes}
        issues = [_missing(key, filename) for key in REQUIRED_KEYS if key not in found]
        return attributes, issues


def _missing(key, filename):
    return {
        "key": key, "severity": "WARNING", "page": None, "source": filename,
        "parser_version": VERSION,
        "why": f"Tech pack did not contain extractable {key}; review source pages.",
    }


def _collect_line_notes(page, add):
    lines = page["text"].splitlines()
    text = page["text"]
    for i, line in enumerate(lines):
        if "BILL OF MATERIALS" in text and re.search(
            r"PLASTIC BUTTON|SLEEVE PLACKET BINDING|ALARM:|FLAG LABEL:|WOVEN (MAIN|FIT) LABEL|HANGTAG;",
            line,
        ):
            add("bom", f"bom_{page['page']}_{i}", line, "\n".join(lines[i:i + 3]), page["page"], 0.68)
        elif re.search(r"TOP STITCH|CUFF AS|PLEAT|LOCK STITCH|NEEDLE", line):
            add("construction", f"note_{page['page']}_{i}", line, "\n".join(lines[i:i + 3]), page["page"], 0.68)
        elif re.search(r"COTTON|ELASTANE|GSM|POPELINE|DOBBY|SOLID DYED", line):
            add("fabric", f"fabric_{page['page']}_{i}", line, line, page["page"], 0.68)
