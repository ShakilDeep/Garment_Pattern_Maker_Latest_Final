"""Classify and convert the marker-view SVG elements of a PDS into centimetre geometry.

The SVG uses 0.01 cm units with y pointing down; results are cm with y pointing up.
"""
import re
from enum import Enum
from xml.etree.ElementTree import Element

from app.domain.reference import Point, Polyline

SVG_UNITS_PER_CM = 100.0
_NUMBER = r"-?\d+(?:\.\d+)?"
_PAIR = re.compile(rf"({_NUMBER})[ ,]({_NUMBER})")
_PATH = re.compile(rf"(?:\s*[ML]\s*{_NUMBER}[ ,]{_NUMBER})+\s*(Z\s*)?")
_FILL = re.compile(r"fill:\s*(#[0-9A-Fa-f]{6})")


class Mark(Enum):
    CLOTH = "cloth"
    CUT = "cut"
    SEW = "sew"
    FOLD = "fold"
    NOTCH = "notch"


_POLYGON_FILLS = {"#CCCC33": Mark.CLOTH, "#FFBE46": Mark.CUT}
_GROUP_FILLS = {"#000000": Mark.SEW, "#FF6633": Mark.FOLD, "#0000FF": Mark.NOTCH}


def classify(element: Element) -> Mark:
    """Strategy table: (tag, fill colour) -> mark kind; unknown colours are rejected, not dropped."""
    if element.tag == "polygon":
        fill, table = (element.get("fill") or "").upper(), _POLYGON_FILLS
    else:
        found = _FILL.search(element.get("style", ""))
        fill, table = (found[1].upper() if found else ""), _GROUP_FILLS
    if fill not in table:
        raise ValueError(f"Unsupported PDS SVG {element.tag} colour {fill or 'none'}")
    return table[fill]


def _to_cm(x: str, y: str) -> Point:
    return round(float(x) / SVG_UNITS_PER_CM, 6), round(-float(y) / SVG_UNITS_PER_CM, 6)


def cut_ring(element: Element) -> Polyline:
    """Polygon ``points`` as a counter-clockwise ring without a repeated closing point."""
    ring = [_to_cm(x, y) for x, y in _PAIR.findall(element.get("points", ""))]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        raise ValueError("PDS cut outline has fewer than 3 points")
    doubled_area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))
    return tuple(ring if doubled_area > 0 else reversed(ring))


def polyline(path: Element) -> Polyline:
    """A path of absolute move/line commands; a closing ``Z`` repeats the first point."""
    data = path.get("d", "")
    match = _PATH.fullmatch(data)
    if match is None:
        raise ValueError(f"Unsupported SVG path data: {data[:40]!r}")
    points = [_to_cm(x, y) for x, y in _PAIR.findall(data)]
    if len(points) < 2:
        raise ValueError(f"PDS SVG path has fewer than 2 points: {data[:40]!r}")
    return tuple(points + points[:1] if match[1] else points)
