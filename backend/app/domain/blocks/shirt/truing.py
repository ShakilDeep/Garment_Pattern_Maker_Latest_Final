"""True a graded 1078375 size: each seam relation is brought back to its base value by one measurement.

In TRUED order, each relation (``seams.py``) is solved for its measurement with a secant (``numeric``), so
seams that sew together stay equal in every size, the band stays half neckline + 0.945 and the cap ease
stays 3.929 (docs/grading/shirt.md). The round repeats until every relation holds. A measurement in a
SHARED pair moves its partner the opposite way, so the pair's PDS step is kept. ``locked`` measurements (chart
values, T145) are never moved: a relation solved with one, or with its partner, is left unheld.
"""
from collections.abc import Mapping
from collections.abc import Set as AbstractSet

from app.domain.blocks.shirt.block import ShirtBlock
from app.domain.blocks.shirt.grading import PARTNER, TRUED
from app.domain.blocks.shirt.seams import RELATIONS, seam_sum
from app.domain.blocks.sketch.named_edges import path_length
from app.domain.numeric.secant import TOLERANCE, solve_1d

ROUNDS = 20


def relation_values(measures: Mapping[str, float]) -> dict[str, float]:
    pieces = {str(piece.id): piece for piece in ShirtBlock().draft_pieces(measures, "", {})}
    return {name: seam_sum(terms, lambda pid, path: path_length(pieces[pid], path))
            for name, terms in RELATIONS.items()}


def _set(measures: dict[str, float], name: str, value: float) -> dict[str, float]:
    moved = {**measures, name: value}
    if name in PARTNER:
        partner = PARTNER[name]
        moved[partner] = measures[partner] - (value - measures[name])
    return moved


def held(locked: AbstractSet[str] = frozenset()) -> tuple[str, ...]:
    """The relations truing can hold: neither their measurement nor its SHARED partner is locked."""
    return tuple(relation for relation, name in TRUED.items()
                 if name not in locked and PARTNER.get(name) not in locked)


def _holds(measures: Mapping[str, float], targets: Mapping[str, float], relations: tuple[str, ...]) -> bool:
    values = relation_values(measures)
    return all(abs(values[relation] - targets[relation]) <= 2 * TOLERANCE for relation in relations)


def _solve(measures: dict[str, float], relation: str, targets: Mapping[str, float]) -> dict[str, float]:
    name = TRUED[relation]

    def gap(value: float) -> float:
        return relation_values(_set(measures, name, value))[relation] - targets[relation]

    return _set(measures, name, solve_1d(gap, measures[name]))


def true_seams(measures: Mapping[str, float], targets: Mapping[str, float],
               locked: AbstractSet[str] = frozenset()) -> dict[str, float]:
    """The measurements with every relation in ``held(locked)`` at its target (rounds of one solve each)."""
    trued, relations = dict(measures), held(locked)
    for _ in range(ROUNDS):
        if _holds(trued, targets, relations):
            return trued
        for relation in relations:
            trued = _solve(trued, relation, targets)
    if _holds(trued, targets, relations):
        return trued
    raise ValueError("The graded size could not be trued: its relations work against each other")
