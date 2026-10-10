"""T131 (build plan M4): Hypothesis fuzzing of the 1078375 grading.

The PDS steps that drive the grade are moved by up to 5 % of their measurement around any PDS size, then the
real pipeline runs (follows, proportional steps, truing). Every seam relation must come back to its base
value, and every piece must draft a simple outline with a valid cut outline.
"""
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from app.domain.blocks.shirt.allowances import seam_allowance
from app.domain.blocks.shirt.block import ShirtBlock
from app.domain.blocks.shirt.grading import DRIVEN, graded
from app.domain.blocks.shirt.reference import graded_sizes, reference_measurements
from app.domain.blocks.shirt.truing import relation_values, true_seams
from app.infrastructure.pds.shirt_grade_numbers import pds_steps, proportional_steps
from app.infrastructure.piece_validity import check_cut_geometry

BASE = reference_measurements()
TARGETS = relation_values(BASE)
SHARE = 0.05


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(size=st.sampled_from(graded_sizes()),
       shares=st.lists(st.floats(min_value=-SHARE, max_value=SHARE), min_size=len(DRIVEN), max_size=len(DRIVEN)))
@example(size="S", shares=[0.0] * 6 + [-0.03125, 0.0])  # once clipped the BND TOP end (band_top_reach fix)
def test_moved_grades_true_to_equal_seams_and_valid_outlines(pds_styles, size, shares):
    style = pds_styles["1078375"]
    steps = pds_steps(style, size)
    for (name, number), share in zip(DRIVEN.items(), shares, strict=True):
        steps[number] += BASE[name] * share
    trued = true_seams(graded(BASE, steps, proportional_steps(style, size, BASE)), TARGETS)
    values = relation_values(trued)
    for relation, target in TARGETS.items():
        assert abs(values[relation] - target) <= 1e-5, (size, relation, values[relation], target)
    for piece in ShirtBlock().draft_pieces(trued, size, {}):
        check_cut_geometry(piece, seam_allowance(str(piece.id)))  # raises on a crossing or lost allowance
