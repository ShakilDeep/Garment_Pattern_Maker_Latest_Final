"""T142: a block's chart map (block input <- chart POM) is data a pattern maker confirms, never guessed."""
import pytest

from app.domain.blocks.chart_map import ChartMapEntry, chart_map, parse_chart_map
from app.domain.blocks.registry import installed

SHIRT = "shirt_1078375"


def _entry(**changes):
    return {"input": "front_length", "pom": "front_length_hps", "status": "confirmed",
            "evidence": "Pattern maker, 2026-10-12: chart front length = HPS to hem on the sew line", **changes}


def test_the_shipped_shirt_map_has_no_entries_yet():
    assert chart_map(installed().get(SHIRT)) == ()


def test_a_block_without_a_map_file_has_no_entries():
    assert chart_map(installed().get("demo_v1")) == ()


def test_a_valid_entry_parses():
    entries = parse_chart_map({"block": SHIRT, "entries": [_entry()]}, installed().get(SHIRT))
    assert entries == (ChartMapEntry("front_length", "front_length_hps", "confirmed",
                                     _entry()["evidence"]),)


@pytest.mark.parametrize(("changes", "message"), [
    ({"input": "hip_width"}, "Chart map for shirt_1078375: hip_width is not an input of the block"),
    ({"status": "assumed"}, "Chart map for shirt_1078375: front_length status must be proposed or confirmed"),
    ({"evidence": "  "}, "Chart map for shirt_1078375: front_length is confirmed without evidence"),
])
def test_a_bad_entry_is_refused_by_name(changes, message):
    with pytest.raises(ValueError, match=message):
        parse_chart_map({"block": SHIRT, "entries": [_entry(**changes)]}, installed().get(SHIRT))


def test_a_map_for_another_block_is_refused():
    with pytest.raises(ValueError, match="Chart map is for demo_v1, not shirt_1078375"):
        parse_chart_map({"block": "demo_v1", "entries": []}, installed().get(SHIRT))
