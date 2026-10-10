"""ShirtBlock (a ``NamedBlock``): the 1078375 men's regular short-sleeve shirt, drafted as docs/drafting/shirt.md.

Back yoke, grown-on 3.5 cm placket, collar on a band and a short set-in sleeve are the only construction the
client pattern has, so each is a fixed option. The shape constants are the base size L of the PDS; per-size
drafting arrives with grading (T131), so ``size`` does not change the draft yet.
"""
from collections.abc import Mapping

from app.domain.blocks.base import Calibration, Pieces, StyleOption
from app.domain.blocks.shirt.allowances import seam_allowance as piece_allowance
from app.domain.blocks.shirt.draft import draft_recipe
from app.domain.blocks.shirt.measures import RECIPES, REQUIRED, require
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.blocks.shirt.shape import shape
from app.domain.blocks.transforms import Transform
from app.domain.pattern.seam import SeamAllowance


class ShirtBlock:
    id: str = "shirt_1078375"
    version: str = "1"
    family: str = "shirt"
    calibration: Calibration = "client_approved"
    required: tuple[str, ...] = REQUIRED
    optional: tuple[str, ...] = ()
    options: tuple[StyleOption, ...] = (
        StyleOption("yoke", "Back yoke", ("split",), "split", fixed=True),
        StyleOption("placket", "Front placket", ("grown_on_3_5",), "grown_on_3_5", fixed=True),
        StyleOption("collar", "Collar", ("collar_band",), "collar_band", fixed=True),
        StyleOption("sleeve", "Sleeve", ("short_set_in",), "short_set_in", fixed=True),
    )
    transforms: tuple[Transform[Pieces], ...] = ()
    reference_size: str = "L"  # the PDS base size its measurements and shape constants come from

    def draft_pieces(self, measurements: Mapping[str, float], size: str, choices: Mapping[str, str]) -> Pieces:
        values = require(measurements)
        shapes = shape()
        return tuple(draft_recipe(recipe, values, shapes[recipe.id]) for recipe in RECIPES)

    def reference_measurements(self) -> Mapping[str, float]:
        return reference_measurements()

    def seam_allowance(self, piece_id: object) -> SeamAllowance:
        return piece_allowance(str(piece_id))
