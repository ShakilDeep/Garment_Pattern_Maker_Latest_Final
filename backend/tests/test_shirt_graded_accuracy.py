"""T131 accuracy suite per size (build plan M4): every 1078375 size against its own PDS numbers."""
from dataclasses import replace

import pytest

from app.application.accuracy.graded import graded_report
from app.application.cad.style_from_block import style_from_block

SUM_AREA = {"S": 1.2965, "M": 1.3607, "L": 1.4262, "XL": 1.5216, "XXL": 1.5993, "3XL": 1.6781}


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


@pytest.fixture(scope="module")
def report(style, pds_styles):
    return graded_report(style, pds_styles["1078375"])


def test_every_gate_passes_in_every_size(report):
    failed = [f"{c.name}: {c.value:.4f} (limit {c.limit})" for c in report.checks if c.gate and not c.passed]
    assert not failed, failed
    assert report.passed


def test_piece_sizes_off_the_base_size_are_reported_not_gated(report):
    by_name = {check.name: check for check in report.checks}
    assert by_name["L Sleeve cut area"].gate and by_name["L Sleeve cut area"].passed
    sleeve_3xl = by_name["3XL Sleeve cut area"]
    assert not sleeve_3xl.gate and not sleeve_3xl.passed  # over 3 %: the held cap ease, a review point
    assert sleeve_3xl.value > 0.1283 * 1.03  # PDS 3XL Sleeve AREA 0.1283 m2


def test_sum_area_is_checked_against_each_pds_size_total(report):
    by_name = {check.name: check for check in report.checks}
    for size, total in SUM_AREA.items():
        assert by_name[f"{size} SUM_AREA"].limit == f"3 % of {total} m2"
        assert by_name[f"{size} SUM_AREA"].value == pytest.approx(total, rel=0.03)


def test_pieces_seams_and_outlines_are_checked_in_every_size(report):
    names = {check.name for check in report.checks}
    for size in SUM_AREA:
        assert {f"{size} FRT length", f"{size} Sleeve width", f"{size} back YK cut area"} <= names
        assert f"{size} outlines valid" in names
        if size != "L":  # L's own seams are checked against the PDS (run.base_checks), not against itself
            assert {f"{size} side seams", f"{size} sleeve cap ease"} <= names
    assert "areas grow size to size" in names and "L side seams" not in names


def test_a_size_drafted_from_the_wrong_measurements_fails(style, pds_styles):
    swapped = replace(style, geometry={**style.geometry, "S": style.geometry["3XL"]})
    failed = {check.name for check in graded_report(swapped, pds_styles["1078375"]).checks if not check.passed}
    assert {"S SUM_AREA", "areas grow size to size"} <= failed
