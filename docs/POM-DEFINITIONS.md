# POM definitions (src/pom.rs)

Every POM is measured on the **sew line** of the drafted `Pattern` (centimetres, y-up), with one
fixed definition. `pom::pant_defs()` / `pom::shirt_defs()` carry the same text in `PomDef.definition`.

What is guaranteed: the fitted pattern reproduces the spec numbers **by these definitions**.
What is not: that Optitex's Measure tool, on an exported file, returns the same number. See
"CONFIRM IN OPTITEX" at the end.

Vocabulary: FRONT/BACK are pattern pieces. "horiz width at y" = (max x - min x) where a horizontal
line at height y crosses the piece's sew outline. "crotch point" = start node of the piece's
`crotch` edge (inseam meets crotch seam). "top edge" = highest node of the piece.
Kinds: Width, Length, CurvedLength (arc length along a seam), Position, PassThrough.

## Pants (17 POMs)

| Code | Key | Kind | Definition |
|---|---|---|---|
| 20125 | half_waist | PassThrough (input) | Relaxed elastic waist. The flat top edge is cut to the STRETCHED size, so the relaxed value is set by the elastic, not the flat geometry. Reported = spec value. |
| 20245 | half_waist_stretched | PassThrough (input) | Elastic stretched minimum; drives belt length (belt top edge - 2.5 overlap). Reported = spec value. |
| 20305-A | hip_pos_side | Position (input) | Locator only, below the top edge at the side seam. Reported = spec value. |
| 20305-B | hip_pos_cf | Position (input) | Locator only, below the top edge at CF. Reported = spec value. |
| 20305 | half_seat | Width | horiz width of FRONT at (front top - 16 cm) + horiz width of BACK at (back top - 17 cm) |
| 20865 | thigh | Width | (FRONT horiz width 1 cm below its crotch point + BACK same) / 2 |
| 21505 | front_rise | CurvedLength | arc length of FRONT `crotch` curve + waistband width |
| 21545 | back_rise | CurvedLength | arc length of BACK `crotch` curve + waistband width |
| 20905 | knee | Width | (FRONT horiz width 30.48 cm (12") below crotch point + BACK same) / 2 |
| 21125 | leg_opening | Width | (FRONT `hem` edge length + BACK `hem` edge length) / 2 (hem edges are straight) |
| 30210 | hem_height | Length (Cut) | hem fold allowance on the `hem` edge (cut line - sew line) = `opts.pant_hem` |
| 21885 | inseam | CurvedLength | (FRONT `inseam` arc + BACK `inseam` arc) / 2 |
| 20265 | waistband_width | Width | half the belt piece height (the belt is drawn folded, 2x finished width) |
| 22145 | pocket_opening_waist | Width | FRONT pocket mouth horizontal run (outseam corner x - waist corner x) - 2.04 (sample calibration) |
| 22165 | pocket_opening_length | Length | FRONT pocket mouth vertical drop (waist corner y - outseam corner y) |
| 22565 | pocket_bag_depth | Length | y extent of the `PKT-IN` piece |
| 30845 | drawcord_length | PassThrough (input) | cut-only trim, (DRAWSTRING length - 105) / 2. Reported = spec value. |

Why the ½ waist is an input: the flat FRONT+BACK top edge (arc, not straight; sum of the two
`waist` edges, about 45.7 cm for size S) is the stretched circumference and is not the 35.0
relaxed chart value. Driving it would be wrong, so both waists are inputs.

Sketch (FRONT, CF side right of the crotch curve):
```
  top edge  ______a3___          ^
           |       \  \ pocket   |  rise (curved, along crotch edge)
  crotch   (        \  a4        |
  curve     \        |           |
             \______ | outseam   v
   crotch pt  *------+ <- thigh = horiz width 1 cm below *
   inseam     |      |   knee   = horiz width 30.48 cm below *
              |______|   leg opening = hem edge
```

## Shirts (13 POMs, keyed to ShirtSpec fields)

| Code/key | Kind | Definition |
|---|---|---|
| half_chest | Width | FRT (CF to side) + back (CB to side) horizontal widths at the underarm line (end node of FRT `side` edge); the grown-on placket is excluded |
| half_hem | Width | FRT `hem` length (minus placket extension) + back `hem` length |
| across_shoulder | Width | 2 x largest x of the yoke |
| body_length_hps | Length | FRT highest node (HPS) to lowest node (CF hem corner) |
| back_length_cb | Length | back piece height + yoke `cb` length |
| yoke_depth | Length | yoke `cb` edge length |
| armhole | CurvedLength (informational, input_only) | FRT + back + yoke `armhole` arcs. No spec target (the spec drives `armhole_drop`), so it is reported, never driven |
| sleeve_length | Length | sleeve piece height (cap crest to hem) |
| bicep | Width | half the sleeve horizontal width at the `underarm_r` node height |
| sleeve_opening | Width | half the sleeve `hem` edge |
| neck_size | CurvedLength | 2 x (BND IN `neck_front` + `neck_back`) |
| stand_height | Length | BND IN `cb` edge length |
| collar_point_length | Length | CLR `point` edge length |

## CONFIRM IN OPTITEX

Pick one size (e.g. M), export the fitted pattern, and compare each line below with Optitex's
Measure tool. If a number differs, only the listed alternative needs to change in `pom.rs`.

1. **Width, horizontal vs perpendicular** (20305, 20865, 20905). Encoded: horizontal (parallel to x
   at the stated height). Alternative: perpendicular to the grain/side seam. Matters when the leg
   edges lean; difference grows with the leg's taper angle.
2. **Knee reference** (20905). Encoded: 30.48 cm (12") below the crotch point, as the chart label
   says. Alternatives: 12" up from the hem; half the inseam below the crotch.
3. **Rise, curved vs straight** (21505/21545). Encoded: curved arc length of the crotch seam +
   waistband width (chart says CURVED). Alternatives: straight crotch point to top edge; arc
   without adding the waistband (the drafter's crotch edge stops at the waist seam).
4. **Seat line** (20305). Encoded: a fixed 16 cm (CF) / 17 cm (side) below the top edge of each
   piece (the base-size hip positions), NOT the per-size hip_pos values, so the measurement is a
   function of the pattern alone. Alternative: use each size's hip positions (20305-A/B) or the widest
   point. Seat is also half the circumference only if FRONT+BACK are measured at one horizontal line.
5. **Thigh** (20865). Encoded: average of FRONT and BACK horizontal widths. Alternative: FRONT+BACK sum.
   Note the chart value (33) is a half measure like the others.
6. **Inseam** (21885). Encoded: average of the two inseam arcs; alternatives: back only / front only.
7. **Leg opening** (21125). Encoded: average of hem edge lengths (straight). Alternative: sum / 2 of
   the sew widths excluding hem allowance.
8. **Pocket opening along WB** (22145). Encoded with a -2.04 cm calibration so the sample's 5.04 cm
   drafted run equals the chart's 3.0. Alternative: raw horizontal run, or run along the waist edge
   measured from the waistband seam. This is the least certain definition.
9. **Waist** (20125/20245). Passed through. Verify the flat top edge against the stretched value.
10. **Shirt chest / hem**: front measured from CF (placket excluded). Alternative: include placket.
11. **Neck size**: 2x half stand length along the neck seam. Alternative: measured at the button
    centre line (adds the overlap).
