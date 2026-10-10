"""T131 / P1-19: per-point grade rules derived by matching named points across the drafted sizes."""
import pytest

from app.application.cad.style_from_block import style_from_block
from app.application.grading.grade_rules import grade_rules, with_grade_rules
from app.domain.pattern.ids import PieceId, PointId


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


def test_the_style_holds_every_pds_size_with_l_as_base(style):
    assert style.sizes == ("S", "M", "L", "XL", "XXL", "3XL") and style.base_size == "L"
    assert all(len(style.view(size)) == 7 for size in style.sizes)


def test_each_named_point_s_rule_is_its_move_from_l_in_every_size(style):
    rules = grade_rules(style)
    assert rules.table.sizes == style.sizes and rules.table.sample_size == "L"
    for piece_id, point in ((PieceId("FRT"), PointId("HPS")), (PieceId("Sleeve"), PointId("cap_crown"))):
        number = rules.by_point[(piece_id, point)]
        deltas = rules.table.rules[number - 1]
        base = next(p for p in style.view("L") if p.id == piece_id).point(point).position
        for size, (dx, dy) in zip(style.sizes, deltas, strict=True):
            moved = next(p for p in style.view(size) if p.id == piece_id).point(point).position
            assert (dx, dy) == pytest.approx((moved.x - base.x, moved.y - base.y), abs=1e-6), size


def test_points_that_move_alike_share_one_rule(style):
    rules = grade_rules(style)
    still = rules.by_point[(PieceId("back"), PointId("CB_hem"))]  # the back's frame origin never moves
    assert all(delta == (0.0, 0.0) for delta in rules.table.rules[still - 1])
    assert rules.by_point[(PieceId("back_YK"), PointId("CB_yoke"))] == still  # nor does the yoke's: one rule
    assert len(rules.table.rules) < len(rules.by_point)


def test_base_points_carry_their_rule_ids(style):
    rules = grade_rules(style)
    named = with_grade_rules(style, rules)
    hps = next(p for p in named.view("L") if p.id == PieceId("FRT")).point(PointId("HPS"))
    assert str(hps.grade_rule) == f"R{rules.by_point[(PieceId('FRT'), PointId('HPS'))]}"


def test_a_style_with_ungraded_sizes_is_refused(style):
    from app.domain.pattern.style import Style

    base_only = Style(style.id, style.name, style.sizes, "L", {"L": style.geometry["L"]})
    with pytest.raises(ValueError, match="Grade rules need every size drafted; missing S, M, XL, XXL, 3XL"):
        grade_rules(base_only)
