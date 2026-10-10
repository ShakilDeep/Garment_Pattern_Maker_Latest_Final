"""T130 accuracy suite (build plan M3), run on every commit: the drafted 1078375 L against its own PDS."""
import pytest

from app.application.accuracy.run import shirt_report
from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_named
from app.domain.blocks.shirt.reference import reference_measurements


@pytest.fixture(scope="module")
def report(pds_styles):
    pieces = draft_named(installed().get("shirt_1078375"), reference_measurements(), "L", {})
    return shirt_report(pieces, pds_styles["1078375"])


def test_every_check_passes(report):
    failed = [f"{c.name}: {c.value:.4f} (limit {c.limit})" for c in report.checks if not c.passed]
    assert not failed, failed


def test_the_build_plan_checks_are_all_present(report):
    names = {check.name for check in report.checks}
    for piece in ("FRT", "back", "back YK", "CLR", "BND TOP", "BND IN", "Sleeve"):
        assert {f"{piece} width", f"{piece} length", f"{piece} cut area"} <= names
    assert {"side seams", "shoulder seam", "yoke seam", "sleeve cap ease", "band neck edge vs neckline",
            "collar on band top edge", "notches", "outlines valid"} <= names


def test_the_drafted_seam_values_match_the_pds(report):
    by_name = {check.name: check for check in report.checks}
    assert by_name["sleeve cap ease"].value == pytest.approx(3.929, abs=0.1)
    assert by_name["band neck edge vs neckline"].value == pytest.approx(0.945, abs=0.1)
    assert by_name["collar on band top edge"].value == pytest.approx(-1.882, abs=0.1)
    assert by_name["FRT cut area"].limit == "3 % of 0.2588 m2"


def test_a_wrong_piece_fails_its_check(pds_styles):
    pieces = draft_named(installed().get("shirt_1078375"), {**reference_measurements(), "bicep": 50.0}, "L", {})
    failed = {check.name for check in shirt_report(pieces, pds_styles["1078375"]).checks if not check.passed}
    assert "Sleeve width" in failed and "sleeve cap ease" in failed
