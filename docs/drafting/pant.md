# Drafting: women's high-rise wide-leg pant (CL1086464, block 1074664)

**Status: DRAFT — AWAITING OWNER / PATTERN-MAKER REVIEW (written 2026-10-12, T133a).** No `PantBlock` code is written until this file is reviewed (MASTER T133). Every number below is read from the client files; where a number is a *reading* of the geometry (which edge is which, how a POM is taken), it is marked **to confirm** and listed under "Questions".

Numbers come from `python scripts/survey_pds.py --style 1074664` (the sew line of every piece at the base size), from `infrastructure/pds/edges.edge_allowances` (cut-to-sew width per edge), and from the measurements in "Chart POMs on the PDS" (method stated per row).

## Sources
- **Optitex pattern** `1074664 - CROSS PKT PANT.PDS` (tracked copy `fixtures/reference_patterns/1074664.PDS`): Optitex 21.4, internal NAME "1079077- CROSS PKT PANT", sizes XS S M L XL, **base S**, SUM_AREA S 1.8339 m². Seven pieces. Every piece: NESTING ROTATION 180° only, Shrink 1.00, 1.00. FRONT, BACK, PKT-IN, FACING, FACING1 are "Up/Down". MATERIAL "A" on WAIST- BELT, FRONT, BACK, PKT-IN; empty on the others. No grain lines, no drill holes, no text in the PDS.
- **Measurement chart** `CL1086464 pant folder summer.xlsx`, sheet " graded spec sheet ": 17 POMs, XS–XXL, base S, cm, half ("½") measurements flat; tolerances in column L ("1/2 body yarıda/tolerance"). The chart has **no measurement diagram** (its images are the Colin's logo only).
- **Tech pack** `CL1086464.pdf` (7 pages): high rise / wide leg; waistband with inside elastic, drawcord through embroidery holes, gathering; **0.7 cm binding on all seams inside the waistband tunnel**, single needle; pockets "same as sample"; bartacks; hem single needle; pocket bag "other fabric 1" cotton/polyester. Main fabric (visible page 5): **100 % linen, piece dyed, 14×14 54×54, −5 % warp and weft, 150 GSM**, enzyme wash, for both colourways (Khaki, Dark Plum). The linen-viscose text in the PDF lies off the page and is not part of the spec.
- **Original style** CL 1079432 (workbook sheet "orj. photo": flat sketch and photos worn front, side, back): the predecessor this style is based on.

## Conventions
- Sew line, cm, y up, as the PDS marker view places the pieces (positions are arbitrary).
- Each piece lies with its length along **x**: the hem is at small x, the waist at large x. Grain is therefore along x, as for the shirt (Q4; the PDS lets every piece rotate 180° only).
- Edges are listed in the PDS ring order; the V6 block will draft them counter-clockwise (reversed), as `docs/drafting/shirt.md` does. Edge ids will be `start:end`.
- Point names below are **proposals** (to confirm in review); they follow `domain/blocks/sketch/naming.py`.
- Cut line = sew line + per-edge allowance. The allowances are the `finishing.json` pant roles, measured from this PDS and **still inferred** (`needs_pattern_maker_review`, Q5).

## Pieces (base size S)

### FRONT — cut 2 (mirrored pair), not on fold, material A
| Proposed point | PDS S (x, y) | Reading |
|---|---|---|
| `hem_crease` | (7.52, −66.54) | vertex splitting the hem into two lines (to confirm: crease/grain point) |
| `hem_inseam` | (7.51, −52.54) | hem meets inseam |
| `crotch` | (88.45, −51.60) | inseam meets front rise |
| `CF_waist` | (112.90, −55.92) | front rise meets waist |
| `side_waist` | (113.51, −76.42) | waist meets outseam |
| `hem_side` | (7.53, −80.55) | outseam meets hem |

| Edge | Kind | Sew length | Allowance (role) |
|---|---|---|---|
| `hem_crease → hem_inseam` | line | 14.000 | 1.5 (hem) |
| `hem_inseam → crotch` (inseam) | cubic, fit 0.000 | 80.954 | 1.0 (body_seam) |
| `crotch → CF_waist` (front rise) | cubic, fit 0.029 | 25.807 | 1.0 (body_seam) |
| `CF_waist → side_waist` (waist) | cubic, fit 0.000 | 20.511 | 1.3 (waist_edge) |
| `side_waist → hem_side` (outseam) | cubic, fit 0.024 | 106.802 | 1.0 (body_seam) |
| `hem_side → hem_crease` | line | 14.010 | 1.5 (hem) |

No notches. The FRONT sew line has **no diagonal pocket corner**: its outseam is one smooth curve from waist to hem (to confirm how the cross pocket is built, Q-P1).

### BACK — cut 2 (mirrored pair), not on fold, material A
| Proposed point | PDS S (x, y) | Reading |
|---|---|---|
| `hem_side` | (7.45, −39.17) | outseam meets hem |
| `hem_inseam` | (7.46, −6.07) | hem meets inseam |
| `crotch` | (88.07, −2.14) | inseam meets back rise |
| `CB_waist` | (117.45, −16.00) | back rise meets waist |
| `side_waist` | (113.75, −40.96) | waist meets outseam |

| Edge | Kind | Sew length | Allowance (role) |
|---|---|---|---|
| `hem_side → hem_inseam` | line | 33.100 | 1.5 (hem) |
| `hem_inseam → crotch` (inseam) | cubic, fit 0.093 (two cubics 0.140/0.000, split at (63.92, −5.42)) | 80.857 | 1.0 (body_seam) |
| `crotch → CB_waist` (back rise) | cubic, fit 0.021 | 36.133 | 1.0 (body_seam) |
| `CB_waist → side_waist` (waist) | line | 25.233 | 1.3 (waist_edge) |
| `side_waist → hem_side` (outseam) | cubic, fit 0.002 | 106.329 | 1.0 (body_seam) |

No notches. The back hem is one line; the front hem has a vertex (Q-P2).

### WAIST- BELT — cut 1 on fold, material A
A rectangle: sew 51.500 × 10.400 (cut 52.8 × 13.0); the fold is a short end (x = 63.10). Allowance 1.3 on three sides, 0 on the fold. **10.400 = 2 × 5.2**, the chart's waistband width (POM 20265), so the belt is folded lengthwise to 5.2 finished.

### PKT-IN — cut 2, material A
Four edges: 21.717 (cubic, shared exactly with FACING), 34.145 (cubic; one cubic misses by 0.470, two by 0.041/0.048), 22.202 (cubic), 25.991 (cubic, allowance 1.3 = waist_edge); the others 1.0. Two notches (0.70 cm slits; PDS T-notch, cut length 1.2 each): on the waist edge **4.750 cm** from its corner with the 21.717 edge, and on the 21.717 edge **6.201 cm** from its far end.

### FACING — cut 2
Four edges: 23.374 (line), 8.755 (cubic, allowance 1.3 = waist_edge), 21.717 (cubic, **the same curve as PKT-IN's**), 4.388 (cubic). Two notches: on the waist edge **4.740 cm** from its corner with the 21.717 edge, and on the 21.717 edge **6.212 cm** from its far end. These are PKT-IN's two notches at the same distances (within 0.011): **a notch pair**, so FACING is sewn onto PKT-IN along that edge and the waist (to confirm).

### FACING1 — cut 2
A strip: 22.528 (line), 3.114 (line, allowance 1.3), 22.219 (cubic), 0.950 (line); other allowances 1.0. No notches. Where it is sewn is not drawn in the PDS (Q-P1).

### DRAWSTRING — cut 1
165.0 × 4.0, cut line only (no sew line), the same in every size.

## Chart POMs on the PDS (size S)
Measured on the sew line. "Value" is the PDS measurement; "Chart" is CL1086464 S; "Chart / 0.95" is what the PDS would show if −5 % shrinkage were built into it (Q11).

| POM | Chart S (tol) | Method on the PDS | PDS value | Chart / 0.95 |
|---|---|---|---|---|
| 21885 inseam (along seam) | 78 (0.5) | FRONT inseam 80.954 − hem height 2.8 (POM 30210), *if the sew line at the hem is the raw turn-up edge* (to confirm) | **78.154** (BACK: 78.057) | 82.11 |
| 21505 front rise to top edge | 30.5 (0.5) | FRONT rise 25.807 + waistband 5.2 | **31.007** | 32.11 |
| 21545 back rise to top edge | 41 (0.5) | BACK rise 36.133 + waistband 5.2 | **41.333** | 43.16 |
| 20265 waistband width | 5.2 (0) | belt sew height 10.400 / 2 | **5.200** | 5.47 |
| 21125 ½ leg opening | 30 (0) | (FRONT + BACK width) / 2, square to x, 2.8 above the hem sew edge | **30.497** | 31.58 |
| 20865 thigh, 1 cm below crotch | 33 (0.5) | (FRONT + BACK width) / 2 at crotch x − 1 | **33.600** | 34.74 |
| 20905 knee, 12" below crotch | 30 (0.5) | (FRONT + BACK width) / 2 at crotch x − 30.48 | **30.871** | 31.58 |
| 20305 ½ seat | 52 (1) | FRONT + BACK width at side-waist x − 17 (POM 20305-A) | **53.056** | 54.74 |
| 20125 / 20245 ½ waist relaxed / stretched | 35 / 49 (1) | body half waist FRONT 20.511 + BACK 25.233 = 45.744; half belt 51.500 (elastic gathers both) | not directly measurable | — |
| 22145 / 22165 pocket opening along WB / down outseam | 3 / 15.5 (0) | the opening is not drawn on FRONT (Q-P1) | — | — |
| 22565 pocket bag depth | 24 (0) | depends on how PKT-IN is placed (Q-P1) | — | — |
| 30845 ½ drawcord (fold to end) | 30 (0) | DRAWSTRING 165 is the whole cord; the hanging half is not drawn | — | — |

Reading: every comparable value is close to the chart as it is and far from chart / 0.95, which supports "the PDS is **not** shrink-compensated" (Q11). Inseam, back rise and waistband are within tolerance; front rise (+0.507 vs 0.5), thigh (+0.6 vs 0.5), knee (+0.871 vs 0.5), leg opening (+0.497 vs 0) and seat (+1.056 vs 1) are just outside **under these methods**, which are themselves to confirm (Q-P3).

## Grading facts from the PDS (XS→S→M→L→XL steps)
- WAIST- BELT length: +2.0, +2.0, +2.5, +2.5, **the same steps as the chart's ½ waist and ½ seat**; height constant 13.0.
- FRONT / BACK length: +2.0, +2.3, +2.3, +2.3 vs chart rise + inseam +2.0, +2.0, +2.3, +2.3 (**S→M differs by 0.3**, Q8). Width: FRONT +1.10, +1.10, +1.40, +1.40; BACK +1.10, +1.09, +1.40, +1.40.
- PKT-IN, FACING, FACING1 change **every second size** (XS = S, M = L, then XL).
- DRAWSTRING constant 165 × 4.
- The PDS stops at XL; the chart runs to XXL (Q8).

## Truing checks (would become tests)
| Check | PDS S | Status |
|---|---|---|
| Inseams equal (FRONT 80.954 vs BACK 80.857) | 0.097 | within 0.1 |
| Outseams equal (FRONT 106.802 vs BACK 106.329) | 0.473 | **not equal** (Q-P4) |
| PKT-IN / FACING shared edge | 21.717 / 21.717 | equal |
| PKT-IN / FACING notch pair | 4.750 / 4.740 and 6.201 / 6.212 | within 0.011 (spec limit 0.1) |
| Waistband finished width = chart 5.2 | 10.400 / 2 | equal |

## Questions for the owner / pattern maker / client
- **Q5 (MASTER):** pant seam-allowance roles (body 1.0, waist 1.3, hem 1.5, belt 1.3) are measured but not confirmed.
- **Q8 (MASTER):** is 1074664 (internal 1079077) the block for 1086464? Its waist grades exactly like the chart, but its length grades +0.3 more at S→M; and it has no XXL.
- **Q11 (MASTER):** the PDS appears not to include −5 %: build it into the export, or leave it to Optitex's shrink setting?
- **Q12 (MASTER):** export the PDS T-notches (cut 1.2) or the 0.7 cm slits the SVG draws?
- **Q-P1:** how is the cross pocket built? FRONT has no diagonal corner; PKT-IN (cut in material A) and FACING carry the waist and notch pair; FACING1 is a 22.5 × 3.1 strip. Where do POMs 22145 (3 along the waistband), 22165 (15.5 down the outseam) and 22565 (bag depth 24) sit on these pieces?
- **Q-P2:** the FRONT hem has a vertex at (7.52, −66.54) splitting it 14.000 / 14.010; the BACK hem has none. A crease mark or a construction point?
- **Q-P3:** how are thigh, knee, leg opening and seat measured (square to the grain, or square to the inseam; knee 12" along the inseam or straight down)? Is the hem sew edge the raw turn-up edge (so inseam = sew inseam − 2.8)? The chart's hem height 2.8 and the measured hem allowance 1.5 suggest a 2.8 turn-up inside the sew line plus a 1.5 turn-under.
- **Q-P4:** the outseams differ by 0.473 cm (front longer). Ease, or does the pocket take it up?
- **Q-P5:** the half belt (51.5) is 5.76 cm longer than the body half waist (45.74) and 2.5 longer than the stretched ½ waist (49). Is the body eased into the belt?
- **Q-P6:** drawstring 165 cm total vs chart ½ drawcord 30 (hanging part): is 165 the cord to cut?

## Review sign-off
| Reviewer | Date | Verdict | Notes |
|---|---|---|---|
| | | | |
