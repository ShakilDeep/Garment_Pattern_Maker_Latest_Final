"""Accuracy suite results: one ``Check`` per rule, with the measured value, its limit and where the rule comes from."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    limit: str
    passed: bool
    source: str


@dataclass(frozen=True)
class Report:
    checks: tuple[Check, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def near(name: str, value: float, target: float, tolerance: float, source: str) -> Check:
    """Passes when ``value`` is within ``tolerance`` of ``target`` (both in cm)."""
    return Check(name, value, f"{target:.3f} ± {tolerance} cm", abs(value - target) <= tolerance, source)
