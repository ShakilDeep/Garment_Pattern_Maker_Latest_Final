"""The AAMA/ASTM D6673 layer map and unit flags — the code's single source of truth for the DXF layout.

Layer numbers are the standard AAMA numbering the build plan lists. AAMA "METRIC" files are millimetres and
"ENGLISH" files inches; R12 has no $INSUNITS, so the ``UNITS:`` header text is the only unit flag.
"""
from enum import IntEnum

AAMA_VERSION = "ANSI/AAMA VERSION: 1.0.0"
CM_PER_INCH = 2.54
MODEL_DECIMALS = 6  # read-back coordinates land on the 1e-6 cm model grid (domain/tolerances.py)


class AamaLayer(IntEnum):
    CUT = 1  # boundary (cut line) and piece text
    TURN = 2  # turn points (corners) of the cut line
    CURVE = 3  # curve points of the cut line
    NOTCH = 4
    GRADE_REFERENCE = 5
    MIRROR = 6  # fold line of a piece cut on the fold
    GRAIN = 7
    INTERNAL = 8
    CUTOUT = 11
    DRILL = 13
    SEW = 14
    ANNOTATION = 15

    @property
    def dxf(self) -> str:
        return str(int(self))


# unit -> (AAMA flag, drawing units per cm)
UNITS: dict[str, tuple[str, float]] = {"mm": ("METRIC", 10.0), "inch": ("ENGLISH", 1 / CM_PER_INCH)}
CM_PER_DRAWING_UNIT = {flag: 1 / scale for flag, scale in UNITS.values()}


def unit_scale(unit: str) -> tuple[str, float]:
    if unit not in UNITS:
        raise ValueError(f"Unsupported AAMA unit {unit!r}; use mm (METRIC) or inch (ENGLISH)")
    return UNITS[unit]


def cm_per_unit(flag: str) -> float:
    if flag not in CM_PER_DRAWING_UNIT:
        raise ValueError(f"Unsupported AAMA units {flag!r}")
    return CM_PER_DRAWING_UNIT[flag]
