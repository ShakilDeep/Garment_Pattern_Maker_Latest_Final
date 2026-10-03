import pytest

from app.domain.units import from_cm, to_cm


def test_inch_converts_to_cm_exactly():
    assert to_cm(44, "inch") == 111.76
    assert to_cm(18.1, "inch") == 45.974  # no 45.974000000000004 float noise
    assert to_cm(58, "cm") == 58


def test_cm_converts_to_every_output_unit():
    assert from_cm(10, "cm") == 10
    assert from_cm(10, "mm") == 100
    assert from_cm(10, "inch") == 3.937008
    assert from_cm(-0.0, "mm") == 0.0


def test_inch_round_trip_stays_on_the_model_grid():
    assert to_cm(from_cm(111.76, "inch"), "inch") == 111.76


@pytest.mark.parametrize("unit", ["ft", "", "CM", None])
def test_unknown_unit_is_rejected(unit):
    with pytest.raises(ValueError, match="Unsupported unit"):
        to_cm(1, unit)
    with pytest.raises(ValueError, match="Unsupported unit"):
        from_cm(1, unit)
