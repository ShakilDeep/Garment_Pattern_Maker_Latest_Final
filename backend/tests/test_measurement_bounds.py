"""P0-07: per-measurement plausible ranges derived from the source chart (domain rule, table-driven)."""
import pytest

from app.domain.measurement_bounds import accepts, keep_source_value, plausible_range


def _row(*cells):
    return {"key": "sleeve_length", "values": {f"size{i}": cell for i, cell in enumerate(cells)}}


def _source(value):
    return {"value": value, "raw": value, "override": False}


SLEEVE = _row(_source(64.0), _source(66.0), _source(69.5))


@pytest.mark.parametrize(("row", "expected"), [
    (SLEEVE, (32.0, 104.25)),
    (_row(_source(6.0)), (3.0, 9.0)),
    (_row(), (0, 500)),
    (_row({"value": 90.0, "raw": 66, "override": True}, _source(64.0)), (32.0, 99.0)),
    (_row({"value": 90.0, "raw": "=A1*2", "override": True}), (0, 500)),
    (_row({"value": 90.0, "raw": True, "override": True}), (0, 500)),
    (_row(_source(0), _source(None)), (0, 500)),
    (_row(_source(400.0)), (200.0, 500)),
    (_row({"value": 90.0, "raw": "=F23-1", "override": True, "source_value": 69.5}), (34.75, 104.25)),
], ids=["sleeve-chart", "constant-cuff", "no-source", "override-keeps-raw", "formula-raw-dropped",
        "bool-raw-dropped", "non-positive-ignored", "capped-at-blanket",
        "formula-source-value-kept"])
def test_plausible_range_is_derived_from_source_values(row, expected):
    assert plausible_range(row) == pytest.approx(expected)


@pytest.mark.parametrize(("value", "allowed"), [
    (-3, False), (0, False), (31.9, False), (32.0, True), (66, True), (104.25, True), (104.3, False),
])
def test_sleeve_edits_are_checked_against_its_range(value, allowed):
    assert accepts(SLEEVE, value) is allowed


@pytest.mark.parametrize(("value", "allowed"), [(-1, False), (0, False), (0.1, True), (500, True), (500.1, False)])
def test_measurements_without_source_values_keep_the_blanket_bound(value, allowed):
    assert accepts(_row(), value) is allowed


def test_first_override_remembers_the_evaluated_source_value():
    cell = {"value": 69.5, "raw": "=F23-1", "override": False}
    keep_source_value(cell)
    cell.update(value=90.0, override=True)
    keep_source_value(cell)
    assert cell["source_value"] == 69.5
