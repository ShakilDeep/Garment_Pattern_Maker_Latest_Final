"""T127: the AAMA .RUL grade-rule writer/reader (fed with real rules in T131)."""
import pytest

from app.domain.interchange import GradeRuleTable
from app.infrastructure.aama.rul import read_rul, write_rul

TABLE = GradeRuleTable(
    name="Style 1", sizes=("S", "M", "L"), sample_size="M",
    rules=(((-1.0, -0.5), (0.0, 0.0), (1.0, 0.5)), ((0.0, -2.0), (0.0, 0.0), (0.25, 2.0))),
)


def test_the_text_layout_is_pinned():
    assert write_rul(TABLE, "mm").splitlines() == [
        "ANSI/AAMA VERSION: 1.0.0",
        "GRADE RULE TABLE: Style 1",
        "NUMBER OF SIZES: 3",
        "SIZE LIST: S M L",
        "SAMPLE SIZE: M",
        "UNITS: METRIC",
        "RULE: DELTA 1",
        "-10.000000, -5.000000",
        "0.000000, 0.000000",
        "10.000000, 5.000000",
        "RULE: DELTA 2",
        "0.000000, -20.000000",
        "0.000000, 0.000000",
        "2.500000, 20.000000",
        "END",
    ]


@pytest.mark.parametrize("unit", ["mm", "inch"])
def test_write_then_read_round_trips_in_cm(unit):
    read = read_rul(write_rul(TABLE, unit))
    assert (read.name, read.sizes, read.sample_size) == (TABLE.name, TABLE.sizes, TABLE.sample_size)
    flat = [c for rule in read.rules for delta in rule for c in delta]
    assert flat == pytest.approx([c for rule in TABLE.rules for delta in rule for c in delta], abs=1e-6)


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"sample_size": "XL"}, "Sample size XL is not in the size list"),
    ({"rules": (((0.0, 0.0), (0.0, 0.0)),)}, "Rule 1 has 2 deltas for 3 sizes"),
    ({"rules": (((0.0, 0.0), (0.1, 0.0), (0.0, 0.0)),)}, "Rule 1 moves the sample size"),
])
def test_an_invalid_table_is_rejected(kwargs, message):
    fields = {"name": "T", "sizes": ("S", "M", "L"), "sample_size": "M", "rules": TABLE.rules} | kwargs
    with pytest.raises(ValueError, match=message):
        GradeRuleTable(**fields)


@pytest.mark.parametrize(("text", "message"), [
    ("GRADE RULE TABLE: x\nEND", "RUL field missing: SIZE LIST"),
    (write_rul(TABLE, "mm").replace("10.000000, 5.000000", "ten, five"), "RUL delta is not a number"),
    (write_rul(TABLE, "mm").replace("UNITS: METRIC", "UNITS: FURLONG"), "Unsupported AAMA units 'FURLONG'"),
    (write_rul(TABLE, "mm").replace("NUMBER OF SIZES: 3", "NUMBER OF SIZES: 10"), "declares 10 sizes but lists 3"),
    (write_rul(TABLE, "mm").replace("10.000000, 5.000000", "1, 2, 3"), "RUL delta needs two values"),
])
def test_malformed_rul_text_is_rejected(text, message):
    with pytest.raises(ValueError, match=message):
        read_rul(text)
