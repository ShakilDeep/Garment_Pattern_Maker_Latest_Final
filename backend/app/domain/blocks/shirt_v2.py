"""The POM-driven shirt with Optitex-shaped curves (id ``shirt_v2``) as a registered V5 block.

It reads the same measurement chart as demo_v1 and drafts the same eight pieces, with every curve shaped
like the client's 1078375 PDS (``domain/shirt_v2``). Calibration stays ``demo``: it is not a client block.
"""
from collections.abc import Mapping

from app.domain.blocks.base import Calibration, StyleOption
from app.domain.blocks.transforms import Transform
from app.domain.profiles import SHIRT_V2
from app.domain.shirt_v2.draft import draft_v2


class ShirtV2Block:
    id: str = SHIRT_V2.id
    version: str = SHIRT_V2.version
    family: str = "shirt"
    calibration: Calibration = "demo"
    required: tuple[str, ...] = SHIRT_V2.required_measurements
    optional: tuple[str, ...] = SHIRT_V2.optional_measurements
    options: tuple[StyleOption, ...] = (
        StyleOption("yoke", "Back yoke", ("split",), "split", fixed=True),
        StyleOption("placket", "Front placket", ("cf_extension",), "cf_extension", fixed=True),
        StyleOption("sleeve", "Sleeve", ("long_with_cuff",), "long_with_cuff", fixed=True),
    )
    transforms: tuple[Transform, ...] = ()

    def draft(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> dict:
        return draft_v2(dict(measurements), size, SHIRT_V2)
