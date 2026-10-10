"""Accuracy suite results: one ``Check`` per rule, with the measured value, its limit and where the rule comes from."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    limit: str
    passed: bool
    source: str
    gate: bool = True  # False: reported for review, but a miss does not fail the suite


@dataclass(frozen=True)
class Report:
    checks: tuple[Check, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks if check.gate)


def near(name: str, value: float, target: float, tolerance: float, source: str) -> Check:
    """Passes when ``value`` is within ``tolerance`` of ``target`` (both in cm)."""
    return Check(name, value, f"{target:.3f} ± {tolerance} cm", abs(value - target) <= tolerance, source)
