"""Installed drafting strategies and their explicit capability metadata."""

from dataclasses import dataclass

from app.domain.catalog import ASSUMPTIONS, REQUIRED


@dataclass(frozen=True)
class DraftingProfile:
    id: str
    version: str
    garment_family: str
    calibration: str
    required_measurements: tuple[str, ...]
    optional_measurements: tuple[str, ...]
    validators: tuple[str, ...]
    seam_policy: str
    assumptions: tuple[str, ...]
    back_neck_drop_cm: float


DEMO_V1 = DraftingProfile(
    id="demo_v1",
    version="1.0.0",
    garment_family="mens_regular_long_sleeve_shirt",
    calibration="demo",
    required_measurements=tuple(REQUIRED),
    optional_measurements=("collar_buttoned_length", "collar_outside_edge", "sleeve_pleat_depth",
                           "forward_shoulder_neck", "forward_shoulder_armhole"),
    validators=("geometry", "edge_quality", "notches", "grainline", "seam_compatibility", "source_dimensions"),
    seam_policy="uniform_optional_polygon_offset",
    assumptions=tuple(ASSUMPTIONS) + (
        "Demo v1 shortens back/yoke half-shoulder by max(0, forward_shoulder_armhole - forward_shoulder_neck); not a client block.",
        "Demo v1 places sleeve placket/pleat notches on the outline from source lengths; not a construction block.",
    ),
    back_neck_drop_cm=2.0,
)

SHIRT_V2 = DraftingProfile(
    id="shirt_v2",
    version="2.0.0",
    garment_family="mens_regular_long_sleeve_shirt",
    calibration="demo",
    required_measurements=tuple(REQUIRED),
    optional_measurements=DEMO_V1.optional_measurements + ("waist_position_hps", "hem_curve", "back_neck_drop"),
    validators=DEMO_V1.validators,
    seam_policy=DEMO_V1.seam_policy,
    assumptions=tuple(a for a in ASSUMPTIONS if not a.startswith(("Curves use", "Body widths"))) + (
        ("Curves are cubic Béziers shaped like the client's Optitex 1078375 sew lines (neckline, armholes, hems, "
         "yoke, sleeve cap, collar, band); their end points come from this chart."),
        "Front/back split of chest, waist and hem follows the 1078375 block (front about 51 %), not half and half.",
        "Collar and band are the 1078375 PDS shapes rescaled to the drafted neckline and the chart's widths.",
        "Notches are the two the PDS has: yoke shoulder and sleeve crown, plus the source sleeve placket/pleat marks.",
    ),
    back_neck_drop_cm=2.0,
)

PROFILES = {DEMO_V1.id: DEMO_V1, SHIRT_V2.id: SHIRT_V2}


def get_profile(profile_id):
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Drafting profile is not installed: {profile_id}") from exc

