"""True a graded 1078375 size: each seam relation is brought back to its base value by one measurement.

In TRUED order, each relation (``seams.py``) is solved for its measurement with a secant (``numeric``), so
seams that sew together stay equal in every size, the band stays half neckline + 0.945 and the cap ease
stays 3.929 (docs/grading/shirt.md). The round repeats until every relation holds. A measurement in a
SHARED pair moves its partner the opposite way, so the pair's PDS step is kept.
"""
from collections.abc import Mapping

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


def _gaps(measures: Mapping[str, float], targets: Mapping[str, float]) -> dict[str, float]:
    values = relation_values(measures)
    return {relation: values[relation] - targets[relation] for relation in TRUED}


def _holds(measures: Mapping[str, float], targets: Mapping[str, float]) -> bool:
    return max(abs(gap) for gap in _gaps(measures, targets).values()) <= 2 * TOLERANCE


def _solve(measures: dict[str, float], relation: str, targets: Mapping[str, float]) -> dict[str, float]:
    name = TRUED[relation]

    def gap(value: float) -> float:
        return relation_values(_set(measures, name, value))[relation] - targets[relation]

    return _set(measures, name, solve_1d(gap, measures[name]))


def true_seams(measures: Mapping[str, float], targets: Mapping[str, float]) -> dict[str, float]:
    """The measurements with every TRUED relation at its target (rounds of one solve per relation)."""
    trued = dict(measures)
    for _ in range(ROUNDS):
        if _holds(trued, targets):
            return trued
        for relation in TRUED:
            trued = _solve(trued, relation, targets)
    if _holds(trued, targets):
        return trued
    raise ValueError("The graded size could not be trued: its relations work against each other")
