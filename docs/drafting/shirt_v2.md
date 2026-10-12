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
| Back | 3.81 cm | 0.22 cm | −0.2 % | 0.3 cm (T147) |
| Yoke | 2.89 cm | 0.06 cm | −0.1 % | 0.2 cm |
| Collar | 1.72 cm | 0.02 cm | +0.0 % | 0.2 cm (T147) |
| Band | 1.91 cm | 0.12 cm | +0.2 % | 0.2 cm (T147) |
| Sleeve cap | 3.14 cm | 0.11 cm | +0.1 % | 0.2 cm |

Front, back, yoke, collar and band areas are held to the spec's 0.5 % target (T147). `tests/test_shirt_v2_draft.py` checks the Book2 chart at every size. No size has a validation error or a flat vertex, and the cap ease against its whole armhole lies between 0 and the client block's L ease (3.948 cm; PDS 3.929).

## Yoke drop (T147, 2026-10-12)

The back yoke seam drops **1.07 cm** from CB to the armhole, as on the client PDS (`back_yoke_drop` = CB_yoke.x − yoke_armhole.x on the PDS sew line, where x runs along the body length; it is y, downward, in the shirt_v2 frame; `domain/data/measurements_1078375_L.json`); the yoke piece's own seam stays flat, as on the PDS. Back gap 0.87 → 0.22 cm, area +0.5 → −0.2 %. The armhole is about 0.95 cm shorter, so the Book2 cap ease moves from +1.4…−1.0 to **+2.3 cm (S) … 0.0 (3XL)**, L +1.9. The generic ±2 cm band no longer applies (owner 2026-10-12; the client's own ease is 3.93 cm at L, shirt.md Q1); the shirt_v2 test now requires 0 ≤ ease ≤ the client block's L ease. The V5 seam check still shows its generic 2 cm band as a WARNING (unchanged).

## Forward shoulder (T147, 2026-10-13)

Owner decision: the chart's neck width is the yoke's, and the front neck sits **0.56 cm** inside it, as on the client PDS (`FRONT_NECK_INSET` = back_neck_width 9.18 − front_neck_width 8.62, `domain/data/measurements_1078375_L.json`). The band, scaled to the front + yoke neckline, now lands on the PDS: collar 0.47 → 0.02 cm (+2.0 → +0.0 %), band 0.45 → 0.12 cm (+2.4 → +0.2 %). Front, back and yoke are unchanged.

Only the neck moves; how the shoulder seam moves with it is still open (Q13). The front shoulder seam is therefore 0.54 cm longer than before. On Book2 L the front/yoke shoulder seams are **17.78 / 16.76 cm** (before: 17.24 / 16.76; PDS: 17.48 / 17.43). The V5 seam check reports "Shoulder seam" as a WARNING; it is not gated.

## Missing Information instead of defaults (T147)

- **Waist level:** shirt_v2 requires `waist_position_hps` (Book2 row 10185). A chart without it gets a Missing Information item; the old 0.62 × body length default is gone.
- **Sleeve variants and pocket:** a confirmed style with a short sleeve or any pocket on shirt_v2 is a blocking `style:sleeve` / `style:pockets` item (`application/style_requirements.py`). No source gives either, so nothing is drafted and nothing can answer it but a source or a style the block drafts.

## Open

- **Shoulder seam method:** Q13 (pattern maker). See above.
- **Cap ease target:** client question Q2 (per fabric; should the cap height follow the armhole). The owner keeps 0 ≤ ease ≤ 3.948 until then.

## Open questions for the pattern maker

1. Is "1/2 ARMHOLE (STRAIGHT)" measured shoulder point to underarm (shirt_v2), or is it the armhole depth (demo_v1)?
2. The Book2 chart grades the cap height by only 0.2 cm a size, so the cap ease runs from +2.3 cm at S to 0.0 at 3XL with the yoke drop (PDS L: +3.9 cm). Should the cap height follow the armhole instead?
