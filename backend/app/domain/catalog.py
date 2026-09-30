from app.domain.catalog_source_codes import MAPPING

__all__ = ["ASSUMPTIONS", "MAPPING", "PROFILE", "REQUIRED", "SIZES"]

SIZES = ("S", "M", "L", "XL", "XXL", "3XL")
PROFILE = "mens_regular_long_sleeve_shirt_demo_v1"
REQUIRED = [
    "back_length_hps",
    "front_length_hps",
    "half_chest",
    "half_waist",
    "half_bottom_opening",
    "yoke_depth_cb",
    "shoulder_slope",
    "shoulder_point_to_point",
    "half_armhole_straight",
    "half_bicep",
    "sleeve_cap_height",
    "sleeve_length",
    "cuff_width",
    "cuff_edge_to_edge",
    "sleeve_placket_length",
    "sleeve_placket_width",
    "collar_width_cb",
    "collar_band_width_cb",
    "neck_width",
    "front_neck_drop",
    "front_placket_width",
]
ASSUMPTIONS = [
    "Demo profile only; client base blocks and physical sample calibration are not supplied.",
    "Body widths allocate half of each flat half-body measurement to each front/back half.",
    "Source shoulder-to-cuff sleeve length includes cuff; sleeve body subtracts cuff width.",
    "Curves use sampled quadratic construction with 24 segments; no shrinkage or additional ease.",
    "Back neck drop is 2 cm. Collar attachment follows generated neckline, not a certified collar block.",
    "Front placket is a center-front extension using the explicitly resolved source width.",
    "Collar point and center-back height use source values; buttoned length and outside edge are checked against source as calibration targets.",
    "Back and yoke are unfolded before nesting. Grain follows the vertical piece axis; no rotation.",
    "Seam allowance defaults to zero. Positive allowance is a polygon offset, not a manufacturing standard.",
    "Pocket omitted because no pocket dimensions are supplied. Sleeve cap mismatch remains a visible warning.",
]
