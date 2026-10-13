"""Which accuracy suite checks each block (Strategy per reference): a block without one has no client reference.

A suite runs every check that compares a drafted style with its client PDS, in every drafted size, plus the
block's input definitions, which the chart checks measure back on the drafted sew line.
"""
from collections.abc import Callable, Mapping
from typing import NamedTuple

from app.application.accuracy.allowance_checks import allowance_checks
from app.application.accuracy.gap_checks import gap_checks
from app.application.accuracy.graded import graded_report
from app.application.accuracy.model import Check, Source, at_size
from app.application.accuracy.notch_pairs import notch_pair_checks
from app.application.accuracy.run import base_checks
from app.domain.blocks.registry import demo_block
from app.domain.blocks.shirt.allowances import seam_allowance
from app.domain.blocks.shirt.measures import DEFINITIONS, Definition
from app.domain.blocks.shirt.seams import PDS_UNPAIRED, RELATIONS
from app.domain.pattern.style import Style
from app.domain.reference import ReferenceStyle

PDS_BASE = Source("pds", "1078375 PDS: outlines exist at its base size only")


class Suite(NamedTuple):
    checks: Callable[[Style, ReferenceStyle], list[Check]]
    definitions: Mapping[str, Definition]


def _allowances(style: Style) -> list[Check]:
    """Every drafted size's cut line against the block's finishing.json widths (T144)."""
    sizes = (size for size in style.sizes if style.has_geometry(size))
    return [at_size(check, size) for size in sizes
            for check in allowance_checks(style.view(size), style.allowances, seam_allowance)]


def _at_pds_base(style: Style, reference: ReferenceStyle) -> list[Check]:
    """The PDS outline exists at the PDS base size only, so that size is compared, whatever size the project's
    pattern was generated at; until it is drafted the comparison cannot run, and that is an error."""
    size = reference.base_size
    if not style.has_geometry(size):
        return [Check(f"PDS base size {size} drafted", 0, f"draft or grade {size} to compare it with the PDS", False,
                      PDS_BASE)]
    view = style.view(size)
    at_outline = (*base_checks(view, reference), *gap_checks(view, reference),
                  *notch_pair_checks(view, RELATIONS, PDS_UNPAIRED))
    return [at_size(check, size) for check in at_outline]


def shirt_checks(style: Style, reference: ReferenceStyle) -> list[Check]:
    """Every drafted size (graded suite, allowances), and the PDS base size against the PDS outline (edges, seams,
    gaps) with its notch pairs."""
    return [*graded_report(style, reference).checks, *_allowances(style), *_at_pds_base(style, reference)]


SUITES: Mapping[str, Suite] = {"shirt_1078375": Suite(shirt_checks, DEFINITIONS)}


def profile_of(project: dict) -> str:
    """The block the project drafts with (the demo block until one is chosen, as drafting does)."""
    return (project.get("resolutions") or {}).get("profile", demo_block().id)
