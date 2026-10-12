"""One 1078375 size graded from chart values (T145; owner decisions 2026-10-12, docs/grading/shirt.md).

The size starts from the PDS grading (already trued, so the solver only has to follow the chart's change).
Chart values replace their measurements and are never moved. A FOLLOWS measurement takes its leader's chart
change; the other half of a SHARED pair absorbs it, so the piece keeps its PDS step. The seam relations are
then trued again; a relation that can only be held by moving a chart value stays unheld, and the accuracy
suite reports it as an error. Each value says where it came from.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache, lru_cache

from app.domain.blocks.shirt.grading import FOLLOWS, PARTNER, SHARED, TRUED
from app.domain.blocks.shirt.reference import graded_measurements, reference_measurements
from app.domain.blocks.shirt.truing import held, relation_values, true_seams
from app.domain.pattern.point import quantize

FROM_BLOCK, CHART = "from_block", "chart"
CACHED_SIZES = 32
SOLVED_BY = {moved: relation for relation, name in TRUED.items()  # a solved measurement and its partner
             for moved in (name, PARTNER.get(name)) if moved is not None}


@dataclass(frozen=True)
class ChartGraded:
    values: dict[str, float]
    sources: dict[str, str]  # chart, follows:<leader>, balances:<input>, trued:<relation> or from_block
    unheld: tuple[str, ...]  # relations a chart value keeps from being trued


@cache
def _targets() -> dict[str, float]:
    return relation_values(reference_measurements())


def _carry(values: dict[str, float], sources: dict[str, str], chart: Mapping[str, float]) -> None:
    """Followers and pair partners take the chart's change (unless they are chart values themselves)."""
    pds = dict(values)
    deltas = {name: value - pds[name] for name, value in chart.items()}
    values.update(chart)
    sources.update(dict.fromkeys(chart, CHART))
    moves = [(follower, leader, 1, "follows") for follower, leader in FOLLOWS.items()]
    for first, second in SHARED:
        moves += [(second, first, -1, "balances"), (first, second, -1, "balances")]
    for name, cause, sign, kind in moves:
        if cause in deltas and name not in chart:
            values[name] = quantize(pds[name] + sign * deltas[cause])
            sources[name] = f"{kind}:{cause}"


def _graded(size: str, chart: tuple[tuple[str, float], ...]) -> ChartGraded:
    values = dict(graded_measurements(size))
    sources = dict.fromkeys(values, FROM_BLOCK)
    if not chart:
        return ChartGraded(values, sources, ())
    locked = frozenset(name for name, _ in chart)
    _carry(values, sources, dict(chart))
    trued = true_seams(values, _targets(), locked)
    for name, value in trued.items():
        if name not in locked and quantize(value) != values[name]:
            values[name] = quantize(value)
            sources[name] = f"trued:{SOLVED_BY[name]}"
    unheld = tuple(relation for relation in TRUED if relation not in held(locked))
    return ChartGraded(values, sources, unheld)


_cached = lru_cache(maxsize=CACHED_SIZES)(_graded)


def grade_from_chart(size: str, chart: Mapping[str, float]) -> ChartGraded:
    """``size`` of the PDS grading with ``chart`` values (by block input) in place; cached by content."""
    found = _cached(size, tuple(sorted(chart.items())))
    return ChartGraded(dict(found.values), dict(found.sources), found.unheld)
