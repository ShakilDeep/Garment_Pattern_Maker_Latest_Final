"""P1-01: marks (internal lines, notches, drills, labels) and cutting values validate on construction."""

from math import nan

import pytest

from app.domain.geom.primitives import Point2D
from app.domain.pattern.annotation import DrillHole, InternalLine, Label, Notch
from app.domain.pattern.cutting import CutQuantity, Grainline
from app.domain.pattern.ids import AnnotationId, SegmentId

S, N = SegmentId("s"), AnnotationId("n")


@pytest.mark.parametrize(
    ("single", "pairs", "fold", "total"), [(1, 0, 0, 1), (0, 1, 0, 2), (0, 0, 1, 1), (2, 1, 1, 5)]
)
def test_cut_quantity_totals(single, pairs, fold, total):
    assert CutQuantity(single, pairs, fold).total == total


@pytest.mark.parametrize("counts", [(0, 0, 0), (-1, 1, 0), (True, 0, 0), (1.5, 0, 0)])
def test_cut_quantity_rejects_empty_or_non_integer_counts(counts):
    with pytest.raises(ValueError, match="cut"):
        CutQuantity(*counts)


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: Grainline(Point2D(1, 1), Point2D(1, 1)), "grainline"),
        (lambda: DrillHole(N, Point2D(0, 0), 0), "diameter"),
        (lambda: DrillHole(N, Point2D(0, 0), True), "diameter"),
        (lambda: InternalLine(N, [Point2D(0, 0)]), "two points"),
        (lambda: Label(N, "  ", Point2D(0, 0)), "text"),
        (lambda: Notch(N, S, 1.5), "between 0 and 1"),
        (lambda: Notch(N, S, nan), "between 0 and 1"),
    ],
    ids=["grainline", "diameter-zero", "diameter-bool", "internal-line", "label", "notch-range", "notch-nan"],
)
def test_mark_shape_rules(build, message):
    with pytest.raises(ValueError, match=message):
        build()


def test_internal_line_coerces_a_list_to_a_tuple():
    line = InternalLine(N, [Point2D(0, 0), Point2D(1, 1)])
    assert isinstance(line.points, tuple) and hash(line)


def test_notch_parameter_keeps_a_resolution_finer_than_the_coordinate_grid():
    # 1e-9 in t keeps a notch on a 1000 cm edge within 1e-6 cm; 1e-6 in t would move it 5e-4 cm.
    assert Notch(N, S, 0.1234567894).t == 0.123456789
    assert Notch(N, S, 1 + 4e-10).t == 1.0
    with pytest.raises(ValueError, match="between 0 and 1"):
        Notch(N, S, 1 + 6e-10)
