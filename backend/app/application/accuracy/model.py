"""Accuracy suite results: one ``Check`` per rule, with the measured value, its limit and where the limit comes from.

A limit's source is the chart (a POM tolerance), the client PDS (a number of the reference pattern) or a
setting (a spec or owner rule, e.g. "seams that sew together are equal"); spec §9 shows it per check.
"""
from dataclasses import dataclass, replace
from typing import Literal

SourceKind = Literal["chart", "pds", "setting"]


@dataclass(frozen=True)
class Source:
    kind: SourceKind
    ref: str  # the document and section the limit is taken from


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    limit: str
    passed: bool
    source: Source
    gate: bool = True  # False: reported for review, but a miss does not fail the suite
    size: str | None = None
    piece: str | None = None
    edge: str | None = None


@dataclass(frozen=True)
class Report:
    checks: tuple[Check, ...]

    @property
    def errors(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if check.gate and not check.passed)

    @property
    def passed(self) -> bool:
        return not self.errors


def near(name: str, value: float, target: float, tolerance: float, source: Source) -> Check:
    """Passes when ``value`` is within ``tolerance`` of ``target`` (both in cm)."""
    return Check(name, value, f"{target:.3f} ± {tolerance} cm", abs(value - target) <= tolerance, source)


def at_size(check: Check, size: str) -> Check:
    """The check as one size's row: its name starts with the size."""
    return replace(check, name=f"{size} {check.name}", size=size)
