"""Strict readers for the PDS ``SIZES_TABLE`` and ``PIECE`` elements."""
import re
from types import MappingProxyType
from xml.etree.ElementTree import Element

from app.domain.reference import GeomInfo, SizeTotals

_ROTATION = re.compile(r"\s*(-?\d+(?:\.\d+)?)\s*deg\.?\s*")
_GEOM_FIELDS = ("SIZE_X", "SIZE_Y", "AREA", "PERIMETER")
_SEW_FIELDS = ("SEW_AREA", "SEW_PERIMETER")
_TOTAL_FIELDS = ("SUM_AREA", "SUM_PERIMETER", "SUM_SEW_AREA", "SUM_SEW_PERIMETER")


def text(element: Element, path: str, default: str | None = None) -> str:
    found = element.find(path)
    if found is None:
        if default is not None:
            return default
        raise ValueError(f"PDS field missing: {path}")
    return (found.text or "").strip()


def number(raw: str, field: str) -> float:
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"PDS field {field} is not a number: {raw!r}") from None


def optional_attribute(element: Element, name: str) -> float | None:
    raw = element.get(name)
    return None if raw is None else number(raw, name)


def attribute(element: Element, name: str) -> float:
    value = optional_attribute(element, name)
    if value is None:
        raise ValueError(f"PDS field missing: {element.tag}/@{name}")
    return value


def size_table(style: Element) -> tuple[tuple[str, ...], str, MappingProxyType[str, SizeTotals]]:
    """Return (sizes in file order, base size, per-size totals)."""
    totals = {
        text(size, "NAME"): SizeTotals(*(number(text(size, field), field) for field in _TOTAL_FIELDS))
        for size in style.iterfind("SIZES_TABLE/SIZE")
    }
    base = text(style, "SIZES_TABLE/BASE_SIZE")
    if base not in totals:
        raise ValueError(f"PDS base size {base} is not in the size table")
    return tuple(totals), base, MappingProxyType(totals)


def piece_geometry(piece: Element) -> MappingProxyType[str, GeomInfo]:
    geometry = {}
    for size in piece.iterfind("SIZE"):
        info = size.find("GEOM_INFO")
        if info is None:
            raise ValueError("PDS field missing: PIECE/SIZE/GEOM_INFO")
        cut = (attribute(info, field) for field in _GEOM_FIELDS)
        sew = (optional_attribute(info, field) for field in _SEW_FIELDS)
        geometry[text(size, "NAME")] = GeomInfo(*cut, *sew)
    return MappingProxyType(geometry)


def piece_fields(piece: Element) -> dict:
    """Scalar piece attributes, ready to pass to ``ReferencePiece``."""
    nesting = piece.find("NESTING_ENABLES")
    rotation = _ROTATION.fullmatch(nesting.get("ROTATION", "") if nesting is not None else "")
    if rotation is None:
        raise ValueError("PDS field missing: PIECE/NESTING_ENABLES ROTATION")
    quantity = number(text(piece, "QUANTITY"), "QUANTITY")
    if quantity < 1 or not quantity.is_integer():
        raise ValueError(f"PDS piece QUANTITY must be a whole number of at least 1: {quantity}")
    return {
        "name": text(piece, "NAME"),
        "code": text(piece, "CODE", ""),
        "quantity": int(quantity),
        "on_fold": text(piece, "HALF", "") == "CLOSE",
        "rotation_deg": float(rotation[1]),
        "opposite": nesting.get("OPPOSITE", "None") if nesting is not None else "None",
    }
