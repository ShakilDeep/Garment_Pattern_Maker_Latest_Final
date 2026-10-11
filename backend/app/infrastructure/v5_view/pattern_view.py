"""Adapter: a named block's draft -> the V5 pattern dict (T141b).

The keys match V5 drafts (`domain/drafting.py`) so the views, projections and DTOs read it unchanged.
`geometry_source: "v6"` marks that the V6 pieces are the geometry and this dict is only their view.
`seam_allowance` is None because allowances are per edge, carried by the V6 style, never one number.
"""
import json
from collections.abc import Mapping
from hashlib import sha256

from app.domain.blocks.base import NamedBlock

SCHEMA_VERSION = 1
V6_SOURCE = "v6"


def pattern_view(block: NamedBlock, values: Mapping[str, float], size: str, pieces: list[dict]) -> dict:
    measurements = dict(values)
    inputs = json.dumps({"measurements": measurements, "size": size, "profile": block.id}, sort_keys=True)
    return {
        "size": size, "profile": block.id, "input_hash": sha256(inputs.encode()).hexdigest(),
        "pieces": pieces, "assumptions": [], "measurements": measurements, "seam_allowance": None,
        "profile_metadata": {"id": block.id, "garment_family": block.family, "calibration": block.calibration},
        "schema_version": SCHEMA_VERSION, "calibration": block.calibration, "geometry_source": V6_SOURCE,
    }
