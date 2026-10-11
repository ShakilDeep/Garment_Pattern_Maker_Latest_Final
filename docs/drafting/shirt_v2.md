# Drafting: shirt_v2 (measurement chart + Optitex 1078375 curve shapes)

**Status: DEMO calibration (2026-10-11).** The default drafting profile for a V5 project since 2026-10-11; `demo_v1` stays selectable under "Drafting profile". Code: `backend/app/domain/shirt_v2/`, block `blocks/shirt_v2.py`.

## Why

`demo_v1` drew every curve as a 3-point quadratic, the sleeve cap as a symmetric dome, the band as a rectangle and one arbitrary notch per piece. It also read "1/2 ARMHOLE (STRAIGHT)" as the armhole depth, which left each armhole about 20 cm shorter than its sleeve cap (Book2 L: cap 54.86 cm, armhole 34.50 cm).

## What shirt_v2 does

- **Same inputs and piece set as demo_v1.** It reads the same chart keys and drafts the same eight pieces, so grading, markers and exports work unchanged.
- **Curves.** Each curve is the matching 1078375 PDS sew-line curve (`data/shirt_1078375_shape.json`), stretched along x and y so its ends land on the chart's points (`curves.py`). Curves keep the PDS angles where these are square: neck and hem at CF/CB, and the armhole level at the underarm.
  - Front: neckline, armhole, hem (square to CF), and the grown-on placket step above the neck point (PDS 2.21 cm).
  - Back: armhole, hem (square to CB). The yoke seam ends 1.96 cm inside the shoulder point, as on the PDS.
  - Yoke: neckline, armhole.
  - Sleeve: the PDS cap S-curve on the chart's bicep and cap height. The long body, wrist pleat and placket marks are the same as demo_v1.
  - Collar and band: the PDS CLR and BND TOP shapes. The band is rescaled so its neck edge equals the drafted half neckline plus the PDS overlap (0.93 cm). The collar sits on the band's top edge, set back by the PDS 1.92 cm. The chart sets the CB widths and the collar point length.
- **Chart reading.** "1/2 ARMHOLE (STRAIGHT)" is the straight line from the front shoulder point to the underarm point. Chest, waist and hem are split front/back in the 1078375 proportion (front 51.3 %).
- **Marks and grain.** The notches are the two the PDS has (yoke shoulder, sleeve crown) plus demo_v1's sleeve placket and pleat marks. The yoke is cut 2 (outer and inner), as on the PDS. Grain on the collar and band runs along their length.

## Accuracy (tests)

`tests/test_shirt_v2_accuracy.py` drafts charts that describe the PDS itself (`tests/shirt_v2_pds_poms.py`) and compares each piece with the PDS sew outline at L. It reports the largest gap (Hausdorff distance) and the area.

| Piece | demo_v1 gap | shirt_v2 gap | shirt_v2 area | Limit |
|---|---|---|---|---|
| Front | 4.83 cm | 0.25 cm | −0.2 % | 0.5 cm |
| Back | 3.81 cm | 0.87 cm | +0.5 % | 1.0 cm |
| Yoke | 2.89 cm | 0.06 cm | −0.1 % | 0.2 cm |
| Collar | 1.72 cm | 0.47 cm | +2.0 % | 0.6 cm |
| Band | 1.91 cm | 0.45 cm | +2.4 % | 0.6 cm |
| Sleeve cap | 3.14 cm | 0.11 cm | +0.1 % | 0.2 cm |

Every area limit is 3 % (build plan accuracy suite). The back misses the PDS's 1.07 cm yoke-seam drop at the armhole. `tests/test_shirt_v2_draft.py` checks the Book2 chart at every size. No size has a validation error or a flat vertex, and the cap stays within the 2 cm seam check of its whole armhole (front + back + yoke).

## Open questions for the pattern maker

1. Is "1/2 ARMHOLE (STRAIGHT)" measured shoulder point to underarm (shirt_v2), or is it the armhole depth (demo_v1)?
2. The Book2 chart grades the cap height by only 0.2 cm a size, so the cap ease runs from +1.4 cm at S to −1.0 cm at 3XL (PDS L: +3.9 cm). Should the cap height follow the armhole instead?
