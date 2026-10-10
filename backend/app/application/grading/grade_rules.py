"""Per-point grade rules matched by name across sizes (T131, P1-19).

Every size is re-drafted from its own measurements, so a named point's grade rule is simply where it moved
from the base size in each size; points keep their names in every size, so no matching search is needed.
Points that move alike share one rule; rules are numbered from 1 in first-seen order (AAMA ``DELTA n``).
"""
from collections.abc import Mapping
from dataclasses import dataclass, replace

from app.domain.geom.primitives import Point2D
from app.domain.interchange import GradeRuleTable
from app.domain.pattern.ids import GradeRuleId, PieceId, PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.point import quantize
from app.domain.pattern.style import Style

Key = tuple[PieceId, PointId]


@dataclass(frozen=True)
class StyleRules:
    table: GradeRuleTable
    by_point: Mapping[Key, int]  # rule number, 1-based


def _positions(style: Style, size: str) -> dict[Key, Point2D]:
    return {(piece.id, point.id): point.position for piece in style.view(size) for point in piece.points}


def _move(sizes: Mapping[str, Mapping[Key, Point2D]], key: Key, at: Point2D) -> tuple[tuple[float, float], ...]:
    row = []
    for size, positions in sizes.items():
        if key not in positions:
            raise ValueError(f"{key[0]} has no point {key[1]} in size {size}")
        moved = positions[key]
        row.append((quantize(moved.x - at.x), quantize(moved.y - at.y)))
    return tuple(row)


def rules_from_positions(name: str, sizes: Mapping[str, Mapping[Key, Point2D]], base_size: str) -> StyleRules:
    """Grade rules for any per-size positions of the same keys (named points, cut corners...)."""
    numbers: dict[tuple[tuple[float, float], ...], int] = {}
    by_point = {key: numbers.setdefault(_move(sizes, key, at), len(numbers) + 1)
                for key, at in sizes[base_size].items()}
    return StyleRules(GradeRuleTable(name, tuple(sizes), base_size, tuple(numbers)), by_point)


def require_graded(style: Style) -> None:
    missing = [size for size in style.sizes if not style.has_geometry(size)]
    if missing:
        raise ValueError(f"Grade rules need every size drafted; missing {', '.join(missing)}")


def grade_rules(style: Style) -> StyleRules:
    require_graded(style)
    return rules_from_positions(style.name, {size: _positions(style, size) for size in style.sizes}, style.base_size)


def _ruled(piece: Piece, rules: StyleRules) -> Piece:
    points = tuple(replace(point, grade_rule=GradeRuleId(f"R{rules.by_point[(piece.id, point.id)]}"))
                   for point in piece.points)
    return replace(piece, points=points)


def with_grade_rules(style: Style, rules: StyleRules) -> Style:
    """The style with every base-size point carrying its rule id (``R<number>``)."""
    return style.with_pieces(style.base_size, [_ruled(piece, rules) for piece in style.view(style.base_size)])
