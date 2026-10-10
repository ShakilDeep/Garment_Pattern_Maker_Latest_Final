"""Grade the 1078375 block per size from the client PDS per-size numbers (docs/grading/shirt.md, T131).

Each size: the grading table's PDS steps, follows and constants; proportional steps for the rest; then the
seam relations trued to their base values. The result is written by scripts/derive_shirt_1078375.py and a
test re-derives it.
"""
from app.domain.blocks.shirt.grading import (
    CONSTANT,
    DRIVEN,
    FOLLOWS,
    PROPORTIONAL,
    SHARED,
    TRUED,
    graded,
)
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.blocks.shirt.truing import relation_values, true_seams
from app.domain.pattern.point import quantize
from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.shirt_grade_numbers import axis_number, pds_steps, proportional_steps

NOTE = "Graded from the 1078375 PDS per-size numbers by scripts/derive_shirt_1078375.py. Do not edit."


def _sources() -> dict[str, str]:
    sources = {name: f"PDS {piece} {field} step from L" for name, (piece, field) in DRIVEN.items()}
    for (first, second), (piece, field) in SHARED.items():
        sources[second] = f"PDS {piece} {field} step from L, less the step of {first}"
    sources |= {name: f"follows {leader}" for name, leader in FOLLOWS.items()}
    sources |= {name: "constant (tech pack construction)" for name in CONSTANT}
    for name in (*PROPORTIONAL, "yoke_depth_cb"):
        piece, field = axis_number(name)
        sources[name] = f"proportional: L value x PDS {piece} {field} growth"
    return sources | {name: f"trued: {relation} held at its L value" for relation, name in TRUED.items()}


def derive_graded(style: ReferenceStyle) -> dict:
    base = reference_measurements()
    targets = relation_values(base)
    sizes = {}
    for size in style.sizes:
        start = graded(base, pds_steps(style, size), proportional_steps(style, size, base))
        # The base size is the PDS reference itself: its relations are the targets, so it needs no truing.
        values = base if size == style.base_size else true_seams(start, targets)
        sizes[size] = {name: quantize(values[name]) for name in base}
    return {"source_pds": "1078375", "base_size": style.base_size, "note": NOTE, "sources": _sources(),
            "targets": {name: quantize(value) for name, value in targets.items()}, "sizes": sizes}
