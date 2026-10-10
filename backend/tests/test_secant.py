"""T131: the 1-D secant solver that trues each seam relation by moving one measurement."""
import pytest

from app.domain.numeric.secant import solve_1d


def test_a_linear_equation_is_solved_in_one_step():
    assert solve_1d(lambda x: 3 * x - 6, 0.0) == pytest.approx(2.0, abs=1e-6)


def test_a_curved_equation_converges_from_a_nearby_start():
    assert solve_1d(lambda x: x * x - 2, 1.0) == pytest.approx(2 ** 0.5, abs=1e-6)  # roots are taken on the 1e-6 cm model grid


def test_an_equation_without_a_root_is_refused():
    with pytest.raises(ValueError, match="did not converge"):
        solve_1d(lambda x: x * x + 1, 0.5)


def test_a_flat_equation_is_refused():
    with pytest.raises(ValueError, match="does not change"):
        solve_1d(lambda x: 4.0, 1.0)
