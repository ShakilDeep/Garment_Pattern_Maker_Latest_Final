"""Seam checks of the 1078375 block (relations in ``domain/blocks/shirt/seams.py``).

Seams that sew together must be equal within 0.1 cm (the build plan's truing rule). The cap ease, band and
collar targets are the client PDS values of the same sums (docs/drafting/shirt.md Q1, Q2), not the build
plan's generic 0-1 cm and 0.3 cm rules, which the client's own pattern does not follow.
"""
from collections.abc import Mapping
from itertools import pairwise

from app.application.accuracy.model import Check, near
from app.domain.blocks.shirt.seams import AS_PDS, TRUED, seam_sum
from app.domain.blocks.sketch.named_edges import path_length
from app.domain.geom.polyline_ops import length
from app.domain.pattern.piece import Piece
from app.infrastructure.pds.shirt_named import NamedPiece

TOLERANCE_CM = 0.1


def _pds_path(named: Mapping[str, NamedPiece], piece: str, path: tuple[str, ...]) -> float:
    return sum(length(named[piece].run(a, b)) for a, b in pairwise(path))


def seam_checks(pieces: Mapping[str, Piece], named: Mapping[str, NamedPiece]) -> list[Check]:
    def drafted(piece: str, path: tuple[str, ...]) -> float:
        return path_length(pieces[piece], path)

    checks = [near(name, seam_sum(terms, drafted), 0.0, TOLERANCE_CM, "build plan: seams that sew together are equal")
              for name, terms in TRUED.items()]
    for name, terms in AS_PDS.items():
        target = seam_sum(terms, lambda piece, path: _pds_path(named, piece, path))
        checks.append(near(name, seam_sum(terms, drafted), target, TOLERANCE_CM, "1078375 PDS, shirt.md Q1/Q2"))
    return checks
