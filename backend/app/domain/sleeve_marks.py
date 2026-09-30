"""Strategy: demo_v1 sleeve placket/pleat marks on the cut outline."""
from itertools import pairwise
from math import hypot


def _same(a, b):
    return hypot(a[0] - b[0], a[1] - b[1]) <= 1e-6


def _along(start, end, distance):
    dx, dy = end[0] - start[0], end[1] - start[1]
    span = hypot(dx, dy) or 1.0
    t = min(max(distance / span, 0.0), 1.0)
    return [round(start[0] + dx * t, 6), round(start[1] + dy * t, 6)]


def sleeve_marks(points, placket_length, pleat_depth):
    wrist_y = max(point[1] for point in points)
    wrist = [point for point in points if abs(point[1] - wrist_y) <= 1e-6]
    right = max(wrist, key=lambda point: point[0])
    left = min(wrist, key=lambda point: point[0])
    cap_side = None
    for start, end in pairwise(points):
        if _same(end, right) and start[1] + 1e-6 < end[1]:
            cap_side = start
            break
        if _same(start, right) and end[1] + 1e-6 < start[1]:
            cap_side = end
            break
    if cap_side is None:
        raise ValueError("Sleeve outline has no underarm edge from the wrist")
    return (
        {"kind": "placket", "point": _along(right, cap_side, placket_length)},
        {"kind": "pleat", "point": _along(right, left, pleat_depth)},
    )


def apply_sleeve_marks(piece, measurements):
    marks = sleeve_marks(
        piece["points"],
        measurements["sleeve_placket_length"],
        measurements.get("sleeve_pleat_depth") or 0,
    )
    piece["marks"] = list(marks)
    piece["notches"] = [mark["point"] for mark in marks]
    return piece
