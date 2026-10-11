"""T141b: a named block drafts through the engine; its V5 view is drawn from the V6 pieces."""
from dataclasses import replace
from itertools import pairwise

import pytest

from app.application.commands import execute
from app.application.drafting_engine import draft
from app.application.pattern_validation import validate_draft
from app.application.project_style import refresh_style
from app.domain.blocks.registry import installed
from app.domain.geom.primitives import Point2D
from app.domain.pattern.edges import stitch_ring
from app.domain.tolerances import COORDINATE
from app.infrastructure.v5_view.unfold import unfold_ring

QUANTITY = {"FRT": 2, "back": 1, "back YK": 2, "CLR": 2, "BND TOP": 1, "BND IN": 1, "Sleeve": 2}
FOLDED = {"back", "back YK", "CLR", "BND TOP", "BND IN"}


@pytest.fixture(scope="module")
def shirt():
    block = installed().get("shirt_1078375")
    return block, draft(block, block.reference_measurements(), "L", {})


def test_every_piece_has_a_view_with_the_client_quantities(shirt):
    pattern = shirt[1].pattern
    assert {piece["name"]: piece["quantity"] for piece in pattern["pieces"]} == QUANTITY
    assert {piece["name"] for piece in pattern["pieces"] if piece["cut_on_fold"]} == FOLDED
    assert pattern["geometry_source"] == "v6" and pattern["seam_allowance"] is None
    assert pattern["profile_metadata"]["id"] == "shirt_1078375" and pattern["size"] == "L"
    assert all(piece["grainline"] and piece["cut_points"] for piece in pattern["pieces"])


@pytest.mark.parametrize("name", sorted(FOLDED))
def test_a_fold_piece_opens_to_twice_its_drawn_half(shirt, name):
    result = shirt[1]
    half = next(piece for piece in result.pieces if piece.name == name)
    view = next(piece for piece in result.pattern["pieces"] if piece["name"] == name)
    drawn = [[p.x, p.y] for p in stitch_ring(half)]
    assert view["area"] == pytest.approx(2 * _area(drawn), abs=view["perimeter"] * COORDINATE)  # 1e-6 cm grid
    assert min(p[0] for p in view["points"]) == 0 and min(p[1] for p in view["points"]) == 0


def test_notches_sit_on_the_sew_line(shirt):
    pieces = [piece for piece in shirt[1].pattern["pieces"] if piece["notches"]]
    assert {piece["name"] for piece in pieces} == {"back YK", "Sleeve"}  # the two PDS notches (T129 Q6)
    for piece in pieces:
        ring = piece["points"]  # closed: the first point repeats at the end
        assert ring[0] == ring[-1]
        for notch in piece["notches"]:
            assert min(_to_segment(notch, a, b) for a, b in pairwise(ring)) < 1e-6


def test_the_draft_is_valid_and_a_crossed_outline_is_an_error(shirt):
    result = shirt[1]
    assert validate_draft(result) == []
    piece = result.pieces[0]
    points = list(piece.points)
    points[0], points[2] = (replace(points[0], position=points[2].position),
                            replace(points[2], position=points[0].position))
    crossed = replace(result, pieces=(replace(piece, points=tuple(points)), *result.pieces[1:]))
    issues = validate_draft(crossed)
    assert [issue["piece"] for issue in issues] == [piece.name]
    assert issues[0]["severity"] == "ERROR" and issues[0]["code"] == "GEOMETRY_INVALID"
    assert "not a simple outline" in issues[0]["message"]


def test_a_ring_without_its_fold_edge_cannot_be_opened():
    with pytest.raises(ValueError, match="fold edge is not on the outline"):
        unfold_ring([Point2D(0, 0), Point2D(4, 0), Point2D(4, 3)], Point2D(10, 10), Point2D(10, 20))


def _area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2


def _to_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2) ** 0.5


def _v6_project(shirt):
    pattern = {**shirt[1].pattern, "id": "named-L", "stale": False}
    return {"id": "p", "name": "Named", "pattern": pattern, "grades": [], "state": "PATTERN_NEEDS_REVIEW",
            "style": "stored", "style_key": ["kept"]}


def test_a_named_style_is_never_re_derived_from_its_view(shirt):
    project = _v6_project(shirt)
    refresh_style(project)
    assert (project["style"], project["style_key"]) == ("stored", ["kept"])


def test_v5_edits_refuse_a_named_pattern(shirt):
    with pytest.raises(ValueError, match="edit it with the Pattern Studio CAD tools"):
        execute(None, _v6_project(shirt), "allowance", 1.0)
