"""Length units: the model is centimetres; other units are converted once, exactly, at the boundary."""
from typing import Literal

from app.domain.tolerances import MODEL_DECIMALS

SourceUnit = Literal["cm", "inch"]
OutputUnit = Literal["cm", "mm", "inch"]

CM_PER_INCH = 2.54  # exact by definition (international inch, 1959)
MM_PER_CM = 10
_CM_PER_UNIT = {"cm": 1.0, "mm": 1 / MM_PER_CM, "inch": CM_PER_INCH}


def _cm_per(unit: str) -> float:
    if unit not in _CM_PER_UNIT:
        raise ValueError(f"Unsupported unit {unit!r}; use cm, mm or inch")
    return _CM_PER_UNIT[unit]


def to_cm(value: float, unit: str) -> float:
    """`value` in `unit` as centimetres, on the 1e-6 model grid; cm comes back untouched (same hash input)."""
    factor = _cm_per(unit)
    return value if unit == "cm" else round(value * factor, MODEL_DECIMALS) + 0.0


def from_cm(value: float, unit: str) -> float:
    """Centimetres as `unit`, rounded to 1e-6 of that unit (+0.0 folds -0.0)."""
    return round(value / _cm_per(unit), MODEL_DECIMALS) + 0.0
