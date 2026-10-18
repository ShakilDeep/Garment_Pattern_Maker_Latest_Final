# Marker making (nesting) — `src/marker.rs`

The garment-factory step "lay the patterns on the fabric so as to use the least fabric"
(Optitex *Marker* / *Nest*). Zero dependencies, deterministic, no clock and no threads
(works on wasm32).

## Conventions

* Marker coordinates: `x` runs along the fabric length (= the grain direction), `y` across the
  width, `0 <= y <= fabric_width`, centimetres, y up.
* A placement maps a piece outline `p` to `R(angle) * M(flipped) * p + (x, y)`, where `M` mirrors
  `x -> -x` (flip happens before rotation). `angle` is counter-clockwise, `[0, 360)`.
* `NestPiece.rotations` are **relative to the grain-aligned orientation**: `0` = the piece's
  grain line (direction `grain_deg` in piece coordinates) lies along the marker length; the
  absolute `Placement.angle` is `rotation - grain_deg` (for a flipped piece the grain direction
  mirrors to `180 - grain_deg`). So `[0, 180]` is Optitex "rotation 180" whatever the drafting
  orientation of the piece is.
* Grain rule (`allowed_rotations`): a listed rotation `r` is legal if
  `min(r mod 180, 180 - r mod 180) <= grain_tol_deg`, **or** `r` is a multiple of 90 (listing
  90/270 explicitly means the piece "allows 90"). `one_way_nap` additionally requires `r` within
  `grain_tol_deg` of 0 (mod 360), i.e. no 180 turns. Free steps such as `0,15,30,...` are thus
  filtered by the tolerance. At most 36 rotations per piece are used.
* Flip: `allow_flip` pieces may be mirrored. With `pair_mirroring` (default) odd copies
  (`copy % 2 == 1`) are the mirrored ones (left/right pairs); without it the optimiser picks.

## API (all `pub` in `patternforge::marker`)

```rust
pub struct NestPiece { name, outline: Vec<V2>, qty, rotations: Vec<f64>, allow_flip, grain_deg, grain_tol_deg }
impl NestPiece { pub fn new(name: &str, outline: Vec<V2>) -> NestPiece }   // qty 1, rotations [0,180]
pub struct NestOpts { fabric_width /*150*/, gap /*0.5*/, edge_margin /*0*/, max_length /*10000*/,
                      time_budget_iters /*200*/, seed /*1*/, one_way_nap, pair_mirroring /*true*/ }
pub struct Placement { piece, copy, x, y, angle, flipped }
pub struct NestResult { placements, length, width, efficiency, unplaced: Vec<(usize,usize)>, warnings }

pub fn nest(pieces: &[NestPiece], opts: &NestOpts) -> Result<NestResult, String>
pub fn verify(pieces, &NestResult, &NestOpts) -> Result<(), String>      // independent exact checker
pub fn placed_polygons(pieces, &NestResult) -> Vec<(usize /*piece*/, Vec<V2>)>
pub fn allowed_rotations(&NestPiece, &NestOpts) -> Vec<f64>
pub fn clean_outline(&[V2]) -> (Vec<V2>, Option<String>)
pub fn marker_svg(pieces, &NestResult, &NestOpts) -> String              // fabric, coloured pieces, names, grain arrows, caption
pub fn marker_dxf(pieces, &NestResult, style: &str) -> String            // POLYLINE per piece on layer 1, mm
pub fn pieces_from_pattern(&Pattern, &BTreeMap<String,usize>) -> Vec<NestPiece>
pub fn nest_pattern(&Pattern, &BTreeMap<String,usize>, &NestOpts) -> Result<(Vec<NestPiece>, NestResult), String>
pub fn nest_json(pieces, &NestResult, &NestOpts) -> Json                 // placements+polygons, unplaced, warnings, svg, verified
pub fn opts_from_json(&Json) -> NestOpts
pub fn nest_request(&Json) -> Result<Json, String>                       // API entry (adds "dxf")
```

`efficiency = sum(placed polygon area) / (fabric_width * length)`; `length` is the right-most
polygon edge plus `edge_margin`.

### From a Pattern

`nest_pattern` uses `export::cut_outline` (sew line + seam allowance). Pieces drafted as a half on
a fold (`cf`/`cb`/`crotch_fold` edge) are **unfolded** into the full piece (mirrored about the fold
edge and spliced) because a single-layer marker needs the whole piece. The `qty` map gives the
number of marker copies per piece name; a piece missing from the map defaults to
`qty` (fold pieces), `2*qty` as L/R pair (`mirror` pieces without a fold, `allow_flip = true`), or
`qty`. A map value of 0 leaves the piece out. Grain comes from `Piece.grain`; rotations
`[0, 180]`, tolerance 0.

### API request (for `api.rs`, not wired here)

```json
{"op":"nest","pattern":{...},"qty":{"Front":2},"opts":{"fabric_width":150,"gap":0.5,"iters":200,"seed":1}}
{"op":"nest","pieces":[{"name":"r","outline":[[0,0],[10,0],[10,5],[0,5]],"qty":3,
   "rotations":[0,180],"allow_flip":false,"grain_deg":0,"grain_tol_deg":0}],"opts":{...}}
```
`marker::nest_request(&Json)` returns `{length,width,efficiency,fabric_area,placed,placements:[{piece,name,copy,x,y,angle,flipped,polygon}],unplaced,warnings,verified,svg,dxf}`.

## Algorithm

1. **Clean** every outline (`clean_outline`): drop non-finite points and duplicates, cut away
   swallow-tail loops (e.g. from mitred offsets), replace a still self-intersecting outline by its
   convex hull (warning), make it CCW. Empty / zero-area outlines are reported unplaced.
2. **Orientations**: each allowed rotation (x flip when mirroring is possible) is rasterised on a
   0.5 cm grid (1 cm above 400 copies). A cell is marked when its square is within `gap/2` of the
   polygon, so two pieces whose marked cells are disjoint are guaranteed `gap` apart (a conservative
   no-fit approximation); touching pieces (gap 0) are not flagged. Identical rasters (a rectangle at
   0 and 180) are merged. Orientations that cannot fit the width are dropped before rasterising; a
   piece with none left is reported in `unplaced` with a warning (no panic).
3. **Placement**: items are placed one at a time at the position with the smallest right edge, ties
   to the lowest y, found by a run-length "slide until free" search over every y row. Holes and
   concavities of earlier pieces are used (L shapes interlock).
4. **Improvement**: four sort orders (area, longest side, width, area/extent) then seeded random
   swaps/moves of the best order and noisy area orders; the shortest marker wins. The number of
   iterations is `min(time_budget_iters, WORK_BUDGET / cost_of_first_pack)`, a deterministic
   work bound that replaces a wall-clock budget (no `Instant` on wasm32), so results are
   reproducible for equal seed/inputs.
5. **Exact compaction**: with the true polygons, every piece (left to right) is slid left, down, left
   with steps 4, 2, 1, 0.5, 0.25, 0.1, 0.05, 0.02 cm (plus a snap to the margin) while the exact
   clearance test passes. This removes the raster slack (up to one cell diagonal per gap). Skipped
   above 800 placed copies (warning).
6. **`verify`** re-derives everything with brute-force exact geometry: every copy placed or
   unplaced exactly once, rotation/grain/nap/flip/pair rules, fabric bounds (`y` within the
   margins, `x >= margin`), no overlap and distance `>= gap - 1e-6` for every pair (edge-to-edge
   distances, crossing detection, boundary-touch splitting and interior sample points for nesting
   and coincident outlines), reported length and efficiency. All tests call it.

Hard guarantees: fabric width never exceeded, no overlap, clearance >= gap (1e-6 cm tolerance),
grain/rotation rules honoured, no panics on empty, NaN, duplicated, collinear or self-intersecting
outlines. `Err` is returned only for invalid options (width <= 0, gap < 0, margins eating the
width, width > 10 m, > 20000 copies).

## Measured results (release build, one core, `cargo test --release marker -- --nocapture`)

Pieces are the cut-line polygons of the `<MARKER>` svgs in `samples/52abc29d.xml` (shirt, 12
pieces) and `samples/61dcbea7.xml` (pant, 8 pieces). The unit is 0.01 cm per svg unit (derived in the
test: the FRT polygon perimeter 22355 units vs `GEOM_INFO PERIMETER` 223.5822 cm of size L). Utilisation of
Optitex's own layout = polygon area / marker rectangle.

| case | fabric width | gap | length | efficiency | time |
|---|---|---|---|---|---|
| shirt, Optitex layout | 113.14 | n/a | 154.0 | 0.541 | |
| shirt x1 (this module) | 113.16 | 0.5 | 105.6 | **0.790** | 0.04 s |
| shirt x1 | 113.16 | 0 | 102.3 | 0.815 | 0.04 s |
| shirt x3 sets | 150 | 0.5 | 239.3 | **0.789** | 0.4 s |
| pant, Optitex layout | 118.39 | n/a | 190.1 | 0.453 | |
| pant x1 | 118.39 | 0.5 | 165.0 | 0.522 (bound, see below) | 0.01 s |
| pant x3 sets | 150 | 0.5 | 250.9 | **0.812** | 0.13 s |
| synthetic garment, 7 curved pieces x 6 sizes (84 copies, 60 pts each) | 150 | 0.5 | 1231.5 | 0.814 | ~1.2 s |
| 600 small copies | 150 | 0.5 | | 0.633 | ~1.9 s |

The one-set pant marker contains a 165 x 4 cm strip that only fits along the grain, so any marker is
at least 165 cm long and 0.522 is the geometric upper bound for that fabric width (Optitex's layout
uses 190 cm). Drafted PatternForge garments (default measurements, one set, 150 cm): bodice 0.54,
skirt 0.70, trousers 0.68 (few pieces, so the ends of the marker dominate).

Variance: more iterations help (shirt x3: 0 iterations 0.775, 40: 0.779, 150: 0.788, 400: 0.809), but
the default is capped by the work budget (~1.2 s for ~100 polygons).

## Known limits / not done

* The search is heuristic (bottom-left style with random restarts), not optimal; a 1-3 % gain is
  available with more iterations or a finer grid.
* One fabric layer, single width; no pattern matching (stripes/plaids), no block fusing, no
  buffer/shrinkage per piece (`Shrink` and `TILT` from `NESTING_ENABLES` are not modelled), no
  cutter-path ordering.
* Self-intersecting outlines are repaired by dropping the smaller loop or by the convex hull, so
  the area of such a piece can shrink or grow; a warning is issued.
* The marker DXF is AAMA-style (closed polylines on layer 1 with name text and grain lines) and,
  like the pattern DXF, is not verified against Optitex.
* `api.rs` / web are not modified; `nest_request` is the intended hook (`"op":"nest"`).
