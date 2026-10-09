"""Finishing settings (seam allowances, notches, corners, fabric shrinkage) read from ``data/finishing.json``.

Values are data so a factory can change them without code. Every value names its source; an edge role the
file does not list is a KeyError, never a silent default.
"""
import json
from functools import cache
from pathlib import Path
from types import MappingProxyType

from app.domain.finishing_model import Allowance, Evidence, FamilyFinishing, Finishing, Shrinkage

FINISHING_FILE = Path(__file__).with_name("data") / "finishing.json"
MAX_SHRINK_PCT = 50.0


def _allowance(raw: dict) -> Allowance:
    role = raw["role"]
    if raw["value_cm"] < 0:
        raise ValueError(f"Finishing allowance {role} must not be negative")
    if not str(raw.get("source", "")).strip():
        raise ValueError(f"Finishing allowance {role} needs a source")
    evidence = tuple(Evidence(e["piece"], (e["mid"][0], e["mid"][1]), e["length"]) for e in raw.get("evidence", []))
    return Allowance(role, float(raw["value_cm"]), raw["source"], raw.get("status", ""), evidence)


def _family(family_id: str, raw: dict) -> FamilyFinishing:
    allowances: dict[str, Allowance] = {}
    for item in map(_allowance, raw["allowances"]):
        if item.role in allowances:
            raise ValueError(f"Finishing family {family_id} lists allowance {item.role} twice")
        allowances[item.role] = item
    if raw["notch"]["depth_cm"] <= 0:
        raise ValueError(f"Finishing family {family_id} notch depth must be positive")
    return FamilyFinishing(raw["source_pds"], float(raw["fold_edge_cm"]), raw["corner"]["value"],
                           raw["corner"]["source"], float(raw["notch"]["depth_cm"]), MappingProxyType(allowances))


def _shrinkage(fabric: str, raw: dict) -> Shrinkage:
    if not {"warp_pct", "weft_pct"} <= raw.keys():
        raise ValueError(f"Fabric {fabric} needs warp_pct and weft_pct")
    if not all(0 <= raw[key] <= MAX_SHRINK_PCT for key in ("warp_pct", "weft_pct")):
        raise ValueError(f"Fabric {fabric} shrinkage must be 0-50 %")
    return Shrinkage(float(raw["warp_pct"]), float(raw["weft_pct"]), raw["source"])


def parse_finishing(data: dict) -> Finishing:
    families = {family_id: _family(family_id, raw) for family_id, raw in data["families"].items()}
    fabrics = {fabric: _shrinkage(fabric, raw) for fabric, raw in data.get("fabrics", {}).items()}
    return Finishing(MappingProxyType(families), MappingProxyType(fabrics))


@cache
def finishing() -> Finishing:
    return parse_finishing(json.loads(FINISHING_FILE.read_text(encoding="utf-8")))


def allowance(family: str, role: str) -> Allowance:
    families = finishing().families
    if family not in families:
        raise KeyError(f"No finishing settings for family {family!r}")
    if role not in families[family].allowances:
        raise KeyError(f"{family} has no finishing allowance {role!r}")
    return families[family].allowances[role]
