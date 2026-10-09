"""Finishing settings data model: seam allowances with their PDS evidence, notches, corners, fabric shrinkage."""
from dataclasses import dataclass
from types import MappingProxyType

from app.domain.interchange import Point


@dataclass(frozen=True)
class Evidence:
    piece: str
    mid: Point
    length: float


@dataclass(frozen=True)
class Allowance:
    role: str
    value_cm: float
    source: str
    status: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class FamilyFinishing:
    source_pds: str
    fold_edge_cm: float
    corner: str
    corner_source: str
    notch_depth_cm: float
    allowances: MappingProxyType[str, Allowance]


@dataclass(frozen=True)
class Shrinkage:
    warp_pct: float
    weft_pct: float
    source: str


@dataclass(frozen=True)
class Finishing:
    families: MappingProxyType[str, FamilyFinishing]
    fabrics: MappingProxyType[str, Shrinkage]
