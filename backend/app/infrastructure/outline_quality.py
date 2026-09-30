"""Outline turning-angle and flattening policy from documented tolerances."""
from math import atan2, degrees, hypot, pi, tau

from app.domain.tolerances import ANGLE_DEGREES, LENGTH_CM


def _turn_degrees(a, b, c):
    incoming = atan2(b[1] - a[1], b[0] - a[0])
    outgoing = atan2(c[1] - b[1], c[0] - b[0])
    delta = (outgoing - incoming + pi) % tau - pi
    return abs(degrees(delta))


def outline_quality(pattern):
    issues = []
    for piece in pattern.get("pieces", []):
        points = piece.get("points") or []
        if len(points) < 4:
            continue
        vertices = points[:-1] if points[0] == points[-1] else points
        count = len(vertices)
        for index in range(count):
            start, vertex, end = vertices[index - 1], vertices[index], vertices[(index + 1) % count]
            first = hypot(vertex[0] - start[0], vertex[1] - start[1])
            second = hypot(end[0] - vertex[0], end[1] - vertex[1])
            if min(first, second) <= LENGTH_CM:
                continue
            turn = _turn_degrees(start, vertex, end)
            if turn <= ANGLE_DEGREES:
                issues.append({
                    "code": "FLATTENING", "severity": "WARNING", "piece": piece["name"],
                    "actual": turn, "expected": ANGLE_DEGREES, "tolerance": ANGLE_DEGREES,
                    "message": f"{piece['name']}: nearly collinear vertex (turn {turn:.3f}°)",
                })
            if abs(turn - 180) <= ANGLE_DEGREES:
                issues.append({
                    "code": "TURN_ANGLE", "severity": "WARNING", "piece": piece["name"],
                    "actual": turn, "expected": 180, "tolerance": ANGLE_DEGREES,
                    "message": f"{piece['name']}: spike turn {turn:.3f}° at a vertex",
                })
    return issues
