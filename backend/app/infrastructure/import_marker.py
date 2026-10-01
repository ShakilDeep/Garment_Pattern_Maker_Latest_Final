"""Import validator for an optional marker: placements lie on the fabric and reference imported versions."""
from math import isfinite

from app.application.errors import ImportInvalid
from app.domain.geometry import EPSILON

MIN_POLYGON_POINTS = 3


def _invalid(message):
    return ImportInvalid("IMPORT_MARKER_INVALID", message)


def number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


def is_polygon(points):
    return isinstance(points, list) and len(points) >= MIN_POLYGON_POINTS and all(
        isinstance(point, list) and len(point) == 2 and all(number(v) for v in point) for point in points)


def _on_fabric(placed, width, length):
    if not isinstance(placed, dict) or not isinstance(placed.get("name"), str):
        return False
    if not (number(placed.get("x")) and number(placed.get("y")) and is_polygon(placed.get("points"))):
        return False
    xs = [placed["x"] + x for x, _ in placed["points"]]
    ys = [placed["y"] + y for _, y in placed["points"]]
    return min(xs) >= -EPSILON and min(ys) >= -EPSILON and max(xs) <= width + EPSILON and max(ys) <= length + EPSILON


def _check_provenance(marker, body):
    size_by_id = {version["id"]: version.get("size") for version in (body.pattern, *body.grades)
                  if isinstance(version.get("id"), str)}
    pattern_ids = marker.get("pattern_ids")
    if not isinstance(pattern_ids, dict) or not pattern_ids or any(
            not isinstance(pid, str) or size_by_id.get(pid) != size for size, pid in pattern_ids.items()):
        raise _invalid("Imported marker must reference imported pattern versions of the same size")


def check_marker(body):
    marker = body.marker
    if marker is None:
        return
    width, length = marker.get("width"), marker.get("length")
    if not (number(width) and number(length) and width > 0 and length > 0):
        raise _invalid("Imported marker needs a positive fabric width and length")
    placements = marker.get("placements")
    if not isinstance(placements, list) or not placements:
        raise _invalid("Imported marker placements must be a non-empty list")
    if not all(_on_fabric(placed, width, length) for placed in placements):
        raise _invalid("Imported marker placements must be polygons inside the fabric")
    _check_provenance(marker, body)
