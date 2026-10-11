"""shirt_v2 on the demo chart (Book2, every size): the same eight pieces as demo_v1, valid, with the sleeve cap
eased into its armhole and only the PDS notches; selectable as a drafting profile."""
import pytest
from pom_workbooks import BOOK2
from shapely.geometry import Point, Polygon

from app.application.requirement_resolve import resolve
from app.domain.blocks.registry import installed
from app.domain.blocks.run import draft_pattern
from app.domain.catalog import SIZES
from app.domain.tolerances import SLEEVE_EASE_CM
from app.infrastructure.parsers import parse_xlsx
from app.infrastructure.validation import validate


@pytest.fixture(scope="module")
def patterns():
    rows = parse_xlsx(BOOK2.read_bytes(), "Book2(4).xlsx")
    out = {}
    for size in SIZES:
        values = {row["key"]: row["values"][size]["value"] for row in rows
                  if row["values"].get(size, {}).get("value") is not None and row["mapping_status"] != "unmapped"}
        out[size] = draft_pattern(installed().get("shirt_v2"), values, size, {})
    return out


def by_name(pattern: dict) -> dict:
    return {piece["name"]: piece for piece in pattern["pieces"]}


def test_it_drafts_the_demo_piece_set(patterns):
    demo = {"Front", "Back", "Yoke", "Sleeve", "Collar", "Collar Stand", "Cuff", "Sleeve Placket"}
    assert all(set(by_name(p)) == demo for p in patterns.values())
    assert by_name(patterns["L"])["Yoke"]["quantity"] == 2  # outer and inner yoke, as on the PDS


@pytest.mark.parametrize("size", SIZES)
def test_every_size_validates_without_errors_or_flat_vertices(patterns, size):
    issues = validate(patterns[size])
    assert not [i for i in issues if i["severity"] == "ERROR"]
    assert not [i for i in issues if i["code"] in {"FLATTENING", "TURN_ANGLE"}]


@pytest.mark.parametrize("size", SIZES)
def test_the_sleeve_cap_fits_the_whole_armhole(patterns, size):
    """demo_v1's cap is about 20 cm longer than its armhole; here the two agree within the 2 cm seam check
    (the chart grades the cap slower than the armhole, so the ease runs from +1.4 cm at S to -1 cm at 3XL)."""
    pieces = by_name(patterns[size])
    armhole = pieces["Front"]["seams"]["armhole"] + pieces["Back"]["seams"]["armhole"]
    assert abs(pieces["Sleeve"]["seams"]["cap"] - armhole) <= SLEEVE_EASE_CM


def test_the_notches_are_the_pds_ones_and_lie_on_the_outline(patterns):
    pieces = by_name(patterns["L"])
    assert len(pieces["Yoke"]["notches"]) == 2 and pieces["Front"]["notches"] == pieces["Back"]["notches"] == []
    crown, width = pieces["Sleeve"]["notches"][-1], pieces["Sleeve"]["width"]
    assert crown[0] == pytest.approx(width / 2) and crown[1] < 0.1  # at the top of the cap
    for piece in pieces.values():
        outline = Polygon(piece["points"])
        assert all(outline.boundary.distance(Point(notch)) <= 1e-6 for notch in piece["notches"])


def test_collar_and_band_run_along_the_grain_and_fit_the_neckline(patterns):
    pieces = by_name(patterns["L"])
    neckline = 2 * pieces["Front"]["seams"]["neckline"] + pieces["Yoke"]["seams"]["neckline"]
    assert pieces["Collar Stand"]["seams"]["attachment"] == pytest.approx(neckline)
    for name in ("Collar", "Collar Stand"):
        (x0, y0), (x1, y1) = pieces[name]["grainline"]
        assert y0 == y1 and x1 > x0


def test_it_is_offered_as_a_drafting_profile():
    assert "shirt_v2" in installed().project_ids()
    project = {"resolutions": {}, "documents": []}
    assert resolve(project, "profile", "shirt_v2")["resolutions"]["profile"] == "shirt_v2"
