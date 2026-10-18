# Calibration of the pant and shirt drafters

Scope: `src/garments.rs` (drafters), `src/calib.rs` (shape-distance and diagnostics helper).
Run the tables with `cargo test --release --offline -- --nocapture calib_report`.

## Method

* Pant truth: `pds_bin::decode` of `pant_1074664.PDS` (7 pieces x 5 sizes, sew and cut vertex polygons, base-size notches) plus the XML GEOM_INFO. Shirt truth: XML GEOM_INFO only (6 sizes, base L) plus the base-size marker outlines.
* `calib::shape_distance(ours, theirs)`: rigid alignment (8 dihedral seeds, then ICP on 360 resampled points, 80 iterations), then symmetric Hausdorff, mean nearest-point distance, and area/perimeter/bbox deltas. Fold pieces are mirrored to the whole before comparing. Decoded curves are polygons (not tessellated), so differences up to about 0.2 cm are polygon-versus-curve noise.
* No reference coordinate is embedded in the drafter. Only fitted constants and rule tables (grade steps expressed as spec-relative quantities) are used.
* XML areas are rounded to 1 cm2, which is about 0.8% noise on the smallest pieces; residuals below that are not chased.

## What changed in the drafter

1. **Pocket pieces (PKT-IN, FACING, FACING1)** are now graded like Optitex: a rule table (`PKT_RULES`, `FACING_RULES`, `FACING1_RULES`). Unit steps sit at rule points and non-rule vertices interpolate by base-size arc length between rule points. The S->M step equals the L->XL step and the XS->S step is zero for these pieces (verified on the decoded file). This replaced affine scaling. FACING and FACING1 "end" edges and the PKT-IN opening carry a 1.3 cm allowance (waist-type allowance) instead of 1.0.
2. **Pant legs**: `KNEE_DROP` 38.4, `K_THIGH` 1.10, `K_HEM` 1.0 (the separate front hem share was removed).
3. **Seam pairing (#18)**: BACK `outseam_top` is now `PKT-IN opening + 0.3` (about 26 cm) instead of the 16 cm front pocket opening. Evidence: the decoded BACK has a grade rule vertex 26.3 cm below the waist corner, PKT-IN opening is 25.99 cm, and its 1.3 cm allowance equals the waist-line allowance, i.e. the bag opening is sewn to the back side seam from the waist. FRONT `pocket` still pairs with FACING1 `opening`. The side-seam check now compares the whole side seam (FRONT outseam+pocket vs BACK outseam+outseam_top).
4. **Chart versus PDS**: the xlsx chart (`pant_columns`) belongs to a related style. Widths grade identically but PDS rise steps are 1.0/1.3/1.3/1.29 against chart 1.0/1.0/1.3/1.3. `pant_columns_pds()` gives the PDS-implied columns (`front_rise` 29.5..34.39, `back_rise` 40..44.89). Both are tested.
5. **Shirt sleeve**: Optitex cuff corners are folded mitres. The cut line follows the side edge's offset to the hem sew line and mirrors back out. `geom::offset_polygon` can only mitre or bevel, so the corner is replaced by a 0.04 cm stub edge parallel to the bevel carrying the side allowance (`fold_corner_in/out`, only when `sample_sa`). Underarm edges end with a straight segment, which removes a +0.6 cm spike at the concave underarm/cuff corner in the cut outline.
6. **Shirt growth** (calibrated, see "Limits"): `SHIRT_SLEEVE_OPENING_GROWTH` 0.8272, `SHIRT_ARMHOLE_DROP_GROWTH` 0.5438, `SHIRT_SHOULDER_SLOPE_GROWTH` 0.1424, `SHIRT_UNDERARM_HEIGHT_GROWTH` -0.226. A free fit of template exponents drifted to unphysical values (negative collar exponent), so they were left at 1.

## Before / after (XML GEOM_INFO error, percent of XML)

Columns are dX, dY, area, perimeter, sew area, sew perimeter. "Before" is the worst case over sizes of the original code (full per-size baseline was printed by `calib_report` on the original drafter; only worst cases were retained).

| piece | before (worst over sizes) | after (worst over sizes) |
|---|---|---|
| WAIST- BELT | exact | 0.04 |
| DRAWSTRING | exact | 0.00 |
| FRONT (PDS cols) | dX -0.33, area -0.88, per -0.54 (M/L/XL) | area -0.32, per -0.27, sew area -0.28 (XL) |
| FRONT (chart cols) | same as above | dX -0.33, area -0.55, per -0.47 (XL) |
| BACK | <=0.30 | <=0.18 (PDS cols), XL area -0.32 (chart cols) |
| PKT-IN | area -1.32, per -0.80 (XL) | dX -0.36, area <=0.23, per <=0.08 |
| FACING | dX -1.18, dY -0.55, area -1.71, per -0.96, sew area +2.34 | <=0.32 (sew area, M/L) |
| FACING1 | dX -1.2, dY -0.9, area -3.90, per -1.1, sew area -5.06 (XL) | <=0.55 (sew area +0.55 M/L, rounding level) |
| FRT | area -0.8..+2.0 (3XL), sew area to +2.2 | <=0.15 |
| back | area -0.8..+1.5 | <=0.19 (sew area 3XL) |
| back YK | <=0.6 | <=0.60 (sew area 3XL, S -0.50) unchanged |
| CLR | sew area -1.1..+1.4 | sew area -1.07..+1.45 unchanged |
| BND TOP / BND IN | dX +0.25, dY -0.33..-0.72, area <=0.4 | unchanged |
| Sleeve | dY -1.10..+2.09, cut per +2.60/+2.30/+2.12/+2.22/+2.43/+2.64, area to +1.09 | dY -0.46..+1.10, per -0.04..+0.90, area <=0.38 |

### Pant, PDS-implied columns (after)

| piece | XS | S | M | L | XL |
|---|---|---|---|---|---|
| FRONT area / per | +0.09/-0.03 | +0.08/-0.02 | -0.12/-0.14 | -0.15/-0.14 | -0.32/-0.27 |
| BACK area / per | +0.03/-0.03 | +0.01/+0.01 | -0.03/+0.05 | -0.08/+0.08 | -0.14/+0.09 |
| PKT-IN area / per | +0.23/+0.07 | +0.23/+0.07 | +0.13/-0.01 | +0.13/-0.01 | +0.04/-0.08 |
| FACING area / per | -0.16/+0.02 | -0.16/+0.02 | +0.02/+0.02 | +0.02/+0.02 | -0.03/+0.02 |
| FACING1 area / per | +0.09/+0.02 | +0.09/+0.02 | -0.33/+0.02 | -0.33/+0.02 | +0.07/+0.02 |
| FACING1 sew area | -0.31 | -0.31 | +0.55 | +0.55 | -0.13 |

### Pant shape distance versus decoded PDS (cm, PDS columns, worst of cut/sew)

| piece | XS Hd/mNN | S | M | L | XL |
|---|---|---|---|---|---|
| WAIST- BELT | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| FRONT | 0.19/0.08 | 0.13/0.04 | 0.38/0.10 | 0.44/0.16 | 0.75/0.23 |
| BACK | 0.25/0.10 | 0.17/0.05 | 0.41/0.13 | 0.66/0.23 | 0.93/0.34 |
| PKT-IN | 0.20/0.06 | 0.20/0.06 | 0.25/0.07 | 0.25/0.07 | 0.25/0.06 |
| FACING | 0.07/0.02 | 0.07/0.02 | 0.07/0.02 | 0.07/0.02 | 0.07/0.02 |
| FACING1 | 0.01/0.01 | 0.01/0.01 | 0.07/0.04 | 0.07/0.04 | 0.03/0.01 |

### Shirt (after; S M L XL XXL 3XL)

| piece | area % | perimeter % | sew area % |
|---|---|---|---|
| FRT | +.10 +.13 +.13 +.15 +.14 +.15 | +.09 +.07 +.05 +.01 -.03 -.06 | +.10 +.14 +.14 +.15 +.15 +.09 |
| back | +.02 -.01 -.05 -.06 -.11 -.15 | -.05 -.02 0 -.04 -.05 -.05 | +.02 -.02 -.05 -.07 -.13 -.19 |
| back YK | -.38 -.16 +.05 +.15 +.39 +.50 | -.04 0 +.04 +.07 +.13 +.19 | -.50 -.25 -.01 +.17 +.33 +.60 |
| CLR | -.64 -.27 +.08 +.16 +.51 +.84 | -.18 -.10 -.02 +.05 +.11 +.17 | -1.07 -.62 -.18 +.24 +1.06 +1.45 |
| BND TOP/IN | -.29 -.06 -.18 -.27 -.33 -.37 | 0 | -.12 +.10 -.30 -.03 -.32 -.02 |
| Sleeve | +.38 +.16 -.04 +.10 +.15 +.06 | -.04 -.01 +.02 +.34 +.65 +.90 | +.39 +.26 +.02 +.16 +.18 +.11 |

Sleeve dY: -0.46 -0.23 -0.01 +0.35 +0.75 +1.10. BND dY: -0.33..-0.72, dX +0.25..+0.21.

## Limits (plain statements)

* **Hand-drawn curves are not recoverable.** Only the base-size outline of each piece is known (decoded vertices, or marker outlines for the shirt); curves in the PDS are stored as control polygons and other sizes are grade deltas at rule points. Our curve templates reproduce the base size to a mean 0.02-0.1 cm; between rule points we interpolate, so intermediate-size curve shape differs by up to about 0.9 cm Hausdorff (FRONT/BACK XL, concentrated at the crotch curve and the waist/side corner) even where area and perimeter agree to 0.3%.
* **Shirt validation is circular.** There is no graded shirt chart in the tech pack; the size columns are implied from the XML increments, so the shirt growth constants above are calibrations, not measurements. Residual outliers: CLR sew area (+1.45% at 3XL), back YK (0.6%), BND dY (-0.72%), sleeve dY (+1.10%) and sleeve perimeter (+0.9%) at 3XL. All are within the 3% floor but above the 0.5% target. The collar, yoke and band curves have too few independent size samples to fit a growth law without over-fitting.
* **Chart columns for the pants** cannot beat about 0.55% (FRONT XL area) because the chart is a related style whose rise grading differs from the PDS.
* **XML rounding**: areas are rounded to 1 cm2; PKT-IN/FACING/FACING1 residuals of 0.1-0.5% are at that noise level.
* **Offset algorithm**: `geom.rs` was not modifiable, so the folded mitre is emulated with a 0.04 cm stub; the cut outline of a sleeve cuff has that stub as extra vertices.
* **#18 pairing** is inferred from geometry (rule vertex position, opening length, allowance), not from a seam table in the file.

## Regression tests

`geometry_matches_xml_within_documented_error` (limits just above the residuals above, for shirt, pant chart columns and pant PDS columns), `pant_shape_distance_stays_within_calibrated_bounds` (needs the sample PDS; skipped when absent), `shape_distance_is_zero_for_identical_and_transformed`, and the existing garment tests (112 pass).
