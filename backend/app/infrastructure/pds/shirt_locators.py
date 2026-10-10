"""Where each named point of the 1078375 block sits in the client PDS marker view (docs/drafting/shirt.md).

Only locators: each names the PDS sew-line vertex within 0.05 cm, and the exact value is read from the PDS.
``None`` marks a point that is the foot of the piece's notch on the sew line (the sleeve crown).
"""
from app.domain.interchange import Point

LOCATORS: dict[str, dict[str, Point | None]] = {
    "FRT": {"FE_top": (74.54, -36.39), "CF_top": (74.54, -33.19), "CF_neck": (72.33, -33.19),
            "HPS": (78.90, -24.57), "SP": (72.51, -8.30), "UA": (52.92, -1.83), "side_hem": (6.12, -2.38),
            "FE_hem": (4.87, -36.38)},
    "back": {"CB_yoke": (68.01, -80.66), "yoke_armhole": (66.94, -56.61), "UA": (52.62, -50.90),
             "side_hem": (5.82, -51.46), "CB_hem": (4.52, -80.66)},
    "back_YK": {"CB_neck": (85.08, -80.66), "HPS": (90.31, -71.48), "SP": (85.60, -54.70),
                "yoke_armhole": (73.03, -56.66), "CB_yoke": (73.04, -80.66)},
    "CLR": {"CB_collar_neck": (126.20, -72.99), "collar_neck_end": (147.58, -75.22),
            "collar_point": (148.90, -69.36), "CB_collar_outer": (126.20, -68.20)},
    "BND_TOP": {"CB_band_top": (127.11, -96.71), "band_top_end": (150.34, -99.03),
                "band_neck_end": (151.49, -96.88), "CB_band_neck": (127.11, -93.40)},
    "BND_IN": {"CB_band_top": (126.80, -84.80), "band_top_end": (150.04, -87.12),
               "band_neck_end": (151.19, -84.97), "CB_band_neck": (126.80, -81.49)},
    "Sleeve": {"hem_fold_back": (117.20, -43.70), "UA_back": (125.19, -46.37), "cap_crown": None,
               "UA_front": (125.19, -2.51), "hem_fold_front": (117.20, -5.19), "hem_front": (115.20, -4.53),
               "hem_back": (115.20, -44.36)},
}
