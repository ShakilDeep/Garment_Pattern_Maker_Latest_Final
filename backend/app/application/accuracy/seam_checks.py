"""Seam checks of the 1078375 block: seams that sew together, sleeve cap ease, collar and band against the neck.

Each check is a signed sum of seam lengths walked along named points. Seams that sew together must be equal
within 0.1 cm (the build plan's truing rule). The cap ease, band and collar targets are the client PDS values
of the same sum (docs/drafting/shirt.md Q1, Q2), not the build plan's generic 0-1 cm and 0.3 cm rules, which
the client's own pattern does not follow.
"""
from collections.abc import Callable, Mapping
from itertools import pairwise

from app.application.accuracy.model import Check, near
from app.domain.blocks.sketch.named_edges import path_length
from app.domain.geom.polyline_ops import length
from app.domain.pattern.piece import Piece
from app.infrastructure.pds.shirt_derive import NamedPiece

TOLERANCE_CM = 0.1
Term = tuple[int, str, tuple[str, ...]]  # sign, piece id, named path

_ARMHOLE: tuple[Term, ...] = ((-1, "FRT", ("SP", "UA")), (-1, "back", ("yoke_armhole", "UA")),
                              (-1, "back_YK", ("SP", "yoke_armhole")))
_NECK: tuple[Term, ...] = ((-1, "FRT", ("CF_neck", "HPS")), (-1, "back_YK", ("CB_neck", "HPS")))

TRUED: Mapping[str, tuple[Term, ...]] = {
    "side seams": ((1, "FRT", ("UA", "side_hem")), (-1, "back", ("UA", "side_hem"))),
    "shoulder seam": ((1, "FRT", ("HPS", "SP")), (-1, "back_YK", ("HPS", "SP"))),
    "yoke seam": ((1, "back", ("CB_yoke", "yoke_armhole")), (-1, "back_YK", ("yoke_armhole", "CB_yoke"))),
}
AS_PDS: Mapping[str, tuple[Term, ...]] = {
    "sleeve cap ease": ((1, "Sleeve", ("UA_back", "cap_crown", "UA_front")), *_ARMHOLE),
    "band neck edge vs neckline": ((1, "BND_TOP", ("band_neck_end", "CB_band_neck")), *_NECK),
    "collar on band top edge": ((1, "CLR", ("CB_collar_neck", "collar_neck_end")),
                                (-1, "BND_TOP", ("CB_band_top", "band_top_end"))),
}


def _sum(terms: tuple[Term, ...], measure: Callable[[str, tuple[str, ...]], float]) -> float:
    return sum(sign * measure(piece, path) for sign, piece, path in terms)


def _pds_path(named: Mapping[str, NamedPiece], piece: str, path: tuple[str, ...]) -> float:
    return sum(length(named[piece].run(a, b)) for a, b in pairwise(path))


def seam_checks(pieces: Mapping[str, Piece], named: Mapping[str, NamedPiece]) -> list[Check]:
    def drafted(piece: str, path: tuple[str, ...]) -> float:
        return path_length(pieces[piece], path)

    checks = [near(name, _sum(terms, drafted), 0.0, TOLERANCE_CM, "build plan: seams that sew together are equal")
              for name, terms in TRUED.items()]
    for name, terms in AS_PDS.items():
        target = _sum(terms, lambda piece, path: _pds_path(named, piece, path))
        checks.append(near(name, _sum(terms, drafted), target, TOLERANCE_CM, "1078375 PDS, shirt.md Q1/Q2"))
    return checks
