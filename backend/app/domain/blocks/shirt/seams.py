"""The 1078375 block's seam relations: seams that sew together, and the PDS cap, band and collar relations.

Each relation is a signed sum of seam lengths walked along named points. ``TRUED`` sums are 0 (equal seams,
the build plan's truing rule); ``AS_PDS`` sums keep the client PDS value (docs/drafting/shirt.md Q1, Q2).
The accuracy suite checks them per size, and grading holds them while it settles the free measurements.
"""
from collections.abc import Callable, Mapping

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
RELATIONS: Mapping[str, tuple[Term, ...]] = {**TRUED, **AS_PDS}


def seam_sum(terms: tuple[Term, ...], measure: Callable[[str, tuple[str, ...]], float]) -> float:
    """The relation's value with each named path measured by ``measure(piece id, path)``."""
    return sum(sign * measure(piece, path) for sign, piece, path in terms)
