"""Pure helpers for point-of-measure (POM) names and size labels from buyers' spec sheets."""
import re
import unicodedata

_SPACES = re.compile(r"\s+")
_HALF = re.compile(r"(^|[\s-])(1/2|HALF)([\s-]|$)")
_EDGE_MARKS = "*-:· "


def normalize(name: object) -> str:
    """Comparable form of a POM name: NFKC, ½ as 1/2, upper case, single spaces, no edge marks."""
    text = unicodedata.normalize("NFKC", str(name or "")).replace("⁄", "/")
    return _SPACES.sub(" ", text.upper()).strip(_EDGE_MARKS)


def is_half(name: object) -> bool:
    """True only when the name itself says the measurement is a half (never inferred from values)."""
    return bool(_HALF.search(normalize(name)))


def size_label(value: object) -> str:
    """Header cell -> size label: 4.0 -> "4", " XS " -> "XS", "4½" stays "4½"."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()
