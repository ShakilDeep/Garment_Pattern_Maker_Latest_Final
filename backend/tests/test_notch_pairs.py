"""T144 (spec §7 Finishing): every notch has its pair on the seam it sews to, at the same distance within 0.1 cm.

The client PDS has two shirt notches with no partner (shirt.md Q5/Q6): they are reported, not gated.
"""
from dataclasses import replace

import pytest

from app.application.accuracy.notch_pairs import PAIR_CM, notch_distance, notch_pair_checks
from app.application.cad.style_from_block import style_from_block
from app.domain.blocks.shirt.seams import PDS_UNPAIRED, RELATIONS
from app.domain.pattern.annotation import Notch
from app.domain.pattern.ids import AnnotationId, SegmentId

SHOULDER = SegmentId("HPS:SP")
BISECT_STEPS = 60


@pytest.fixture(scope="module")
def pieces():
    return {piece.name: piece for piece in style_from_block("shirt_1078375").view("L")}


def checks(pieces: dict) -> dict:
    return {c.name: c for c in notch_pair_checks(tuple(pieces.values()), RELATIONS, PDS_UNPAIRED)}


def with_notch(piece, segment: SegmentId, distance: float, name: str = "front_shoulder"):
    """``piece`` with notch ``name`` on ``segment``, ``distance`` cm from the segment start (bisection on t)."""
    low, high = 0.0, 1.0
    for _ in range(BISECT_STEPS):
        t = (low + high) / 2
        low, high = (t, high) if notch_distance(piece, Notch(AnnotationId("probe"), segment, t)) < distance else (low, t)
    return replace(piece, notches=(*piece.notches, Notch(AnnotationId(name), segment, (low + high) / 2)))


def test_the_pds_notches_are_reported_unpaired_not_gated(pieces):
    found = checks(pieces)
    assert set(found) == {"shoulder_notch pair", "crown_notch pair"} and PAIR_CM == 0.1
    for check in found.values():
        assert not check.passed and not check.gate
        assert "Q6" in check.source.ref and check.source.kind == "pds"


def test_a_partner_at_the_same_seam_distance_pairs_the_yoke_notch(pieces):
    yoke = pieces["back YK"]
    distance = notch_distance(yoke, yoke.notches[0])
    assert distance == pytest.approx(1.475, abs=0.01)  # docs/drafting/shirt.md: 1.475 cm from HPS
    found = checks({**pieces, "FRT": with_notch(pieces["FRT"], SHOULDER, distance)})
    for name in ("shoulder_notch pair", "front_shoulder pair"):
        assert found[name].passed and found[name].gate, name


def test_a_partner_half_a_centimetre_off_fails(pieces):
    yoke = pieces["back YK"]
    found = checks({**pieces, "FRT": with_notch(pieces["FRT"], SHOULDER, notch_distance(yoke, yoke.notches[0]) + 0.5)})
    assert not found["front_shoulder pair"].passed and found["front_shoulder pair"].gate


def test_a_new_notch_without_a_partner_is_an_error(pieces):
    found = checks({**pieces, "back": with_notch(pieces["back"], SegmentId("UA:side_hem"), 10.0, "side_notch")})
    assert not found["side_notch pair"].passed and found["side_notch pair"].gate
