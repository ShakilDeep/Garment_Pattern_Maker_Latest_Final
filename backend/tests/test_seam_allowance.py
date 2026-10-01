"""P1-04: SeamAllowance validates per-edge widths and per-corner styles on construction (PM-03)."""

from math import inf, nan

import pytest

from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance

S1, S2, V = SegmentId("s1"), SegmentId("s2"), PointId("v")


def test_defaults_overrides_and_styles():
    allowance = SeamAllowance(1, ((S1, 2.5),), ((V, "fold_back"),))
    assert allowance.width_of(S1) == 2.5 and allowance.width_of(S2) == 1.0
    assert allowance.style_at(V) is CornerStyle.FOLD_BACK
    assert allowance.style_at(PointId("w")) is CornerStyle.MITRE


def test_values_are_quantized_and_sequences_frozen():
    allowance = SeamAllowance(1.0000000004, [(S1, 0.1234567891)])
    assert allowance.default_width == 1.0 and allowance.width_of(S1) == 0.123457
    assert isinstance(allowance.edge_widths, tuple) and hash(allowance)


def test_zero_width_is_allowed_for_hems_and_folds():
    assert SeamAllowance(0, ((S1, 0),)).width_of(S1) == 0


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: SeamAllowance(-1), "non-negative"),
        (lambda: SeamAllowance(nan), "non-negative"),
        (lambda: SeamAllowance(inf), "non-negative"),
        (lambda: SeamAllowance(True), "non-negative"),
        (lambda: SeamAllowance(1, ((S1, -0.5),)), "non-negative"),
        (lambda: SeamAllowance(1, ((S1, 1), (S1, 2))), "more than once"),
        (lambda: SeamAllowance(1, (("s1", 1),)), "SegmentId"),
        (lambda: SeamAllowance(1, ((S1,),)), "pairs"),
        (lambda: SeamAllowance(1, 5), "pairs"),
        (lambda: SeamAllowance(1, corner_styles=((V, "round"),)), "corner style"),
        (lambda: SeamAllowance(1, corner_styles=((V, "mitre"), (V, "square"))), "more than once"),
        (lambda: SeamAllowance(1, corner_styles=(("v", "mitre"),)), "PointId"),
    ],
    ids=["negative", "nan", "inf", "bool", "negative-edge", "duplicate-edge", "edge-id-type", "edge-shape",
         "edge-not-iterable", "unknown-style", "duplicate-corner", "corner-id-type"],
)
def test_invalid_allowances_are_rejected(build, message):
    with pytest.raises(ValueError, match=message):
        build()
