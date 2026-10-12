"""Accuracy suite per size for the graded 1078375 style (build plan M4, T131).

Gated in every size (the build plan's M4 test): SUM_AREA (every piece's cut area times its cut count) within
3 % of the PDS size total, every seam relation at its base value, simple counter-clockwise outlines; and the
total area grows from size to size. Only drafted sizes are checked; the base size's own seams are checked
against the PDS by ``run.base_checks``, so here they are measured in the other sizes only. Each piece's cut length, width and area against its PDS numbers is gated
at the base size (M3) and reported in the other sizes: with the cap ease held at 3.93 the graded Sleeve runs
-3 % to +9 % of the PDS sleeve, a pattern-maker review point (docs/grading/shirt.md, owner 2026-10-10).
"""
from dataclasses import replace
from itertools import pairwise

from app.application.accuracy.model import Check, Report, Source, at_size, near
from app.application.accuracy.piece_checks import AREA_SHARE, size_checks
from app.application.accuracy.run import outlines_check
from app.domain.blocks.shirt.seams import RELATIONS, seam_sum
from app.domain.blocks.sketch.named_edges import path_length
from app.domain.pattern.piece import Piece
from app.domain.pattern.style import Style
from app.domain.reference import ReferenceStyle

RELATION_CM = 0.1  # seams that sew together stay equal within the build plan's 0.1 cm in every size
PLAN = Source("pds", "build plan M4 (1078375 graded)")
GRADING = Source("setting", "build plan M4: seams keep their base value; areas grow with size")


def _relations(pieces: tuple[Piece, ...]) -> dict[str, float]:
    by_id = {str(piece.id): piece for piece in pieces}
    return {name: seam_sum(terms, lambda pid, path: path_length(by_id[pid], path)) for name, terms in RELATIONS.items()}


def _size_checks(size: str, pieces: tuple[Piece, ...], reference: ReferenceStyle) -> tuple[list[Check], float]:
    by_name, gate = {piece.name: piece for piece in reference.pieces}, size == reference.base_size
    checks, total = [], 0.0
    for piece in pieces:
        for check in size_checks(piece, by_name[piece.name].geometry[size]):
            checks.append(replace(at_size(check, size), gate=gate))
            if check.name.endswith("cut area"):
                total += check.value * piece.cut.total
    pds = reference.totals[size].area_m2
    passed = abs(total - pds) <= AREA_SHARE * pds
    checks.append(Check(f"{size} SUM_AREA", total, f"3 % of {pds} m2", passed, PLAN, size=size))
    checks.append(at_size(outlines_check(pieces), size))
    return checks, total


def _relation_checks(size: str, pieces: tuple[Piece, ...], base: dict[str, float]) -> list[Check]:
    relations = _relations(pieces)
    return [at_size(near(name, relations[name], base[name], RELATION_CM, GRADING), size) for name in RELATIONS]


def graded_report(style: Style, reference: ReferenceStyle) -> Report:
    base = _relations(style.view(style.base_size))
    checks: list[Check] = []
    totals = []
    for size in (size for size in style.sizes if style.has_geometry(size)):
        pieces = style.view(size)
        size_checks_, total = _size_checks(size, pieces, reference)
        checks += size_checks_
        totals.append(total)
        if size != style.base_size:
            checks += _relation_checks(size, pieces, base)
    if len(totals) > 1:  # a single-size style has no growth to check
        smallest_step = min(b - a for a, b in pairwise(totals))
        checks.append(Check("areas grow size to size", smallest_step, "every size larger than the one before",
                            smallest_step > 0, GRADING))
    return Report(tuple(checks))
