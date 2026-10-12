"""T143: spec §7 piece gap limits at L, each drafted 1078375 sew outline against its PDS outline (Hausdorff)."""
import pytest

from app.application.accuracy.gap_checks import CAP_CM, GAP_CM, gap_checks
from app.application.cad.style_from_block import style_from_block
from app.domain.pattern.ids import PointId

LIMITS = {"FRT": 0.5, "back": 1.0, "back YK": 0.2, "CLR": 0.6, "BND TOP": 0.6, "BND IN": 0.6}


@pytest.fixture(scope="module")
def base_pieces():
    return style_from_block("shirt_1078375").view("L")


def test_the_limits_are_the_spec_numbers():
    assert GAP_CM == LIMITS and CAP_CM == 0.2


def test_every_piece_lands_within_its_gap_limit(base_pieces, pds_styles):
    checks = gap_checks(base_pieces, pds_styles["1078375"])
    assert [check.name for check in checks] == [*(f"{name} gap" for name in LIMITS), "Sleeve cap gap"]
    assert {check.piece for check in checks} == {*LIMITS, "Sleeve"}
    failed = [f"{c.name}: {c.value:.3f}" for c in checks if not c.passed]
    assert not failed, failed
    assert all(c.source.kind == "pds" for c in checks)


def test_a_moved_shoulder_point_fails_the_front_gap(base_pieces, pds_styles):
    def moved(piece):
        if piece.name != "FRT":
            return piece
        sp = piece.point(PointId("SP"))
        return piece.move_point(PointId("SP"), sp.position.x + 2.0, sp.position.y)

    checks = {c.name: c for c in gap_checks(tuple(map(moved, base_pieces)), pds_styles["1078375"])}
    assert not checks["FRT gap"].passed and checks["FRT gap"].value > LIMITS["FRT"]
    assert checks["back gap"].passed
