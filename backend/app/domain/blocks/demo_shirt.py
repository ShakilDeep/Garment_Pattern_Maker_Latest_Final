"""The V5 demo shirt (id ``demo_v1``) as a registered block: the same draft, byte for byte.

Its yoke, centre-front placket and long sleeve with cuff are built into the draft, so they are declared as
fixed options. Calibration stays ``demo``: it is not a client block.
"""
from collections.abc import Mapping

from app.domain.blocks.base import Calibration, StyleOption
from app.domain.blocks.transforms import Transform
from app.domain.drafting import draft
from app.domain.profiles import DEMO_V1


class DemoShirtBlock:
    id: str = DEMO_V1.id
    version: str = DEMO_V1.version
    family: str = "shirt"
    calibration: Calibration = "demo"
    required: tuple[str, ...] = DEMO_V1.required_measurements
    optional: tuple[str, ...] = DEMO_V1.optional_measurements
    options: tuple[StyleOption, ...] = (
        StyleOption("yoke", "Back yoke", ("split",), "split", fixed=True),
        StyleOption("placket", "Front placket", ("cf_extension",), "cf_extension", fixed=True),
        StyleOption("sleeve", "Sleeve", ("long_with_cuff",), "long_with_cuff", fixed=True),
    )
    transforms: tuple[Transform, ...] = ()

    def draft(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> dict:
        return draft(dict(measurements), size, self.id)
