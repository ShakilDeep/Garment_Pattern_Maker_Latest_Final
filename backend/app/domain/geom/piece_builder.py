"""Build normalized V5 piece dictionaries from drafted outlines."""
from math import isfinite

from app.domain.geom.polyline_ops import area, length
from app.domain.geom.primitives import EPSILON


def make_piece(name, points, quantity=2, fold=False, seams=None):
    if points[-1] != points[0]:
        points = [*points, points[0]]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    points = [[round(x - x0, 6), round(y - y0, 6)] for x, y in points]
    width, height = max(p[0] for p in points), max(p[1] for p in points)
    if not all(isfinite(c) for p in points for c in p) or area(points) <= EPSILON:
        raise ValueError(f"{name}: invalid geometry")
    return {
        "id": name.lower().replace(" ", "_"),
        "name": name,
        "points": points,
        "quantity": quantity,
        "cut_on_fold": fold,
        "width": width,
        "height": height,
        "area": area(points),
        "perimeter": length(points),
        "grainline": [[width / 2, height * 0.35], [width / 2, height * 0.65]],
        "notches": [points[len(points) // 3]],
        "seams": seams or {},
    }


def unfold(half):
    return [*half, *[[-x, y] for x, y in reversed(half)][1:]]
