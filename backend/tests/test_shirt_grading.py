"""T131: the 1078375 grading table, its derived sizes, and the seam relations held in every size."""
import json

import pytest

from app.domain.blocks.shirt.grading import CONSTANT, DRIVEN, FOLLOWS, SHARED, STARTED, classified, graded
from app.domain.blocks.shirt.measures import REQUIRED
from app.domain.blocks.shirt.reference import (
    GRADED_FILE,
    graded_measurements,
    graded_sizes,
    reference_measurements,
)
from app.domain.blocks.shirt.truing import relation_values, true_seams
from app.infrastructure.pds.shirt_grade_derive import derive_graded
from app.infrastructure.pds.shirt_grade_numbers import pds_steps


@pytest.fixture(scope="module")
def derived(pds_styles):
    return derive_graded(pds_styles["1078375"])


def test_every_measurement_is_graded_exactly_one_way():
    assert sorted(classified()) == sorted(REQUIRED) and len(classified()) == len(set(classified()))


def test_the_committed_grading_is_exactly_what_the_pds_gives(derived):
    committed = json.loads(GRADED_FILE.read_text(encoding="utf-8"))
    assert committed["sources"] == derived["sources"] and committed["targets"] == derived["targets"]
    for size, values in derived["sizes"].items():
        assert committed["sizes"][size] == pytest.approx(values, abs=2e-6), size


def test_sizes_are_the_pds_range_and_l_is_the_reference(pds_styles):
    assert graded_sizes() == pds_styles["1078375"].sizes == ("S", "M", "L", "XL", "XXL", "3XL")
    assert graded_measurements("L") == reference_measurements()


def test_driven_shared_follow_and_constant_steps_are_the_pds_steps(pds_styles):
    style, base = pds_styles["1078375"], reference_measurements()
    for size in ("S", "3XL"):
        steps, values = pds_steps(style, size), graded_measurements(size)
        for name, number in DRIVEN.items():
            assert values[name] - base[name] == pytest.approx(steps[number], abs=2e-6), (size, name)
        for pair, number in SHARED.items():
            assert sum(values[n] - base[n] for n in pair) == pytest.approx(steps[number], abs=2e-6), (size, pair)
        for name, leader in FOLLOWS.items():
            assert values[name] - base[name] == pytest.approx(values[leader] - base[leader], abs=2e-6)
        assert all(values[name] == base[name] for name in CONSTANT)


@pytest.mark.parametrize("size", ["S", "M", "XL", "XXL", "3XL"])
def test_every_seam_relation_keeps_its_base_value(size):
    base, values = relation_values(reference_measurements()), relation_values(graded_measurements(size))
    assert values == pytest.approx(base, abs=1e-5)


def test_grading_refuses_a_wrong_number_of_given_steps_and_an_unknown_size():
    with pytest.raises(ValueError, match=f"Grading needs {len(STARTED)} given steps, not 1"):
        graded(reference_measurements(), {}, [0.0])
    with pytest.raises(KeyError, match="The 1078375 grading has no size 4XL"):
        graded_measurements("4XL")


def test_a_relation_that_cannot_be_reached_is_refused_not_returned():
    base = reference_measurements()
    impossible = {**relation_values(base), "side seams": 500.0}  # a side seam 5 m longer than its partner
    with pytest.raises(ValueError, match="did not converge|non-positive shirt measurements"):
        true_seams(base, impossible)
