"""T128: every finishing value seeded from the client PDS re-measures to the same number from the PDS."""
import pytest

from app.domain.finishing import finishing
from app.infrastructure.pds.edges import edge_allowances

MATCH_CM = 0.5  # evidence locates an edge: midpoint and length within 0.5 cm
VALUE_CM = 0.03  # a measured median within 0.03 cm of the stored allowance
NOTCH_CM = 0.02

CASES = [(family_id, item) for family_id, family in finishing().families.items()
         for item in family.allowances.values()]


@pytest.mark.parametrize(("family_id", "item"), CASES, ids=[f"{f}-{i.role}" for f, i in CASES])
def test_each_allowance_is_the_measured_pds_value(pds_styles, family_id, item):
    style = pds_styles[finishing().families[family_id].source_pds]
    pieces = {piece.name: piece for piece in style.pieces}
    for evidence in item.evidence:
        edges = edge_allowances(pieces[evidence.piece])
        found = [edge for edge in edges
                 if abs(edge.mid[0] - evidence.mid[0]) <= MATCH_CM and abs(edge.mid[1] - evidence.mid[1]) <= MATCH_CM
                 and abs(edge.length_cm - evidence.length) <= MATCH_CM]
        assert len(found) == 1, f"{item.role}: no single edge at {evidence}"
        assert found[0].median_cm == pytest.approx(item.value_cm, abs=VALUE_CM), (item.role, evidence.piece)


@pytest.mark.parametrize("family_id", ["shirt", "pant"])
def test_the_notch_depth_is_the_pds_notch_length(pds_styles, family_id):
    family = finishing().families[family_id]
    notches = [notch for piece in pds_styles[family.source_pds].pieces for notch in piece.outline.notches]
    assert notches
    for (x1, y1), (x2, y2) in notches:
        assert ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 == pytest.approx(family.notch_depth_cm, abs=NOTCH_CM)


def test_fold_edges_are_measured_as_fold_not_as_allowance(pds_styles):
    back = next(piece for piece in pds_styles["1078375"].pieces if piece.name == "back")
    folds = [edge for edge in edge_allowances(back) if edge.on_fold]
    assert len(folds) == 1 and folds[0].length_cm == pytest.approx(68.0, abs=0.1)
