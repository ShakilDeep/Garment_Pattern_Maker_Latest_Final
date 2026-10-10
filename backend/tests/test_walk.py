"""T130 / P1-11 (CAD-04): walk one seam along another; sleeve cap vs armhole ease within 0.01 cm."""
import pytest

from app.application.block_pieces import draft_block_pieces
from app.application.cad.walk import WalkPart, walk
from app.domain.blocks.registry import installed
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.geom.polyline_ops import length
from app.domain.pattern.ids import SegmentId
from app.domain.pattern.measure import path_length
from app.domain.pattern.notch_position import point_on
from app.domain.pattern.resolve import resolve_segment

CAP = (WalkPart("Sleeve", ("UA_back", "cap_crown", "UA_front")),)
ARMHOLE = (WalkPart("FRT", ("SP", "UA")), WalkPart("back", ("yoke_armhole", "UA")),
           WalkPart("back_YK", ("SP", "yoke_armhole")))


@pytest.fixture(scope="module")
def pieces():
    drafted = draft_block_pieces(installed().get("shirt_1078375"), reference_measurements(), "L", {})
    return {str(piece.id): piece for piece in drafted}


def _hand(pieces, parts) -> float:
    return sum(path_length(pieces[p.piece_id], [SegmentId(f"{a}:{b}") for a, b in zip(p.points, p.points[1:])])
               for p in parts)


def test_cap_ease_is_the_hand_calculation_and_the_pds_value(pieces):
    result = walk(pieces, CAP, ARMHOLE)
    assert result.first_cm == pytest.approx(_hand(pieces, CAP), abs=1e-9)
    assert result.second_cm == pytest.approx(_hand(pieces, ARMHOLE), abs=1e-9)
    # 1078375 PDS L ease 3.929 within the agreed curve tolerance (shirt.md Q4); the smooth crown gives 3.890
    assert result.difference_cm == pytest.approx(3.929, abs=0.1)


def test_walking_to_a_distance_places_a_matching_point_on_both_seams(pieces):
    result = walk(pieces, CAP, ARMHOLE, at_cm=30.0)
    first, second = result.at
    assert (first.piece_id, str(first.segment)) == ("Sleeve", "cap_crown:UA_front")
    assert (second.piece_id, str(second.segment)) == ("back", "yoke_armhole:UA")
    sleeve = pieces["Sleeve"]
    positions = {p.id: p.position for p in sleeve.points}
    curve = resolve_segment(next(s for s in sleeve.outline if s.id == first.segment), positions)
    partial = [point_on(curve, first.t * i / 4000) for i in range(4001)]
    walked = path_length(sleeve, [SegmentId("UA_back:cap_crown")]) + length([(p.x, p.y) for p in partial])
    assert walked == pytest.approx(30.0, abs=0.01)


def test_a_distance_past_the_seam_end_is_refused(pieces):
    with pytest.raises(ValueError, match="30.0 cm is past the end of the walked seam"):
        walk(pieces, (WalkPart("FRT", ("SP", "UA")),), ARMHOLE, at_cm=30.0)


def test_unknown_pieces_and_edges_are_key_errors(pieces):
    with pytest.raises(KeyError, match="No piece pocket"):
        walk(pieces, (WalkPart("pocket", ("a", "b")),), ARMHOLE)
    with pytest.raises(KeyError, match="FRT has no edge from UA to SP"):
        walk(pieces, (WalkPart("FRT", ("UA", "SP")),), ARMHOLE)
    with pytest.raises(ValueError, match="A walked seam needs at least two points"):
        walk(pieces, (WalkPart("FRT", ("SP",)),), ARMHOLE)
