# Drafting: men's regular short-sleeve shirt (1078375)

**Status: REVIEWED (2026-10-10).** Every question is answered: Q6 from `reference/`, and the rest by the owner where the reference holds no answer. The `ShirtBlock` (T130) is drafted from this file.

This file lists every point, line and curve of the shirt block. It also gives the measurement each one comes from and the truing checks that become tests. Every number comes from the client's Optitex file `1078375- Men Regular SS Shirt.PDS` (tracked copy `fixtures/reference_patterns/1078375.PDS`, sha256 `3bb708…`), base size **L**. The output of `python scripts/survey_pds_shirt.py` reproduces them. Nothing here is a textbook default. Where the PDS disagrees with the build plan's generic drafting rules, the PDS value is used and the conflict is listed under "Questions for the pattern maker".

## Source and conventions

- **Style:**
  - Optitex 21.4, sizes S M L XL XXL 3XL, base L, SUM_AREA L 1.4262 m².
  - Seven pieces. The PDS gives no grain lines, so the block draws grain parallel to CF/CB along x (Q7). Every piece nests at 180° rotation, and FRT, back YK, CLR and Sleeve are marked "Up/Down".
- **Tech pack `1078375.pdf`:**
  - placket 3.5 cm
  - 2 cm hems on sleeve and body
  - topstitch 0.2 cm on collar and yoke
  - topstitch 0.5 cm on shoulder, armhole, side and placket
  - collar code CL28
  - **No measurement chart.** Every "source measurement" below is read from the PDS L pattern, not from a spec.
- **Geometry:**
  - The **sew line** is in cm with y up, as the PDS marker view places it (piece positions are arbitrary marker positions).
  - Cut lines are the sew line plus the per-edge allowances in `backend/app/domain/data/finishing.json`. The allowances are not repeated here.
- **Drafting order:**
  - The PDS draws its sew rings clockwise; the V6 model drafts counter-clockwise. Points below are listed in **drafting (counter-clockwise) order**, and the PDS handles are swapped to match.
  - Edge ids are `start:end`.
  - Handles are offsets from their own end point (`domain/pattern/segment.CubicBezier`).
  - "Fit" is the largest distance from a PDS sample to the fitted cubic (`domain/geom/bezier_fit.py`).
- **Names:** letters and digits joined by single `_` (`domain/blocks/sketch/naming.py`). CF and CB are centre front and back, HPS is the high point shoulder, SP the shoulder point, and UA the underarm.

## Pieces

### FRT (front) — cut 2 (mirrored pair), not on fold
| Point | PDS L (x, y) | Defined by |
|---|---|---|
| `FE_top` | (74.54, −36.39) | top of the front edge (placket edge) |
| `CF_top` | (74.54, −33.19) | CF line at the height of `FE_top` |
| `CF_neck` | (72.33, −33.19) | neckline meets CF |
| `HPS` | (78.90, −24.57) | neckline meets shoulder |
| `SP` | (72.51, −8.30) | shoulder meets armhole |
| `UA` | (52.92, −1.83) | armhole meets side seam |
| `side_hem` | (6.12, −2.38) | side seam meets hem |
| `FE_hem` | (4.87, −36.38) | hem meets front edge |

| Edge | Kind | PDS length | Handles (start / end) | Fit | Allowance role |
|---|---|---|---|---|---|
| `FE_top:CF_top` | line | 3.200 | — | — | placket top: **1.0** cm, PDS measured (Q3) |
| `CF_top:CF_neck` | line | 2.210 | — | — | placket CF step: **0.0** cm, the cut line is on the sew line, PDS measured (Q3) |
| `CF_neck:HPS` | cubic | 12.016 | (−0.226, +4.828) / (−5.191, −1.640) | 0.006 | neckline |
| `HPS:SP` | line | 17.480 | — | — | shoulder |
| `SP:UA` | cubic | 23.670 | (−18.733, −3.821) / (+0.373, −2.638) | 0.018 | armhole_body |
| `UA:side_hem` | cubic | 46.804 | (−15.597, −0.361) / (+15.601, +0.091) | 0.000 | side_seam_front |
| `side_hem:FE_hem` | cubic | 34.041 | (−1.084, −13.019) / (−0.222, +13.997) | 0.002 | hem |
| `FE_hem:FE_top` | line | 69.670 | — | — | front_edge |

There are no notches on FRT in the PDS.

### back — cut 1 on fold
| Point | PDS L (x, y) | Defined by |
|---|---|---|
| `CB_yoke` | (68.01, −80.66) | CB fold meets yoke seam |
| `yoke_armhole` | (66.94, −56.61) | yoke seam meets armhole |
| `UA` | (52.62, −50.90) | armhole meets side seam |
| `side_hem` | (5.82, −51.46) | side seam meets hem |
| `CB_hem` | (4.52, −80.66) | hem meets CB fold |

| Edge | Kind | PDS length | Handles (start / end) | Fit | Allowance role |
|---|---|---|---|---|---|
| `CB_yoke:yoke_armhole` | cubic | 24.081 | (−0.021, +9.592) / (+0.696, −9.195) | 0.000 | yoke_seam |
| `yoke_armhole:UA` | cubic | 16.858 | (−5.844, +0.068) / (+1.427, −6.223) | 0.009 | armhole_body |
| `UA:side_hem` | cubic | 46.804 | (−15.597, −0.390) / (+15.600, +0.107) | 0.000 | side_seam_back |
| `side_hem:CB_hem` | cubic | 29.240 | (−0.936, −11.693) / (−0.054, +11.564) | 0.000 | hem |
| `CB_hem:CB_yoke` | line, **fold** | 63.490 | — | — | none (fold) |

### back YK (yoke) — cut 2 on fold (outer + inner)
| Point | PDS L (x, y) | Defined by |
|---|---|---|
| `CB_neck` | (85.08, −80.66) | CB fold meets neckline |
| `HPS` | (90.31, −71.48) | neckline meets shoulder |
| `SP` | (85.60, −54.70) | shoulder meets armhole |
| `yoke_armhole` | (73.03, −56.66) | armhole meets yoke seam |
| `CB_yoke` | (73.04, −80.66) | yoke seam meets CB fold |

| Edge | Kind | PDS length | Handles (start / end) | Fit | Allowance role |
|---|---|---|---|---|---|
| `CB_neck:HPS` | cubic | 11.847 | (+0.127, +6.092) / (−5.093, −1.596) | 0.004 | neckline |
| `HPS:SP` | line | 17.428 | — | — | shoulder |
| `SP:yoke_armhole` | cubic | 12.751 | (+1.402, −0.424) / (+1.826, −0.067) | 0.000 (5 samples only) | armhole_body |
| `yoke_armhole:CB_yoke` | line | 24.000 | — | — | yoke_seam |
| `CB_yoke:CB_neck` | line, **fold** | 12.040 | — | — | none (fold) |

Notch `shoulder_notch` on `HPS:SP` sits 1.475 cm from `HPS` (t = 0.08463). It is a 0.696 cm slit from the sew line.

### CLR (collar) — cut 2 on fold
| Point | PDS L (x, y) | Defined by |
|---|---|---|
| `CB_collar_neck` | (126.20, −72.99) | CB fold, edge sewn to the band |
| `collar_neck_end` | (147.58, −75.22) | front end of the band edge |
| `collar_point` | (148.90, −69.36) | collar point |
| `CB_collar_outer` | (126.20, −68.20) | CB fold, outer (fall) edge |

| Edge | Kind | PDS length | Handles (start / end) | Fit | Allowance role |
|---|---|---|---|---|---|
| `CB_collar_neck:collar_neck_end` | cubic | 21.546 | (+8.539, −0.017) / (−8.846, +1.844) | 0.005 | collar |
| `collar_neck_end:collar_point` | line | 6.007 | — | — | collar |
| `collar_point:CB_collar_outer` | cubic | 22.742 | (−4.504, +0.428) / (+11.843, +0.048) | 0.000 | collar |
| `CB_collar_outer:CB_collar_neck` | line, **fold** | 4.790 | — | — | none (fold) |

### BND TOP and BND IN (collar band) — each cut 1 on fold
The two pieces have the same shape: every length is within 0.01 cm, and the survey prints both. The 24.81 edge is sewn to the neckline, and the collar's 21.55 edge sits on the 23.43 edge (Q2).

| Point | BND TOP PDS L (x, y) | Defined by |
|---|---|---|
| `CB_band_top` | (127.11, −96.71) | CB fold, top edge (collar side) |
| `band_top_end` | (150.34, −99.03) | top edge meets the rounded band end |
| `band_neck_end` | (151.49, −96.88) | rounded band end meets the neck edge |
| `CB_band_neck` | (127.11, −93.40) | CB fold, neck edge |

| Edge | Kind | PDS length (TOP / IN) | Handles (start / end), TOP | Fit | Allowance role |
|---|---|---|---|---|---|
| `CB_band_top:band_top_end` | cubic | 23.428 / 23.438 | (+16.176, +0.211) / (−0.581, −0.929) | 0.006 | collar_band |
| `band_top_end:band_neck_end` | cubic | 2.502 / 2.502 | (+0.776, +0.458) / (−0.168, −0.804) | 0.000 | collar_band |
| `band_neck_end:CB_band_neck` | cubic | 24.808 / 24.818 | (−7.673, +3.037) / (+11.508, −0.019) | 0.003 | collar_band |
| `CB_band_neck:CB_band_top` | line, **fold** | 3.310 / 3.310 | — | — | none (fold) |

### Sleeve — cut 2 (mirrored pair)
The PDS does not mark which half of the sleeve is the front. The owner decided (Q5) that the side with the narrow felled underarm (0.8) is the front.

| Point | PDS L (x, y) | Defined by |
|---|---|---|
| `hem_fold_back` | (117.20, −43.70) | underarm seam meets the hem fold line |
| `UA_back` | (125.19, −46.37) | underarm meets cap |
| `cap_crown` | (141.67, −24.44) | crown, at the PDS crown notch |
| `UA_front` | (125.19, −2.51) | cap meets underarm |
| `hem_fold_front` | (117.20, −5.19) | underarm seam meets the hem fold line |
| `hem_front` | (115.20, −4.53) | hem turn-up edge |
| `hem_back` | (115.20, −44.36) | hem turn-up edge |

| Edge | Kind | PDS length | Handles (start / end) | Fit | Allowance role |
|---|---|---|---|---|---|
| `hem_fold_back:UA_back` | cubic | 8.430 | (+2.705, −0.754) / (−2.588, +1.100) | 0.000 | underarm_wide |
| `UA_back:cap_crown` | cubic | 28.449 | (+3.541, +10.218) / (−0.650, −12.896) | 0.036 | sleeve_cap |
| `cap_crown:UA_front` | cubic | 28.759 | (+0.235, +13.735) / (+3.362, −9.953) | 0.038 | sleeve_cap |
| `UA_front:hem_fold_front` | cubic | 8.433 | (−2.586, −1.108) / (+2.705, +0.756) | 0.000 | underarm_narrow |
| `hem_fold_front:hem_front` | line | 2.106 | — | — | (turn-up corner) |
| `hem_front:hem_back` | line | 39.830 | — | — | sleeve_hem |
| `hem_back:hem_fold_back` | line | 2.106 | — | — | (turn-up corner) |

A single cubic cannot follow the cap: it misses by 1.591 cm. Split at the crown notch, each half fits within 0.04 cm, so `cap_crown` is a named point. Notch `crown_notch` sits on the cap 28.759 cm from `UA_front` and 28.449 cm from `UA_back`, 0.019 cm off the sampled sew line.

The 2.0 cm between `hem_*` (x 115.20) and `hem_fold_*` (x 117.20) matches the tech pack's 2 cm sleeve hem. The PDS draws the turn-up inside the sew line, with mitred corners that mirror the underarm seam.

## Source measurements (PDS L sew line; no client chart exists)
Every value here is **PDS-derived**. When the client sends the 1078375 measurement chart, it replaces these through Missing Information. Until then, they are the block's inputs for size L. Lengths run along x (the PDS marker's length direction) and widths along y.

| Measurement | Value (cm) | From |
|---|---|---|
| Front length, HPS to hem at front edge | 74.03 | x(`HPS`) − x(`FE_hem`) |
| Front length, HPS to side hem | 72.78 | x(`HPS`) − x(`side_hem`) |
| CB length, neck to hem | 75.53 | back fold 63.49 + yoke fold 12.04 |
| Yoke depth at CB | 12.04 | yoke fold |
| Half chest at underarm, front (CF to UA) | 31.36 | y(`UA`) − y(`CF_neck`) |
| Half chest at underarm, back (CB to UA) | 29.76 | y(`UA`) − y(CB fold) |
| Chest circumference at sew line | 122.24 | 2 × (31.36 + 29.76) |
| Front hem width, CF to side | 30.81 | y(`side_hem`) − y(CF) |
| Back hem width, CB to side | 29.20 | y(`side_hem`) − y(CB) |
| Front edge extension beyond CF | 3.20 | `FE_top:CF_top` |
| Front armhole depth, SP to UA | 19.59 | x(`SP`) − x(`UA`) |
| Front shoulder length | 17.480 | `HPS:SP` |
| Back (yoke) shoulder length | 17.428 | `HPS:SP` on YK |
| Across back at shoulder, SP to SP | 51.92 | 2 × (y(`SP`) − y(CB)) on YK |
| Front neck width / drop | 8.62 / 6.57 | `HPS` to `CF_neck` |
| Back neck width / drop | 9.18 / 5.23 | `HPS` to `CB_neck` on YK |
| Sleeve length, crown to turn-up edge | 26.47 | x(`cap_crown`) − x(`hem_*`) (the cap's highest x is 141.70: 26.50) |
| Sleeve length, crown to hem fold | 24.47 | x(`cap_crown`) − x(`hem_fold_*`) |
| Sleeve cap height | 16.48 | x(`cap_crown`) − x(`UA_*`) |
| Bicep (UA to UA) | 43.86 | `UA_back` to `UA_front` |
| Sleeve width at hem fold / turn-up edge | 38.51 / 39.83 | `hem_fold_*`, `hem_*` |
| Collar width at CB | 4.79 | CLR fold |
| Band height at CB | 3.31 | BND fold |

## Truing checks (become accuracy-suite tests in T130, in every size)
| # | Check | PDS L | Result vs build-plan rule |
|---|---|---|---|
| T1 | Front side seam = back side seam | 46.804 = 46.804 | equal |
| T2 | FRT shoulder = YK shoulder | 17.480 vs 17.428 (0.052) | within 0.1 |
| T3 | Back yoke seam = YK yoke seam | 24.081 vs 24.000 (0.081) | within 0.1 |
| T4 | Sleeve cap − body armhole (ease) | 57.208 − (23.670 + 16.858 + 12.751 = 53.279) = **3.929** | expected 3.929 at L, as in the PDS; the build plan's 0–1 cm rule does not apply (Q1) |
| T5 | Cap halves at crown vs front / back armhole | 28.449 and 28.759 vs 23.670 and 29.609 | crown notch stays where the PDS puts it, as a cap-centre notch and not at the shoulder seam (Q5) |
| T6 | Band neck edge vs half neckline (FRT 12.016 + YK 11.847 = 23.863) | neck edge 24.808 = half neckline + 0.945 | expected +0.945 at L (Q2) |
| T7 | Collar neck edge vs band top edge | 21.546 on 23.428 (1.882 short) | expected −1.882 at L (Q2) |
| T8 | Every outline closed, counter-clockwise, no self-intersection, no zero-length edge | — | build-plan geometry rule |
| T9 | Each curve within the fit tolerance of the PDS | largest fit 0.038 (cap) | within 0.1 (Q4) |
| T10 | Piece bbox and area vs PDS per size | e.g. FRT L 78.888 × 37.0748, 0.2588 m² | build plan: 1.5 cm / 3 %; PDS outline test: 0.1 cm / 0.5 % |
| T11 | Sum of piece areas × quantity = SUM_AREA per size | L 1.4262 m² | grading (T131) |
| T12 | Notches | exactly the two PDS notches: YK `shoulder_notch` and sleeve `crown_notch` | no others are added (Q6) |

## Block implementation (T130)
- **Recipes:** `backend/app/domain/blocks/shirt/` drafts each piece from a recipe (`body.py`, `parts.py`). A recipe lists the named points above in drafting order, and each point is a linear formula of named measurements. The 35 measurement definitions are in `measures.py` (for example `front_length` = x(`HPS`) − x(`FE_hem`) on FRT).
- **Data:** the values (`domain/data/measurements_1078375_L.json`) and the shape constants (`shirt_1078375_shape.json`) are written from the PDS by `scripts/derive_shirt_1078375.py`. The shape constants are each point's leftover offset, each curve's handles as chord fractions, and the notch parameters. `test_shirt_reference_data.py` fails if either file drifts from the PDS.
- **Curve fits:** the yoke armhole (`SP:yoke_armhole`) has only 5 PDS samples. The free fit loops there, so it uses the tangent-constrained fit, which is 0.053 cm off, within the 0.1 tolerance (Q4).
- **Smooth crown (T131):** the PDS cap is one curve; the crown notch only marks a point on it. So both cap halves are fitted with the PDS line's direction at the crown (0.037 and 0.095 cm off), and the crown is smoothed when drafting, so it has no kink in any size. The drafted L cap ease is 3.948 (PDS 3.929).
- **Collar rule:** the build plan's "collar sew line = neckline within 0.3 cm" does not hold for this client pattern (Q2: the band neck edge is the half neckline + 0.945). The accuracy suite checks the PDS value instead.
- **Accuracy suite** (`application/accuracy/`, test `test_shirt_accuracy.py`, run on every commit) at L:
  - every piece's cut length, width and area against the PDS (1.5 cm and 3 %; actual differences are at most 0.2 cm and about 0.1 %)
  - all 37 sew edges within 0.1 (actual at most 0.046)
  - the side, shoulder and yoke seams
  - cap ease 3.948 (PDS 3.930)
  - band and collar against the PDS
  - valid outlines, the two notches, and grain along x

## Questions for the pattern maker
Answered on 2026-10-10. The source is named for each answer.
1. **Sleeve cap ease 3.93 cm.** **Answer (owner):** keep the PDS ease of 3.93 cm; the build plan's 0–1 cm rule does not apply.
2. **Collar band edges.** **Answer (owner):** the 24.81 edge is the neck edge (neckline + 0.95). The collar's 21.55 edge sits on the 23.43 top edge.
3. **FRT step at CF neck.** **Answer (owner):** the top of the grown-on 3.5 cm placket. **Allowances, measured from the PDS** (`edges.edge_allowances` on FRT): 1.0 cm on `FE_top:CF_top`, and 0.0 cm on `CF_top:CF_neck`, where the cut line lies on the sew line. The roles `placket_top` and `placket_cf_step` are added to `finishing.json`, with evidence, in T130.
4. **Curve-fit tolerance.** **Answer (owner):** 0.1 cm.
5. **Sleeve front and back.** `reference/` does not say (PDS, and tech pack pp. 1–6, checked). **Answer (owner):** the narrow-underarm side (0.8, cap half 28.759) is the front, and its points are named `*_front`. The crown notch stays exactly where the PDS puts it (a cap-centre notch, 28.759 / 28.449). It is not moved to match `SP`.
6. **Notches.** **Settled from `reference/`:** the PDS has exactly two notches (YK shoulder, 1.475 cm from HPS, and the sleeve crown). The block reproduces those and adds none.
7. **Grain lines.** The PDS has none, and tech pack pp. 1–6 give none. **Answer (owner):** draw grain parallel to CF/CB, along x (the fabric length).
8. **Allowance role names** from T128 (`finishing.json`). The values are measured from the PDS. **Answer (owner):** all 14 shirt roles and values are confirmed as they stand, and their status in `finishing.json` is now `confirmed`.

## Review sign-off
| Reviewer (pattern maker) | Date | Verdict (approved / changes) | Notes |
|---|---|---|---|
| Owner (on the pattern maker's behalf for Q1–Q4) | 2026-10-10 | partial: Q1–Q4 answered | Q6 from reference; Q5, Q7, Q8 open |
| Owner (Q5, Q7, Q8) | 2026-10-10 | **approved** | sleeve front = narrow-underarm side, crown notch as PDS; grain along CF/CB; finishing.json shirt roles confirmed |
