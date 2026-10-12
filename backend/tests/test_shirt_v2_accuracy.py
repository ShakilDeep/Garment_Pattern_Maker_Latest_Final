"""shirt_v2 shape accuracy: drafted from charts that describe the 1078375 PDS, each piece must land on the
PDS sew outline (size L). demo_v1, given the same charts, misses, so the limits do tell the drafts apart."""
import pytest
import shirt_v2_pds_poms as poms
from outline_compare import above, fit, pds_outline, piece_fit
from shapely.geometry import Polygon

from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_pattern

AREA = 0.03  # build plan accuracy suite: areas within 3 % of the client's Optitex pattern
TARGET_AREA = 0.005  # spec §7: 0.5 % after package 03 (T147)
# (piece, chart, PDS piece, Hausdorff limit in cm, area share); the back has the PDS's 1.07 cm yoke-seam drop,
# the front neck the PDS's 0.56 cm inset, so the collar and band land on the PDS too (T147)
LIMITS = [
    ("Front", "front", "FRT", 0.5, TARGET_AREA),
    ("Back", "back", "back", 0.3, TARGET_AREA),
    ("Yoke", "back", "back YK", 0.2, TARGET_AREA),
    ("Collar", "back", "CLR", 0.2, TARGET_AREA),
    ("Collar Stand", "back", "BND TOP", 0.2, TARGET_AREA),
]


def drafted(profile: str) -> dict:
    charts = {"front": poms.front(), "back": poms.back()}
    return {name: {p["name"]: p for p in draft_pattern(installed().get(profile), chart, "L", {})["pieces"]}
            for name, chart in charts.items()}


@pytest.fixture(scope="module")
def pds(pds_styles):
    return {piece.name: piece for piece in pds_styles["1078375"].pieces}


def cap_fit(pieces: dict, pds: dict):
    depth = poms.R["cap_height"]  # the sleeve above its underarm line; the PDS sleeve is short, ours long
    ours = above(Polygon(pieces["front"]["Sleeve"]["points"]).buffer(0), depth)
    return fit(ours, above(pds_outline(pds["Sleeve"]), depth, top_at_max_x=True))


@pytest.mark.parametrize(("piece", "chart", "pds_name", "limit", "area"), LIMITS)
def test_each_piece_lands_on_the_pds_outline(pds, piece, chart, pds_name, limit, area):
    result = piece_fit(drafted("shirt_v2")[chart][piece]["points"], pds[pds_name])
    assert result.hausdorff_cm <= limit
    assert result.area_ratio == pytest.approx(1, abs=area)


def test_the_sleeve_cap_is_the_pds_cap(pds):
    result = cap_fit(drafted("shirt_v2"), pds)
    assert result.hausdorff_cm <= 0.2
    assert result.area_ratio == pytest.approx(1, abs=AREA)


def test_demo_v1_misses_the_same_limits(pds):
    """The old draft (3-point curves, a dome cap, a straight band) fails every one of these checks."""
    pieces = drafted("demo_v1")
    misses = [piece for piece, chart, name, limit, _ in LIMITS
              if piece_fit(pieces[chart][piece]["points"], pds[name]).hausdorff_cm > limit]
    assert misses == [piece for piece, *_ in LIMITS]
    assert cap_fit(pieces, pds).hausdorff_cm > 1.0
