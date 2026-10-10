"""How each 1078375 measurement grades from the base size L (docs/grading/shirt.md, T131).

The client gave no chart and the PDS keeps its grade rules in an unreadable binary part, so every size is
built from what the PDS XML does give per size and piece (owner's decisions, 2026-10-10). Each measurement
is exactly one of:
- DRIVEN: its step from L is a PDS piece number's step (it sets that piece's extreme on that axis);
- SHARED: two measurements set one extreme together; their sum takes the step;
- FOLLOWS: it moves with another measurement (hem widths with the chest);
- CONSTANT: construction the tech pack fixes (3.5 cm placket, 2 cm turn-up);
- TRUED: solved so one seam relation (``seams.py``) keeps its base value (``truing.py``);
- PROPORTIONAL: its L value scaled by its own piece's PDS growth on its axis (GROWS_WITH overrides the
  axis: the armhole depths grow with the chest, the owner's decision of 2026-10-10).
"""
from collections.abc import Mapping, Sequence
from typing import Literal

PdsNumber = tuple[str, str]  # PDS piece name, GeomInfo field

DRIVEN: Mapping[str, PdsNumber] = {
    "front_length": ("FRT", "size_x_cm"),
    "half_chest_front": ("FRT", "size_y_cm"),
    "back_length": ("back", "size_x_cm"),
    "half_chest_back": ("back", "size_y_cm"),
    "across_back_half": ("back YK", "size_y_cm"),
    "collar_length": ("CLR", "size_x_cm"),
    "band_length": ("BND TOP", "size_x_cm"),
    "bicep": ("Sleeve", "size_y_cm"),
}
SHARED: Mapping[tuple[str, str], PdsNumber] = {  # the first's step is proportional or trued; the second balances
    ("yoke_depth_cb", "back_neck_rise"): ("back YK", "size_x_cm"),
    ("cap_height", "underarm_height"): ("Sleeve", "size_x_cm"),
}
FOLLOWS: Mapping[str, str] = {"front_hem_width": "half_chest_front", "back_hem_width": "half_chest_back"}
CONSTANT: tuple[str, ...] = ("front_extension", "placket_rise", "hem_turnup")
TRUED: Mapping[str, str] = {  # seam relation (``seams.py``) -> the measurement solved to hold it
    "band neck edge vs neckline": "front_neck_width",
    "shoulder seam": "front_shoulder_width",
    "side seams": "back_armhole_depth",
    "sleeve cap ease": "cap_height",
    "yoke seam": "yoke_seam_width",
    "collar on band top edge": "collar_neck_reach",
}
PROPORTIONAL: tuple[str, ...] = (
    "front_neck_drop", "front_shoulder_drop", "front_armhole_depth", "back_yoke_drop", "back_yoke_width",
    "back_neck_width", "yoke_shoulder_drop", "collar_width_cb", "collar_point_rise", "band_height_cb",
    "band_top_reach", "cap_front_width", "sleeve_hem_width",
)
GROWS_WITH: Mapping[str, Literal["x", "y"]] = {"front_armhole_depth": "y", "back_armhole_depth": "y"}
PARTNER: Mapping[str, str] = {first: second for first, second in SHARED}  # first -> the one that balances it
STARTED: tuple[str, ...] = (*PROPORTIONAL, *(m for m in TRUED.values() if m not in PARTNER),
                            *PARTNER)  # measurements whose step ``graded`` takes as given


def classified() -> tuple[str, ...]:
    """Every measurement the table grades (each must appear exactly once)."""
    shared = tuple(name for pair in SHARED for name in pair)
    trued = tuple(m for m in TRUED.values() if m not in shared)
    return (*DRIVEN, *shared, *FOLLOWS, *CONSTANT, *trued, *PROPORTIONAL)


def graded(base: Mapping[str, float], steps: Mapping[PdsNumber, float], given: Sequence[float]) -> dict[str, float]:
    """One size before truing: L values plus PDS steps, follows, and the ``given`` steps of STARTED."""
    if len(given) != len(STARTED):
        raise ValueError(f"Grading needs {len(STARTED)} given steps, not {len(given)}")
    step = dict(zip(STARTED, given, strict=True))
    for name, number in DRIVEN.items():
        step[name] = steps[number]
    for (first, second), number in SHARED.items():
        step[second] = steps[number] - step[first]
    for name, leader in FOLLOWS.items():
        step[name] = step[leader]
    for name in CONSTANT:
        step[name] = 0.0
    return {name: base[name] + step[name] for name in base}
