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

PROFILES = {DEMO_V1.id: DEMO_V1}


def get_profile(profile_id):
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Drafting profile is not installed: {profile_id}") from exc

