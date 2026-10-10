# Grading: men's regular short-sleeve shirt (1078375)

**Status: AWAITING PATTERN-MAKER SIGN-OFF.** The owner made the decisions recorded below on 2026-10-10. The table drives the T131 graded sizes S–3XL. This file needs the same sign-off as `docs/drafting/shirt.md`.

## Sources
- **No chart:** the client sent no 1078375 measurement chart. The tech pack has none, and the PDS keeps its grade rules in an undocumented binary part that is never read.
- **What the PDS XML gives:** for every piece and size, the cut length and width (bbox), area and perimeter, and the sew area and perimeter. `python scripts/survey_pds_grading.py` prints them with their steps. Examples:
  - FRT length: +1.49 / +1.49 / +1.99 / +1.00 / +1.00 (S→M→L→XL→XXL→3XL)
  - FRT and back width: +1.0 / +1.0 / +1.5 / +1.5 / +1.5
  - back YK length: 0 / 0 / +1.0 / 0 / 0; width: +0.8 / +0.8 / +1.0 / +1.0 / +1.0
  - CLR and BND length: +1.0 per size
  - Sleeve length +0.5 per size; width +2.19 / +2.18 / +3.31 / +3.31 / +3.30
- **Data:** the graded values are in `backend/app/domain/data/measurements_1078375_graded.json`, written by `scripts/derive_shirt_1078375.py`. `test_shirt_grading.py` re-derives them and checks them.

## How each measurement grades (code: `domain/blocks/shirt/grading.py`)
- **Driven:** its step is the step of a PDS piece number, because it sets that piece's extreme on that axis. For example, `front_length` sets the FRT length.
- **Shared:** two measurements set one extreme together, so their sum takes the PDS step.
  - The yoke's `yoke_depth_cb` takes its proportional share, and `back_neck_rise` takes the rest.
  - The sleeve's `cap_height` is trued, and `underarm_height` takes the rest.
- **Follows:** the hem widths move with the chest, and the band's rounded end (`band_top_reach`) moves with the band length, keeping its PDS shape. The Hypothesis fuzzing found that grading it proportionally could squeeze the band end until the cut outline lost allowance.
- **Constant:** the 3.5 cm placket (`front_extension`, `placket_rise`) and the 2 cm turn-up (tech pack).
- **Trued** (`truing.py`): solved so one seam relation keeps its L value in every size. Each relation is solved with a secant in turn, and the round repeats until all hold within 2e-6 cm:
  - side seams equal
  - shoulder FRT = YK
  - yoke seam back = YK
  - band neck edge = half neckline + 0.945
  - collar on band top −1.882
  - cap ease at its L value (3.948; PDS 3.929)
- **Proportional:** the L value scaled by its own piece's PDS growth on its axis. The armhole depths grow with the chest (piece width), not the piece length (owner, 2026-10-10).

## The table (steps from L, cm)
| Measurement | L (cm) | S | M | XL | XXL | 3XL | Rule |
|---|---|---|---|---|---|---|---|
| `front_length` | 74.030 | -2.986 | -1.494 | +1.994 | +2.990 | +3.990 | PDS FRT length |
| `front_neck_width` | 8.620 | -1.526 | -0.752 | +0.396 | +1.088 | +1.767 | trued: band neck edge vs neckline |
| `front_neck_drop` | 6.570 | -0.249 | -0.124 | +0.166 | +0.249 | +0.332 | proportional: FRT length |
| `placket_rise` | 2.210 | 0 | 0 | 0 | 0 | 0 | constant (tech pack construction) |
| `front_extension` | 3.200 | 0 | 0 | 0 | 0 | 0 | constant (tech pack construction) |
| `front_shoulder_drop` | 6.390 | -0.242 | -0.121 | +0.161 | +0.242 | +0.323 | proportional: FRT length |
| `front_shoulder_width` | 16.270 | -0.996 | -0.499 | +0.687 | +1.334 | +1.982 | trued: shoulder seam |
| `front_armhole_depth` | 19.590 | -1.057 | -0.528 | +0.793 | +1.585 | +2.378 | proportional: FRT width |
| `half_chest_front` | 31.360 | -2.000 | -1.000 | +1.500 | +3.000 | +4.500 | PDS FRT width |
| `front_hem_width` | 30.810 | -2.000 | -1.000 | +1.500 | +3.000 | +4.500 | follows half_chest_front |
| `back_length` | 63.490 | -2.998 | -1.499 | +0.999 | +1.998 | +2.997 | PDS back length |
| `back_yoke_drop` | 1.070 | -0.047 | -0.024 | +0.016 | +0.031 | +0.047 | proportional: back length |
| `back_yoke_width` | 24.050 | -1.527 | -0.764 | +1.147 | +2.293 | +3.439 | proportional: back width |
| `back_armhole_depth` | 14.320 | -1.264 | -0.631 | -0.056 | +0.804 | +1.661 | trued: side seams |
| `half_chest_back` | 29.760 | -1.998 | -0.999 | +1.501 | +3.000 | +4.500 | PDS back width |
| `back_hem_width` | 29.200 | -1.998 | -0.999 | +1.501 | +3.000 | +4.500 | follows half_chest_back |
| `yoke_depth_cb` | 12.040 | -0.001 | 0 | +0.618 | +0.618 | +0.618 | proportional: back YK length |
| `back_neck_rise` | 5.230 | 0 | 0 | +0.382 | +0.382 | +0.382 | PDS back YK length, less the step of yoke_depth_cb |
| `back_neck_width` | 9.180 | -0.545 | -0.272 | +0.339 | +0.678 | +1.018 | proportional: back YK width |
| `yoke_shoulder_drop` | 4.710 | 0 | 0 | +0.242 | +0.242 | +0.242 | proportional: back YK length |
| `across_back_half` | 25.960 | -1.602 | -0.801 | +0.997 | +1.994 | +2.991 | PDS back YK width |
| `yoke_seam_width` | 24.000 | -1.528 | -0.764 | +1.147 | +2.293 | +3.439 | trued: yoke seam |
| `collar_width_cb` | 4.790 | -0.095 | -0.048 | +0.049 | +0.097 | +0.146 | proportional: CLR width |
| `collar_length` | 22.700 | -1.998 | -0.999 | +0.999 | +1.999 | +2.998 | PDS CLR length |
| `collar_neck_reach` | 21.380 | -2.007 | -1.003 | +1.003 | +2.007 | +3.010 | trued: collar on band top edge |
| `collar_point_rise` | 3.630 | -0.072 | -0.037 | +0.037 | +0.074 | +0.110 | proportional: CLR width |
| `band_height_cb` | 3.310 | -0.118 | -0.059 | +0.059 | +0.118 | +0.178 | proportional: BND TOP width |
| `band_length` | 24.380 | -2.000 | -1.000 | +1.000 | +2.000 | +3.000 | PDS BND TOP length |
| `band_top_reach` | 23.230 | -2.000 | -1.000 | +1.000 | +2.000 | +3.000 | follows band_length |
| `underarm_height` | 9.990 | -1.554 | -0.794 | +1.056 | +2.173 | +3.421 | PDS Sleeve length, less the step of cap_height |
| `bicep` | 43.860 | -4.369 | -2.183 | +3.308 | +6.615 | +9.919 | PDS Sleeve width |
| `cap_height` | 16.481 | +0.554 | +0.294 | -0.555 | -1.169 | -1.911 | trued: sleeve cap ease |
| `cap_front_width` | 21.929 | -2.013 | -1.006 | +1.524 | +3.047 | +4.569 | proportional: Sleeve width |
| `hem_turnup` | 2.000 | 0 | 0 | 0 | 0 | 0 | constant (tech pack construction) |
| `sleeve_hem_width` | 39.830 | -3.655 | -1.827 | +2.768 | +5.534 | +8.299 | proportional: Sleeve width |

## Checks
- Every seam relation holds its L value in every size, within 1e-5 cm (`test_shirt_grading.py`).
- Cut SUM_AREA against the PDS: S −0.73 %, M −0.35 %, L +0.02 %, XL +0.43 %, XXL +1.04 %, 3XL +1.67 %. The build-plan gate is 3 % (`test_shirt_graded_accuracy.py`).
- The sleeve cap runs through the crown without a kink in every size (`test_shirt_smooth.py`). The PDS cap is one curve, so both cap halves are fitted to the PDS line's direction at the crown notch, and the crown is smoothed when each size is drafted.
- Hypothesis fuzzing (`test_shirt_fuzz.py`) moves the driving PDS steps by up to ±5 % and runs the full pipeline. Seams stay trued, and every outline and cut outline stays valid.

## Decisions and findings (2026-10-10)
1. **Source:** grade from the PDS per-size steps (owner).
2. **Settling the open splits:**
   - The approved first approach was a least-squares fit to each piece's PDS sew perimeter and area. It was tried and dropped: 2 numbers per piece cannot fix about 20 measurements. The steps zig-zagged between sizes, and the implied cap ease ran 2.6 to 13.3 cm.
   - The owner then chose proportional grading plus exact truing.
3. **Cap ease:** held at its L value in every size (owner). The PDS confirms it only at L.
4. **Armhole depth:** grows with the chest (owner). Growing with the piece length put 3XL SUM_AREA at +3.38 %, which fails the 3 % gate.
5. **For the pattern maker to review:**
   - **The cap gets lower in bigger sizes** (−1.91 cm at 3XL). The PDS bicep grows +3.3 cm per size, faster than the armhole, while the ease is held.
   - **`back_armhole_depth` dips at XL.** The PDS front length grows +2.0 at XL but the back only +1.0 (the yoke takes the other +1.0), so the side seams pull the back armhole up at that step.
6. **Sleeve area per size** (owner, 2026-10-10): with the ease held at its L value (3.948; PDS 3.929), the graded Sleeve's cut area runs −1.7 % (S), −0.8 % (M), +1.8 % (XL), +3.6 % (XXL) and +5.4 % (3XL) of the PDS sleeve. The build plan's M4 gate (SUM_AREA per size within 3 %) passes in every size. Per-piece checks are gated at L and reported in the other sizes. Before the crown was made smooth, the Sleeve ran −3.1 % to +9.0 %; letting the ease float instead would keep the sleeve within about 3 %. The pattern maker should choose between these two.
7. **When the client sends the 1078375 chart,** it replaces this table through Missing Information.

## Sign-off
| Reviewer (pattern maker) | Date | Verdict | Notes |
|---|---|---|---|
| | | | |
