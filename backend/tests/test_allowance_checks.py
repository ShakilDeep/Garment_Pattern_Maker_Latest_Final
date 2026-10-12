"""T144 (spec §7 Finishing): every cut edge lies at its finishing.json width from the sew line, within 0.05 cm."""
from dataclasses import replace

import pytest

from app.application.accuracy.allowance_checks import ALLOWANCE_CM, allowance_checks
from app.application.cad.style_from_block import style_from_block
from app.domain.blocks.shirt.allowances import seam_allowance
from app.domain.pattern.ids import PieceId, SegmentId

HEM = SegmentId("side_hem:FE_hem")


@pytest.fixture(scope="module")
def style():
    return style_from_block("shirt_1078375")


def test_the_limit_is_the_spec_number():
    assert ALLOWANCE_CM == 0.05


@pytest.mark.parametrize("size", ["S", "M", "L", "XL", "XXL", "3XL"])
def test_every_edge_is_at_its_finishing_width_in_every_size(style, size):
    checks = allowance_checks(style.view(size), style.allowances, seam_allowance)
    failed = [f"{c.name}: {c.value:.3f} ({c.limit})" for c in checks if not c.passed]
    assert not failed, failed
    assert all(c.gate and c.source.kind == "pds" and c.name.endswith(" allowance") for c in checks)


def test_fold_edges_are_not_checked(style):
    pieces = style.view("L")
    folds = {(p.name, str(p.fold.segment)) for p in pieces if p.fold is not None}
    edges = {(c.piece, c.edge) for c in allowance_checks(pieces, style.allowances, seam_allowance)}
    assert folds and not folds & edges
    assert len(edges) == sum(len(p.outline) for p in pieces) - len(folds)


def test_a_cut_line_off_its_finishing_width_fails_only_that_edge(style):
    front = style.allowances[PieceId("FRT")]
    edited = replace(front, edge_widths=tuple((s, 2.0 if s == HEM else w) for s, w in front.edge_widths))
    actual = {**style.allowances, PieceId("FRT"): edited}
    failed = [c for c in allowance_checks(style.view("L"), actual, seam_allowance) if not c.passed]
    assert [c.name for c in failed] == ["FRT side_hem:FE_hem allowance"]
    assert failed[0].value == pytest.approx(2.0, abs=ALLOWANCE_CM) and failed[0].limit == "3.500 ± 0.05 cm"
