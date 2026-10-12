"""Which accuracy suite checks each block (Strategy per reference): a block without one has no client reference.

A suite runs every check that compares a drafted style with its client PDS, in every drafted size, plus the
block's input definitions, which the chart checks measure back on the drafted sew line.
"""
from collections.abc import Callable, Mapping
from typing import NamedTuple

from app.application.accuracy.gap_checks import gap_checks
from app.application.accuracy.graded import graded_report
from app.application.accuracy.model import Check, at_size
from app.application.accuracy.run import base_checks
from app.domain.blocks.registry import demo_block
from app.domain.blocks.shirt.measures import DEFINITIONS, Definition
from app.domain.pattern.style import Style
from app.domain.reference import ReferenceStyle


class Suite(NamedTuple):
    checks: Callable[[Style, ReferenceStyle], list[Check]]
    definitions: Mapping[str, Definition]


def shirt_checks(style: Style, reference: ReferenceStyle) -> list[Check]:
    """Every drafted size (graded suite), and the base size against the PDS outline (edges, seams, gaps)."""
    base = style.view(style.base_size)
    against_outline = (*base_checks(base, reference), *gap_checks(base, reference))
    at_base = [at_size(check, style.base_size) for check in against_outline]
    return [*graded_report(style, reference).checks, *at_base]


SUITES: Mapping[str, Suite] = {"shirt_1078375": Suite(shirt_checks, DEFINITIONS)}


def profile_of(project: dict) -> str:
    """The block the project drafts with (the demo block until one is chosen, as drafting does)."""
    return (project.get("resolutions") or {}).get("profile", demo_block().id)
