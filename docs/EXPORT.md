# DXF export (AAMA/ASTM-style) for Optitex

**Status: NOT verified against Optitex.** Nothing here has been opened in Optitex yet. The file is
written from the public AAMA/ASTM D6673 conventions plus what the sample PDS files show. Native
`.pds` is not written (proprietary, undocumented); use File > Import > DXF AAMA/ASTM.

Units: **millimetres**. Pattern model is cm; every coordinate is multiplied by 10. Each piece block
has its origin at the lower-left corner of the cut-line bounding box. Each file starts with a 999
comment saying "Not verified against Optitex".

## API (src/export.rs)

| function | purpose |
|---|---|
| `dxf_aama(sizes, style)` | R12 polylines only (header `AC1009`), curves flattened to 0.02 cm. Unchanged signature. |
| `dxf_aama_opts(sizes, style, &ExportOpts)` | same, with `ExportOpts { chord_tol, curves: Spline \| Polyline }`. `ExportOpts::default()` = 0.02 cm + Spline; `ExportOpts::polyline()` = pure fallback. |
| `dxf_graded(sizes, base, style)` / `dxf_graded_opts` | graded export (nested sizes), see below. |
| `cut_outline(piece)` | unchanged: (sew, cut) polygons, 16 steps per curve. |
| `cut_outline_tol(piece, tol)` | same but adaptive flattening to chord tolerance `tol`. |
| `flatten_adaptive`, `edge_bezier` | helpers (adaptive outline; cubic control points of a curved edge). |

geom.rs additions: `flatten_cubic_adaptive(p, tol)`, `offset_polygon_opts/_ex`, `offset_polygon_legacy`
(old behaviour, kept only for before/after numbers), `DEFAULT_MITER_LIMIT`, `DEFAULT_TRANSITION_MITER_LIMIT`.

## Layers

| layer | content | entity |
|---|---|---|
| 1 | cut boundary (seam-allowance line); also the ASTM text annotations | closed POLYLINE, TEXT |
| 4 | generic notch (`slit`, `v`, unknown kinds) | POINT |
| 6 | fold line (pieces drawn as a half with `cf`/`cb` edges) | LINE |
| 7 | grain line, from `Piece.grain` | LINE |
| 8 | internal lines and dart legs (a - apex - b) | open POLYLINE |
| 13 | drill holes | POINT |
| 14 | sew line | closed POLYLINE (polyline mode) or POLYLINEs + SPLINEs (spline mode) |
| 80 / 81 / 82 / 83 | notch type `t` / `castle` / `check` / `u` | POINT (on the cut line; width = 1, depth = SA in mm capped at 5, angle = inward direction) |
| `CUT_<size>`, `SEW_<size>` | nested grade outlines (graded export only) | closed POLYLINE |

## Metadata (TEXT on layer 1, one per line, inside each piece block)

`Piece Name`, `Size Name`, `Quantity`, `Material`, `Style Name`, `Mirror: YES|NO`, `Fold: YES|NO`,
`Grain Line: <angle> deg`, `Nesting: Rotate=180 Flip=YES|NO`.

* Quantity = `qty` x 2 for mirrored pieces, but `qty` as-is for fold pieces (same rule as before).
* Material is the fabric code (`Piece.material`). Mirror = piece is cut as a left/right pair.
* Nesting is a **hint** only: rotation 180 is always allowed; flip is allowed when the piece is a mirrored pair.
  The model has no per-piece nesting flags; Optitex may ignore this text entirely.

## Curve method

Where a node has Bezier handles the edge is a cubic Bezier.

* **Spline mode** (`CurveMode::Spline`, header `AC1014`, `$INSUNITS = 4`): each curved *sew* edge is one
  `SPLINE` (degree 3, 4 control points, clamped knots 0,0,0,0,1,1,1,1, planar flag 8). This is an exact
  Bezier, so length error is only the 0.01 mm coordinate rounding. Straight runs between curves are open POLYLINEs.
  SPLINE is **not** R12; it needs R13 or later. If Optitex drops or mangles splines, use polyline mode.
* **Polyline mode** (`CurveMode::Polyline`, header `AC1009`): adaptive subdivision; no point of the true curve
  is more than `chord_tol` (default **0.02 cm = 0.2 mm**) from the polyline. Vertex count follows curvature.
* The **cut line** (layer 1) is an offset of the flattened sew line, so it is always a polyline in both modes
  (an offset of a Bezier is not a Bezier). Arc joins at sharp corners use a chord error of `chord_tol / 4`.
* Tests: spline control polygons give the model's curve length within 0.02 cm over a whole bodice; polyline
  mode is never longer than the model and is short by < 0.1 %.

## Cut-line corners (item #19)

`offset_polygon` now arc-joins sharp convex corners instead of spiking them. Rules, per corner:

* offset lines meet within `limit * offset` of the vertex: mitered (one point);
* convex corner beyond the limit: circular arc around the original vertex;
* reflex corner beyond the limit: bevel.

`limit` is **1.8** where both adjacent edges have the same allowance, **1.3** where the allowance changes
(sleeve cap 1.7 -> 1.5 -> 0.8). The ratio is `1/cos(turn/2)`, so 1.8 mitres turns up to about 112 degrees.
This is an *empirical fit to the two sample garments*: the XML keeps full miters at 110 degrees on the pant
facings (equal allowance) but not at the allowance changes on the sleeve cap. The coordinator's suggested
single limit of 1.6 was tried and made the facings worse (cut perimeter -1.0 % -> -2.4 %, width -1.2 % -> -3.5 %,
which also failed `garments::geometry_matches_xml_within_documented_error`), so it was not adopted. Two sample
garments are thin evidence; if Optitex output differs, tune the two constants in `geom.rs`.

Exact expectations:

* Rectangle with allowance `sa`: cut perimeter = sew perimeter + **8 * sa** (every corner is a mitre, 4 x 2*sa).
* General polygon, equal allowance: cut = sew + sum over mitred corners `2*sa*tan(turn/2)` + sum over arc-joined
  corners `sa*turn` (radians, slightly less because the arc is a chord polygon) - reflex corners subtract.
  Tested on a 3-4-5 triangle (one mitred right angle, two arcs).

Measured before / after (`cargo test --release export:: -- --nocapture`):

| case | XML / file | before | after |
|---|---|---|---|
| shirt Sleeve L cut perimeter (XML PERIMETER 129.8, SEW_PERIMETER 118.1) | 129.8 | 132.57 (+2.14 %) | 130.28 (+0.37 %) |
| pant FRONT S, cut minus sew perimeter, decoded PDS, per-edge SA read from the file's cut polygon | 9.4568 | 9.6906 | 9.6906 |

The pant FRONT is **unchanged** because none of its corners exceed the limit (all turns are under 25 degrees
except right angles, which stay mitred); the remaining 0.23 cm difference is not corner handling. With a
uniform 1.0 cm allowance the delta is 7.93 against 9.46, because the real piece has a larger hem allowance.
The other agents' garment tests (area, perimeter, width limits against all sizes of both samples) still pass.

## Graded export

Method: **nested per-size pieces on size-specific layers**, not ASTM point grade rules. Reason: the model
re-drafts each size from measurements, so there are no grade rules, only finished outlines per size, and I
could not verify a rule-table (`.rul`/D6673 point-grade) writer without Optitex. Structure of `dxf_graded`:

1. base-size piece blocks first, byte-identical to `dxf_aama_opts` for that size (tested);
2. every other size next, one block per piece named `<piece>_<size>`, `Size Name:` text carries the size;
3. one `<piece>_NEST` block per base piece overlaying all sizes' cut (`CUT_<size>`) and sew (`SEW_<size>`)
   outlines, aligned at the start of the grain line (the grade reference point).

If the base size is not in the list, the first size is used and a 999 comment says so. Optitex may import
sizes as separate pieces rather than as one graded piece; that is the main thing to check.

## What to check when importing into Optitex (item #26)

1. **Units**: the imported piece should be the expected size in mm (a 100 cm bodice width must read 1000 mm
   in DXF units / 100 cm in Optitex). Pick metric in the import dialog; the file has no `$INSUNITS` in polyline mode.
2. **Layers**: 1 cut, 14 sew, 7 grain, 8 internal, 13 drill, 80-83 notches, 4 generic notch, 6 fold. Check each
   lands as the Optitex object you expect (cut line vs sew line not swapped, internal lines not turned into seams).
3. **Notches**: count per piece, position on the cut line, direction pointing inward, depth equal to the seam
   allowance (max 5 mm), type (T / castle / check / U) mapped to the right Optitex notch style.
4. **Grain**: line present on layer 7 with the correct direction, not flipped.
5. **Piece names / metadata**: name, size, quantity (a mirrored pair = 2), material, mirror and fold flags
   read from the text. If the text is ignored, note which fields Optitex needs in another format.
6. **Curve fidelity**: import both modes. Overlay or measure a curved edge (armhole, crotch): with splines it
   should be a smooth curve, with polylines the facets should be invisible at 0.2 mm. Compare sew-line length per
   edge against the XML values. Report whether SPLINE entities were accepted at all.
7. **Grading**: all sizes appear; check whether they arrive as one graded piece or separate pieces; check that
   the nests (`CUT_*`, `SEW_*`) overlay at the grain-line start; check growth per size against the spec table.
8. **Cut-line corners**: look at sharp corners (sleeve cap, facing points): arc, not a spike; compare cut
   perimeter against the XML `PERIMETER`.

Please send back anything that fails (and the Optitex version) so the writer can be corrected.
