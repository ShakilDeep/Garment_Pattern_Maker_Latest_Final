# Technical basis: web + Rust garment pattern-design app

Status note: written from working knowledge (no live source checks). Crate APIs and version-specific features (flagged "verify") should be confirmed against docs.rs before committing. Drafting constants below are *representative linearisations* of the Aldrich/Armstrong tables, not verbatim book values; they must be calibrated (see 1.0).

---------------------------------------------------------------------------
## 1. Parametric drafting from body measurements

### 1.0 Principles
- A block is a **script of construction steps** over named points: `P = origin + (dx, dy)`, `P = point_on_line(A,B,t)`, `P = intersect(lineA, lineB)`, `P = perp_from(A, dir, len)`, `P = circle_intersect(...)`, then curves through named points with handle rules. Store the script (a small DSL/JSON op list), not just the resulting geometry: that is what makes it parametric and re-solvable when a measurement changes.
- Units: cm (f64). Coordinates: x right, y DOWN (screen/pattern convention), CB (centre back) on x=0 for back pieces; CF on x=0 for front pieces, mirrored when needed. Drafts are half-blocks (one side), mirror on cut.
- Books give constants per size (a chart) and formulas as `measure/k + c`. Implement formulas as `a*measure + c` plus an override table per size; **calibrate by plotting the 8-14 size range and comparing to the published block, then print 1:1 and toile**. Aldrich is the better reference for a single-measure-driven (chest-driven) system; Armstrong (Patternmaking for Fashion Design) for the "measurement + ease" style with explicit dart manipulation; Winifred Aldrich also gives trousers/sleeve with armhole-length-driven sleeve cap.
- Ease is a first-class parameter: `ease_bust` (Aldrich ~8 cm total on 4 quarters => ~2 cm per quarter-ish; Armstrong 2.5-5 cm), `ease_waist`, `ease_hip`, `ease_sleeve_cap` (2.5-4 cm).
- Measurements (all cm): bust B, waist W, hip H (at hip depth HD below waist, default 20), nape-to-waist (back length) BL, front waist length FWL (shoulder-point/HPS to waist over bust), neck circumference N, shoulder length S, across-back AB, across-chest AC, bust-point separation BPS, bust-point height BPH, armhole/scye depth SD (or derived), upper arm U, wrist Wr, sleeve length SL (shoulder-tip to wrist over bent elbow), elbow height, waist-to-knee, waist-to-floor, inseam IS, outseam OS, body rise (crotch depth, seated) R, thigh T, knee K, ankle A, height Ht.
- Derive missing ones from bust/height by regression defaults (e.g. SD = B/8 + 9.5; AB = B/8 + 6.5; AC = B/8 + 5.2) so the user can fill in only 5-6 measures first.

### 1.1 Bodice (half-block). Back first, then front.
Use lengths in cm, ease Eb = 8 (total circumference ease; per half-block quarter = Eb/4 = 2 added at CB/CF pair).

BACK (origin at CB neck, x=0,y=0 is the *nape* point A):
1. A = (0,0) nape. B = (0, BL) waist at CB. C = (0, SD) chest/scye line at CB, with SD = B/8 + 9.5 (88 bust => 20.5).
2. Chest line: horizontal from C, half-width of back-block D = (B+Eb)/4 => D = (B/4 + 2) at side seam. Side seam vertical x = D from chest line to waist (and a `waist-line` y = BL).
3. Back neck width AN = N/5 - 0.2 (Aldrich-like), so N1 = (AN, 0). Neck rise: N1' = (AN, -2.0) (back neck sits 2 cm above A line)  -- equivalently neck point on a square from A.
4. Shoulder point: back width line x = BW = B/8 + 6.2 from CB, drawn from scye-line level up to y = shoulder-level. Shoulder slope drop: S1y = BL-independent drop of ~ (S_drop_back ≈ 4.0 cm below N1' level). Shoulder tip SP = point at distance S + 1.5 (dart/ease; Aldrich adds 1.5 for shoulder dart suppression on back) from N1' on a line sloping down by `drop` => solve `SP = N1' + S_b * (cosθ, sinθ)` with sinθ = drop/S_b; clamp SP.x to ~BW+ (0 to 1). Armhole width reference x = BW.
5. Shoulder dart (back): 1.5-2 cm intake, point at 1/3 of shoulder from neck, length 7-8 cm toward the scye/blade-point. (Optional: Aldrich puts it in the shoulder; others in waist.)
6. Armhole curve (back): from SP, down to a point E on x = BW at depth `(C.y - SD/3)`, i.e. back-scye-mid is at about SD*0.45 below shoulder tip level; end at side seam on chest line G = (D, SD). Use a cubic with tangents: at SP tangent roughly perpendicular to shoulder (rotate shoulder dir by +90°-~10°), at E tangent vertical (the "back width" point is where armhole is most vertical); at G tangent angled ~ 20° above horizontal (armhole bottom is a gentle "J"). Cubic 1: SP -> E handles length ≈ 0.4*|SPE|. Cubic 2: E -> G through (BW+ (D-BW)*0.5, SD - 1.2) with handle lengths ≈ 0.5 of chord. (Alternative: single quintic; keep as 2 cubics for editability.)
7. Back waist darts / waist suppression: total suppression = (B+Eb)/4 - (W+Ew)/4 + (bodice allows side-seam suppress ~ 1.5-2). Distribute: side seam 1.0-1.5, back waist dart ~ 2.0-2.5 (position at BPS*? or center of shoulder blade x = BW/2), remaining to CB shaping (0.5 hollow of back: CB curved in by up to 1 cm at waist).
8. Hem/waist line: horizontal at y = BL; waist side point = (D - sides_supp, BL).

FRONT (origin at CF on same chest line; mirror x so CF is x=0):
9. Front length: CF waist at (0, FNL) where FNL (nape to waist at front) = BL + 1.0 (bust-curve length). Aldrich lengthens front by about 0.5-1.0 and handles bust by dart.
10. Chest line same depth SD+? Keep SD_front = SD (+0.0). Chest width D' = (B+Eb)/4.
11. Front neck: width N_f = N/5 - 0.2 (same as back, offset -0.2), depth N_d = N/5 + 0.8 (neck depth below HPS-level ≈ 6.9 cm for N 35). CF neck point (0, N_d); neck curve: cubic from (0, N_d) to HPS=(N_f, 0), handles: at CF tangent horizontal (length ≈ 0.55*N_f), at HPS tangent ~ 80°-90° (vertical-ish, length ≈ 0.55*N_d).
12. Shoulder: HPS to SP_f with length S (front shoulder = back shoulder - 1.5 when back has dart). Slope drop ≈ 4.5-5.0 (front drops more than back). 
13. Across chest AC_x = B/8 + 4.2 (front). Armhole (front): SP_f down to X (x = AC_x, y at SD*0.40-0.5) then to side seam G' = (D', SD) in a deeper, rounder curve than back; mid control point at distance such that curve is concave toward body: use `(AC_x + 0.3*(D'-AC_x), SD - 0.8)`. Front armhole is ~1 cm deeper-looking: scoop = 1.0 at the notch.
14. Bust point BP = (BPS/2, BPH_y) with BPH_y = HPS.y + (HPS-to-bust measured) or default `SD + 1.0` (≈ 25.5 for bust 88). 
15. Bust dart (waist/side dart): amount = ~ (cup size) with the standard `1 cm per cup difference` or `(B_full_frontside - B_back)/ ...`: Aldrich uses dart intake of ~ 2.5-3 cm per back-front difference; practical formula: dart_angle = 2*asin(((FNL - BL) + 2)/BP_to_waist) roughly; use *pivot* instead: slash from side seam at (D', y_bust+ ~ 5 below armhole) to BP, rotate wedge closing the waist-ease... Key: implement the **dart rotation (pivot) operation** (see 2.5), not hardcoded numbers, so users can move the dart into shoulder, French, side, waist, etc.
16. Waist dart: apex 2.5 cm below BP, length from waist hem line = BP.y - 2.5 to hem line; intake = (front 1/4 W+ease) deficit minus side seam suppression: `intake_f = (B+Eb)/4 - (W+Ew)/4 - side_supp_f` (side_supp_f ~ 1.0).
17. Side seam: from G' down to waist with a 'vase' hollow (cubic, 0.5 cm in at waist). The back and front side seams must be equal in length: add a verification (`assert |len_back_side - len_front_side| < 0.2`) and a constraint solver option to nudge dart intake.

Validity checks to implement as automated constraints (huge value to the user): armhole length F + B (cm), neck length, side-seam length parity, shoulder length parity, total waist ratio, dart apex distances (bust dart apex ≤ 2.5 cm from BP).

### 1.2 Straight skirt (half-block front & back)
- Waist-to-hip depth HD = 20 (Armstrong 8-9 in; Aldrich 20-ish). Hem length SL_skirt (default 58).
- Hip circumference per half-block quarter: qH = (H + Eh)/4 with Eh = 4 => (H+4)/4 = H/4 + 1. Waist quarter qW = (W + Ew)/4 with Ew = 1 (skirt waist ease; 0.5-2).
- Front: CF line x=0; Hem y = SKL. Hip point = (qH, HD). Waist side point = (qW + total_dart_f_remaining, 0). Total waist suppression per quarter: S_t = qH - qW. Distribution: side seam suppression 1.0-1.25 (curve raises by +0.7 at side waist); remaining is split into **darts** (front: 1 dart = 1.5-2.0 each; back: 2 darts 1.5-2.0 each; or 1 big back dart 3 cm if S_t <= 3). `n_darts = clamp(ceil((S_t - side)/2.2), 1, 2)`.
- Dart placement: first dart centred 1/3 along waist from CF (front: at 8-9 cm from CF, length 9-10 cm; back: 9 and 18 cm from CB approx, lengths 12 and 14; ends tapering to point).
- Side seam: line from hip point to hem with slight flare option: hem width = qH - taper (pencil) or + flare (0 to 10). Side seam waist-to-hip as cubic: handle at waist directed down-out, at hip tangent vertical.
- Waist curve: raise at side by +0.7-1.0 (front), +1.0-1.2 (back); CB waist lowered -0.5 to -1.0; waist as a cubic from CB/CF to side.
- Pattern: also lengthen/shorten, A-line = rotate/slash at hip, dart-to-flare conversion.

### 1.3 Trousers (basic block, Aldrich style; front & back)
Parameters: waist W, hip H, rise (body rise: waist to crotch seated) or derive R = H/4 + 0.5*(HD*?)... but safer: use measured crotch depth + 1.5 ease. Inseam IS, knee width, hem width, outseam OS = waist-to-floor.
- Verticals at x=0 is the crease line placed later. Define from *crotch line* approach:
  1. Waist line y=0, Hip line y = HD (18-20). Crotch line y = CD = R + ease(1.5) (body rise + ease), Knee line y = CD + IS/2 - 5, Hem line y = OS (waist-to-floor) - 1.0 (with hem crease) or CD + IS.
  2. Front: Side-seam vertical at x = 0 (outside edge), centre-front/waist x = Fw = (H+Eh)/4 - small = H/4 + 1 (Eh ~ 4-8); crotch point extension forward Fx = H/20 +0.5 (≈ 4.8 cm for 94) beyond Fw at crotch level (front crotch extension; Aldrich ≈ H/20 - ? ). Back crotch extension Bx = H/10 + 0.5 (≈ 9.9) because back is deeper: this is the **crotch-fork difference**: Fx ≈ 0.5 * Bx.
  3. Crease line: x = (Fw + Fx)/2 for front (halfway between outer side seam and crotch extension), same for back. Knee and hem widths drawn symmetric about crease: kw = K/4+ ease or hem = A/4 + ease, with front narrower by 1 cm and back wider by 1.
  4. Waist: front waist = W/4 + 1.0 (ease) + dart 2.0 (front 1 dart or pleat); back = W/4 + 1.0 + 2×dart ~ 3 total; centre-back raised 2.5 to 3.5 cm ("CB rise") with CB seam sloping from waist to crotch: CB seam line from (Fw+ext, CB_waist_up) to crotch ext. Waist curve cubic: from CB-raised point to side-seam waist dropping 1 cm (back) / 0.5 (front).
  5. Crotch curve (front): cubic from CF-waist (x≈Fw,y=0) down (vertical tangent) to crotch point (Fw+Fx, CD) with horizontal tangent end, handle lengths about 0.55*CD and 0.55*Fx. The back crotch curve uses a deeper "hook": from CB-waist (sloped line) down to a point at CD-... curve to crotch with end tangent horizontal and handle ~ 0.6*Bx.
  6. Side seam: from hip point (0,HD) to knee at x = crease - kw, hem: x = crease - hw; use cubic from waist to hip to knee with slight curve. Inseam: from crotch point to knee, to hem straight.
  7. Checks: front/back inseam length parity (±0.3), side seam parity, crotch seam length (front+back) against body crotch length, thigh width at crotch line >= T/2 + ease (Aldrich: thigh must be ≥ T + 5..8 total).

### 1.4 Set-in sleeve
- Requires the **armhole length AH measured along the bodice armhole curves**: `AH_b`, `AH_f` (use curve arc-length from geometry, kurbo `arclen`).
- Sleeve cap height CH = 0.33*(AH_f + AH_b)/2 .. choose by style: `CH = (SD - (B/8+... ))` Aldrich: cap height = armhole depth*(2/3) ... simpler & stable: CH = SD - (bodice shoulder-tip drop adj.) * ~0.65 => for SD=20.5, CH ≈ 14 (typical 13-15). Use CH = AH_total/6 + 3.0 as the slider default and expose.
- Sleeve width at bicep line SW = (U + Es) / ... with Es = 5 to 8; half-width each side = (U+Es)/2 /... (sleeve block drawn flat as full width: SW = U + Es). Place centre line (grain) vertical x = SW/2, y=0 at cap top (crown).
- Biceps line at y = CH. Cuff width Wr+ease (Cw = Wr + 4) at y = SL (sleeve length), elbow line y = SL/2 + 3. Elbow dart or back-sleeve extension: back seam extra 1.0-1.5 at elbow, with elbow dart 2.5.
- Cap curve: front half from crown (x0, 0) -> notch front (SW/2 - SW/2*? ...). Standard: points: crown C0=(SW/2,0); front notch Fn at bicep line distance? Use: Front cap curve from front bicep end F=(0,CH) up to a point 1/4 of the front-armhole length along (guide point Gf) then crown; Back cap curve from back bicep end B=(SW,CH) via guide Gb on a back-depth ~ 2.5 cm higher; typical **shape control points**: Gf = (SW*0.25, CH*0.62 + 0.5 inward concave of 1.2 cm), Gb = (SW*0.76, CH*0.55). Each half cap curve uses 2 cubics with tangents horizontal at the crown (ease: ×smooth) and tangent ≈ 45° at bicep ends (concave for front, convex for back).
- **Solve for cap ease**: define `cap_len = arclen(front cap) + arclen(back cap)` and target `cap_len = AH_f + AH_b + ease_cap` (2.5-4 cm for woven, 0-1.5 knit). Adjust CH (and optionally width of cap shaping) with 1-D Newton/bisection until constraint satisfied (expose solved CH to UI). Implement this as the *generic parametric constraint solver* applied to patterns: `solve(param, target, f)` with brent root-finding.
- Sleeve head notches: single front, double back, plus crown notch and shoulder dot. Compute from arclen fractions: front notch at (AH_f's armhole notch distance from underarm), back double at corresponding distance + ease distribution (more ease above across-back/chest points).
- Cuff / vent / shirt sleeve variants: derive by templates (see 2.5 pattern operations).

### 1.5 Neckline/armhole/dart manipulation operations (library of ops, in Rust)
- `rotate_dart(piece, from_dart, to_edge_point)`: pivot around bust apex: rotate the portion of the outline between two slash lines by dart angle; recompute outline; keeps edge lengths (except at dart legs).
- `close_dart`, `open_dart(piece, edge_param, width, length)`, `slash_and_spread(piece, slash_lines, amounts)`, `add_fullness`/pleat/gather, `offset_neckline`, `extend_hem_flare`, `lengthen_shorten(line, delta)` that translates part of an outline below a horizontal cut and re-stitches, `mirror`, `join(pieceA, edgeA, pieceB, edgeB)` for facings and yokes, `facing_from_edge_range(piece, a, b, width)`.
- These operate on the data model (section 2), not on the script, and produce a new Piece (non-parametric). Keep both layers: parametric `Block` -> derived `Piece`s -> operation tree (history) -> final `Piece`s. Store the whole as a DAG (like Seamly2D/Valentina's `VPattern`, FreeSewing's design-parts). Prior art to study: FreeSewing (JS, parametric designs, "points/paths/snippets" model, MIT/GPL-3? (FreeSewing core is MIT, verify)); Seamly2D/Valentina (C++, GPL, XML .sm2d, measurement tables .smis/.vit, "increments" and formula strings); Tau Meta Tau Pattern editor; PatternMaker (Python/CAD). All use *named points, expression language over measurements, curve operations*. Design a small expression language (`BL * 0.5 + 1.5`, `intersect(...)`, `arclen(curve)`) — evaluate with `evalexpr`/`rhai` crates or `fasteval` (cheap) -> deterministic; user-editable formulas make the app competitive with Seamly.

---------------------------------------------------------------------------
## 2. Data model

### 2.1 Core geometry (Rust, serde-able, all f64 cm)
```rust
pub struct Pattern { id: Uuid, meta: Meta, units: Unit, params: ParamTable,   // measurements, ease, flags
                     blocks: Vec<Block>, pieces: Vec<Piece>, history: Vec<Op>,
                     size_chart: SizeChart, rules: Vec<GradeRule> }

pub struct Piece {
  id: PieceId, name: String, material: MaterialRef, cut_qty: CutSpec { n: u8, mirror: bool, on_fold: Option<EdgeId>, per_fabric: .. },
  outline: Outline,            // closed, CCW, ordered
  internal: Vec<InternalLine>, // darts-as-lines, fold lines, pocket placement, buttonholes, drill points
  notches: Vec<Notch>, grain: GrainLine, darts: Vec<Dart>, marks: Vec<Mark>,
  seam_allowance: SeamAllowance, label: Label, transform: Affine,   // layout placement
}

pub struct Outline { nodes: Vec<Node>, closed: bool }
pub struct Node { id: NodeId, p: DVec2, kind: NodeKind /* Corner|Smooth|Symmetric|Auto */, 
                  h_in: Option<DVec2>, h_out: Option<DVec2>,   // *relative* handle offsets (cubic control = p + h)
                  edge_tag: Option<EdgeTag>, // sewing label of edge FOLLOWING this node
                  grade: GradeRuleRef }      // rule id (see 3.)
// Edge = segment between node i and i+1: line when both handles None; cubic otherwise.
pub enum EdgeTag { Plain, Fold, Stitch{ name }, Hem, Armhole, Neckline, SideSeam, .. } 
```
- Store **relative** handles (so moving a point moves its handles), `NodeKind` guides handle regeneration (Auto = Catmull-Rom/natural to cubic conversion; kurbo's `BezPath` + `Smooth` helpers or own).
- Edge-level properties: `seam_allowance_override: Option<f64>`, `sew_group: Option<SewGroupId>` (for sewing constraints), `ease_ratio` (gather), `notch positions along edge as t∈[0,1] arc-length parametrised`.
- Notches stored **parametric on an edge**: `Notch { edge: EdgeId, s: f64 /*arc-length from edge start*/, kind: Single|Double|Triple|Dot|T|Slit, depth: f64, orientation: Auto }`. Reason: resilience under editing and grading (arc-length recomputed per size).
- Grainline: `GrainLine { a: DVec2, b: DVec2, arrows: Both|One, bias: f64 }` (two points; auto-placement option = longest axis-aligned inside polygon, clipping with `geo::Rect` inset). Fold: edge tag Fold + `GrainLine` parallel.
- Darts: `Dart { apex: DVec2, leg_a: EdgePos, leg_b: EdgePos, intake: f64 (derived), kind: Pivot|Fisheye|Contour|Princess, mid_line }`. For output: fold along the dart's mid line; seam allowance computed on the *closed* dart outline (or fold-out darts) -- the standard practice is "close dart then offset" (paper pattern: cut and fold dart before cutting SA) to get correct SA corners. Implement `Piece::resolved_outline(with_darts_closed)` using geometric fold (rotate one leg onto other).
- Internal lines: `InternalLine { poly: BezPath-like, style: Dash|Dot|Cut|Fold|Draw, label }`.
- SA/cutting line: **derived**, not stored: `cutline = offset(outline.flattened, per-edge distance)`, recomputed on edit/grade. Cache result keyed by version hash.

### 2.2 Seam allowance offset
- Flatten each edge with Bezier flatten at tolerance 0.02 cm (kurbo `flatten` or `BezPath::flatten`), keep **edge IDs** per polyline segment run so corners get per-edge offset.
- Preferred: use kurbo **offset** (kurbo 0.11+ `offset::offset_path`/`CubicOffset`, verify) for *curved variable-SA-by-edge* offsets, join with mitre (limited), bevel (SA corners at < 135° get a square-cut "mitred hem corner" per sewing practice: `corner_mode: Mitre | Square | HemFold`).
- Alternative robust path: `i_overlay` (`outline` / `OutlineOffset` feature, verify) or Clipper2-style (`clipper2` crate, FFI to C++ clipper2, or `clipper2-rust` port, verify) offsets for polygon in outward direction with round/mitre joins -- gives **uniform SA only**. For *per-edge distances*, offset each edge individually as a line/curve, intersect adjacent offsets (extend) with mitre limit, and use `i_overlay` boolean `Simplify`/union to repair self-intersection loops (typical on concave curves with SA > curvature radius).
- Also support `cavalier_contours` crate (polyline with arc segments offset, robust, parallel offset with bulge arcs) if you move to arc-fitted outlines.
- Typical SA: 1.0 (curves), 1.5 (straight), 4-5 (hem), 0.6 (necklines/armholes in industry), custom per edge.

### 2.3 Grading
- Industry model (AAMA/ASTM, Gerber/Optitex): each pattern point has (dx,dy) growth per size step relative to a **base size**; the pattern is regenerated per size by adding cumulative deltas: `P_s = P_base + Σ_{k=base}^{s} Δ_k`. Grade rules attach to **points** (and handles).
- Data model:
```rust
pub struct SizeChart { sizes: Vec<SizeId /* e.g. "8","10",... */>, base: usize, steps: Vec<SizeStep /* bust Δ, waist Δ, hip Δ, height Δ... */> }
pub struct GradeRule { id: RuleId, name: String, per_size: Vec<DVec2> /* delta from previous size (or from base) */, 
                       handle_policy: Follow | Independent{in_d, out_d} }
// Node.grade = Option<RuleId>; if None, node = base position (no growth). Handles are dragged with node by default and may have their own deltas.
```
- Rule ergonomics (the UX): grade rules as **grade-by-measurement**: `dx = a * ΔB + b * ΔW`, `dy = c * ΔBL + d * ΔSD` e.g. armhole depth point: dy = ΔSD (≈ 0.5 cm per size), side seam hip: dx = ΔH/4, etc. Compile these into per-point per-size deltas. Store both (formula + baked table) so the user can override a single point/size.
- Typical grade increments (EU/UK 4-6 cm bust/hip per size, but use per-size deltas in cm): bust +4, waist +4, hip +4, shoulder +0.3, neck +0.3, back length +0.3/0.5, armhole depth +0.5, bicep +1.3-1.5, thigh +2.5, inseam +0 (per size) or +1 per height class. Implementation: distribute across points using *grade reference lines* (horizontal/vertical): points to the right of the chest-line side grow by ΔB/4; points below waist by ΔBL; etc.
- Validation: after grading, re-run the same constraints (armhole length, side-seam parity, sleeve-cap ease) and **recompute notch arc-length positions**; flag violation. Offer "regrade from blocks" for parametric pieces (instead of per-point rules), i.e. each size is just re-evaluate the parametric block with that size's measurements -- the cleanest solution; per-point grading is mainly for imported (DXF) patterns and hand-edited pieces. Provide both.
- Interchange: `dxf` crate / hand-rolled ASTM-D6673 style DXF writer/reader with layers (1 = cutting line, 8 = notches, 7 = grain, 6 = internal) and AAMA header for size names. Also PDF tiled printing and SVG, plus PLT/HPGL for plotters (optional).

### 2.4 Serialization
- JSON via serde with `#[serde(tag="type")]` enums; schema versioning `version: u32` + migrations; use `schemars` -> JSON Schema -> **`tsify`/`ts-rs`** for TS types (`ts-rs` for HTTP, `tsify` for wasm-bindgen). Use CBOR/`postcard` for compact binary snapshots in IndexedDB. Undo history as list of `Op`s with inverse ops (command pattern), or `im`/persistent structures for O(1) snapshots; consider `automerge`/`yrs`(Yjs Rust) CRDT for collaboration later.

### 2.5 Operation interface (pure functions)
`fn apply(op: &Op, &Pattern) -> Result<Pattern, Err>`; ops: `MoveNode`, `SetHandle`, `InsertNode(edge, s)`, `SplitPiece(line)`, `RotateDart`, `Slash/Spread`, `Mirror`, `Join`, `OffsetEdge(range, d)`, `SetSeamAllowance`, `AddNotch`, `SetParam`. Deterministic, serializable => replay, collaboration, test fixtures (golden SVG/PDF snapshot tests with `insta`).

---------------------------------------------------------------------------
## 3. Rust crates & WASM vs native backend

| Need | Pick | Notes |
|---|---|---|
| 2D curves, arclen, nearest point, flatten, offset/stroke | **kurbo** | `CubicBez`, `BezPath`, `ParamCurveArclen`, `ParamCurveNearest`, `flatten`; offset/stroke in recent versions (verify). Pure Rust, wasm-friendly. Primary geometric kernel. |
| Boolean ops, simplify, polygon offset | **i_overlay** (+ `i_float`, `i_shape`) | Pure Rust, fast, robust integer-based; union/diff/xor/clip; `OutlineOffset`/`StrokeOffset` features in recent versions (verify). Good for SA repair, nesting overlap tests, layout collision. Alternatives: `geo` (`BooleanOps` via i_overlay in recent versions? older uses `geo-clipper`; verify), `clipper2`/`clipper2-rust`, `cavalier_contours` (arc polylines). |
| Higher-level geometry (area, contains, simplify, convex hull, rotations, rstar index) | **geo**, **geo-types**, **rstar** | `geo` for polygon ops, `Rotate`, `Translate`, `Simplify`, `Contains`. |
| Tessellation (fill/stroke, curve flattening) | **lyon** (`lyon_tessellation`, `lyon_path`) | Fill tessellation of curved paths with holes into triangles (indices + vertices) for three.js; stroke tessellation for line rendering. Good for SVG-path -> mesh. |
| Triangulation (polygon -> tris) | **earcutr** (earcut port) or lyon | Earcut: fast, simple, produces sliver triangles. For cloth and FEM-ish simulation, need **good-quality triangulation**: use **spade** (constrained Delaunay + refinement, `spade::ConstrainedDelaunayTriangulation`, `refine` with `RefinementParameters`) or `cdt`, `poly2tri-rs`, `delaunator` (unconstrained). Spade is the pick for cloth meshes: refine to a target max edge length (0.8-1.2 cm), with boundary edges = seam edges (constrained). |
| Linear algebra | **glam** (f32 GPU-ish; has DVec2/DVec3) or **nalgebra** | glam for sim/render; nalgebra if you need dense solves / SVD (e.g. mannequin fitting, least-squares dart solving). `faer` for sparse/dense solvers (implicit cloth) in WASM, verify. |
| Serialization | **serde**, **serde_json**, `schemars`, `tsify`/`ts-rs`, `postcard`, `rmp-serde` | |
| WASM glue | **wasm-bindgen**, `web-sys`, `js-sys`, `serde-wasm-bindgen`, `wasm-pack`/`trunk`, `wasm-opt` (binaryen), `console_error_panic_hook`, `tracing-wasm`/`tracing-web` | `wasm-bindgen-rayon` for threads (needs COOP/COEP + nightly build-std atomics). |
| Server | **axum** (+ tower, tower-http, tokio), `sqlx` (Postgres/SQLite), `utoipa` (OpenAPI), `tower-sessions`/`axum-login`, `object_store` | REST + WebSocket (`axum::extract::ws`) for collab; `axum-extra`. |
| PDF | **printpdf** (simple pages/lines/curves, tiling), **pdf-writer** / **krilla** (typst crates, lower-level/modern, better text/fonts), **svg2pdf** (typst, via `usvg` tree) | For pattern printing you need: true 1:1 scale, A4/Letter tiling w/ registration marks and 1-in test square, A0 single-sheet for plotter/copyshop. Draw vector paths directly with `pdf-writer`/`krilla` for control; `svg2pdf` convenient when you already have SVG (fonts must be preloaded in `fontdb`). `resvg`/`usvg` for rasterising previews/thumbnails. |
| SVG | **svg** crate or `kurbo::BezPath::to_svg()` + hand templates | Write SVG layout export with `<path d>` per piece in layers (cut, SA, notch, grain, text). |
| DXF | **dxf** crate | AAMA/ASTM style output. |
| Nesting / marker making | custom no-fit-polygon in Rust w/ `i_overlay` + `geo`; or `jagua-rs` (Rust, 2D irregular strip packing; verify license/status), `sparrow` | Later feature. |
| Fonts/text (labels, in PDF) | `fontdb`, `ttf-parser`, `rustybuzz`, `cosmic-text` | |
| Expression eval | **evalexpr**, `fasteval`, `rhai` (scripting; heavier but powerful) | For user formulas. |
| Testing | `insta`, `proptest`, `approx`, `criterion` | |

### 3.1 WASM in-browser vs Tauri vs axum backend
Recommendation: **core as a pure Rust library (no I/O) compiled to BOTH WASM (browser) and native; run it in the browser as the default.**
- Interactive editing (dragging nodes, live dart/seam-allowance recompute, live block regen from measurement sliders, 3D drape) needs <16 ms loops; round-trips to a server would make it unusable. WASM runs the kernel locally, in a **Web Worker** (via `comlink`/`wasm-bindgen` + message passing) to keep UI responsive. Performance with kurbo/i_overlay in WASM is ~1.5-2x native; fine for patterns (hundreds of nodes) and mid-size cloth sims (≈ 2-10k vertices at 60 fps; larger with WASM SIMD + threads).
- WASM size: kurbo+geo+i_overlay+serde ≈ 400-900 KB gz after `opt-level=z`/`wasm-opt -Oz`+LTO; lyon+spade add ~150 KB. OK. Keep `printpdf/krilla` out of the main WASM (lazy-load a second module `export.wasm`, or do PDF on server) if size matters. PDF generation in WASM works (pdf-writer is pure Rust) but needs fonts bundled: ~100-300 KB.
- Server (axum): auth, projects/patterns storage (Postgres JSONB + object store for assets), sharing links, measurement profiles, marketplace, heavy/batch jobs (marker nesting, high-res PDF/DXF, server-side thumbnails, import/convert) and **the same core crate compiled natively** => parity & golden tests. Optionally compute authoritative PDF on server to guarantee fonts and consistent 1:1 scale.
- **Tauri**: only if you want an offline desktop edition (file access, native print, plotters/HPGL, USB). Because the core crate is shared, Tauri wraps the same web UI + native crate (no WASM required) -- low marginal cost, defer until demand. Don't choose Tauri-first: web distribution is the product advantage (links, no install, phones/tablets for measurement entry).
- JS side: **TypeScript + Svelte/React/Solid**, 2D editor canvas = **SVG for <1000 elements, or Canvas2D/PixiJS/WebGL for heavy**; hit-testing & snapping done in Rust (kurbo `nearest`) exposed as `hit_test(x,y,tol)`. Use **three.js** for 3D (below). UI state (selection, tool) in TS; **document state lives in Rust** (single source of truth; JS holds only an opaque handle + immutable view snapshots, serialised as JSON/typed arrays). Zero-copy transfer of vertex buffers by exposing `Float32Array` views onto WASM memory (`wasm-bindgen` `js_sys::Float32Array::view`) -- beware views invalidated by memory growth; copy per frame or reserve memory.

---------------------------------------------------------------------------
## 4. 3D visualisation

### 4.1 Pipeline
1. **Piece -> mesh (2D)**: flatten outline (kurbo) at tol 0.1 cm -> polygon (+holes for internal cutouts; darts closed or kept as geometry) -> **constrained Delaunay + refinement (spade)** with max edge length h (~1 cm for preview, 0.5 for hi-fi) -> triangle mesh with 2D rest positions `X_i ∈ R²` (these are the *material coordinates* and give UVs for fabric texture/grain direction `u` aligned with grain line).
2. **Seam constraints**: each seam = pair of edge ranges (A[sa..sb], B[sc..sd]) tagged by user or auto-detected from edge tags/ids (side seam F-B, shoulder F-B, armhole bodice-sleeve, inseam etc.) + ease ratio (if |A| ≠ |B|, distribute: sample both by arc-length fraction; the longer is gathered). Resample the boundary vertices on both sides at matching arc-length fractions, then add **zero-length-rest-length distance constraints** (stitches) between paired vertices, as soft constraint with stiffness ramp (stitches start with rest = initial gap then decrease to 0 over the "pull together" phase). Common technique: weld vertices after the garment is positioned (hard) or keep stitches as springs (soft, allows ease/gather).
3. **Initial placement**: place flat panels in 3D around mannequin: front panel at z = +offset (front), back at -offset, sleeves horizontal at arms (A-pose, 30-45° arms), each panel *curved* roughly cylinderwise onto an elliptical cross-section around the torso (map x by arc to angle on the body's cross-section ellipse at that height) so seams start close (≤ 5 cm). This "pre-wrap" step is crucial for convergence of sewing.
4. **Simulation** (below) with body collision against mannequin; export `positions: Float32Array`, `indices`, `uv` per frame to three.js: update `BufferGeometry` position attribute each frame, `computeVertexNormals()` (or compute normals in Rust).
5. Render: three.js `MeshStandardMaterial` with doubleSide, fabric normal/color map; ground shadow; OrbitControls; toggles: flat 2D overlay (UV grid), seam highlights (LineSegments), tension heatmap (vertex colors = strain/ease from constraint stretch), fit gap map (distance to body).

### 4.2 Parametric mannequin
- Body model: **cross-section based** ("lofted superellipse" dress form): list of ~20-30 horizontal slices at heights (neck, shoulder, armpit, bust, underbust, waist, high hip, hip, thigh, knee, ankle) each = closed curve (superellipse / Fourier / cubic loop) with params (width a, depth b, centre offset (cx,cz), shape exponent n) fitted so that **circumference** = measurements (use arc length of superellipse, solve for scale by 1-D root-finding), and widths determined from breadth/depth ratios (ratios from anthropometric defaults, adjustable). Arms: tapered ellipse-section generalized cylinders along a skeleton (shoulder-elbow-wrist) with U/Wr circumference. Neck/head: simple capsule. Legs: two lofts from crotch. Mesh by lofting (sweep) with cubic interpolation along height (Catmull-Rom or monotone cubic of each param vs height) -> triangle mesh; produce also **signed distance** approx for collision.
- Alternatives/upgrades: statistical body models (SMPL-X licence restrictive for commercial; **MakeHuman** CC0 targets; **MB-Lab**) -> morph targets driven by measurements; Anny (open, 2025, verify) / OpenAvatar; or user scanning later. Start with lofted dress form: deterministic, measurement-exact, tiny, fast collision.
- Collision representation for PBD: either (a) **analytic**: per-height-slice superellipse test: for particle p at height y, interpolate slice params, compute implicit `f(x,z)=|(x-cx)/a|^n + |(z-cz)/b|^n - 1`, push out along gradient to `f=1` + thickness; very cheap, O(1) per particle -- ideal for loft mannequins; (b) SDF grid on GPU/CPU (64³-128³, trilinear) for arbitrary meshes; (c) capsule/sphere approximations for arms. Use (a) for torso + (c) for arms/legs, (b) later.

### 4.3 Cloth sim: feasible in Rust/WASM? **Yes**
- **Position-Based Dynamics (PBD/XPBD)** is the right choice: unconditionally stable, simple, tiny code (~600-1000 LOC in Rust), supports distance (stretch), bending (dihedral or distance across opposite verts), stitch constraints, collision projection, and friction. XPBD (Macklin 2016) adds compliance independent of iteration count/time step: `Δλ = (−C − α̃λ)/(∑w|∇C|² + α̃)`, `α̃ = α/Δt²`.
- Particle count budget in WASM single-thread (scalar f32): ~10-20k particles at 30-60 fps w/ ~10 substeps×? Typical: 4 pieces + 2 sleeves @1 cm mesh ≈ 6-9k verts; 15 solver iterations each 1/60 s with 3 substeps => stretch constraints ≈ 25k edges -> ~ 1M constraint projections/frame: ~ 5-8 ms native; WASM ≈ 8-15 ms. OK. For heavier: enable `+simd128` target feature (`-C target-feature=+simd128`), constraint graph coloring + `wasm-bindgen-rayon` threads (SharedArrayBuffer; requires cross-origin isolation headers), or **WebGPU compute** (wgpu in Rust compiles to WebGPU/WebGL2; Jacobi/graph-colored GS) for >50k particles.
- Algorithm per frame (substep loop): predict `x* = x + dt v + dt² g`; project constraints (Gauss-Seidel over colored batches or sequential): distance (warp/weft/shear: use *triangle strain (Baraff-Witkin/StVK) constraints* for orthotropic fabric, or edges + shear diagonals), bending (dihedral angle XPBD or cheap "opposite vertex distance" with small stiffness), stitch distance constraints (rest 0, compliance ramped), body collision (project outside surface + friction μ≈0.3-0.6), self-collision (spatial hash on particles w/ thickness; start with only cross-piece or layer ordering; self-collision is the hard part -> limit to particle-particle min distance via hashed grid; optionally skip for 'preview'), then `v = (x - x_old)/dt` + damping (0.98).
- Fabric parameters: weight (g/m²) -> particle mass (area × density), stretch (warp/weft stiffness), shear, bend (drape coefficient), friction, thickness. Presets: cotton, denim, silk, knit (stretch 10-30%), linen.
- Phases: (1) **Stitching phase**: reduce stitch rest-lengths to zero over ~1-2 s, gravity off or low, body inflated by shrinking factor? ("body shrink then grow": start with mannequin scaled 0.9 and grow to 1.0 to avoid interpenetration). (2) **Drape phase**: gravity on, settle until kinetic energy < ε; then freeze and allow the user to tweak a parameter and re-settle ("ease preview"). (3) Optional: **strain map** = (current edge length / rest length - 1), shows tightness/ease; **fit analysis** = distance to body (gap), seam length mismatch warnings. Real-time slider -> re-run from previous state.
- Simplifications that matter: no need for physically accurate cloth; the product is *fit visualisation*. A static 'pre-wrap' + short sim (≤ 3 s settle) fits. 
- Risks: stitch convergence for complex (sleeve cap with ease, gathers); mesh-resolution mismatch between seam edges (resample or use matching vertices-by-arc-length); tangling at the armpit/crotch (use collision thickness + layered offsets, enforce sleeves inside-out orientation: normal side of fabric consistent, i.e. *"right side out"* seam normal checks); pins at body anchor (shoulders/neck, waist) as soft constraints to avoid sliding; thin triangles from ear-cut meshes (use spade refine). 
- Cost-benefit: Static (non-physical) wrap = 1-2 weeks; XPBD with analytic collision, stitches, 4-6 pieces = ~4-6 weeks incl. tuning; self-collision & fabric realism = open-ended. Prior art: Blender cloth (Mantle), Marvelous Designer/CLO (proprietary, FEM/PBD hybrid), Valentina has no 3D (Seamly3D roadmap), `bevy_silk`, `rust-cloth` demos, Matthias Müller "Ten Minute Physics" PBD tutorials (JS, easily ported), Macklin XPBD papers, "Cloth Simulation for Computer Graphics" (Tuur Stuyck). 
- Rust sim crate API sketch: `Sim::new(meshes, seams, body, params)`, `step(dt) -> StepStats`, `positions() -> &[f32]` (ptr + len exposed to JS), `set_param(k,v)`, `pin(idx, pos)`, `export_obj/glb`. 

### 4.4 three.js side
- `BufferGeometry` per piece (shared position buffer is single big `Float32Array` from WASM memory, pieces use draw ranges/groups). Normals computed in Rust each N frames or three's `computeVertexNormals()` (CPU cost fine up to 10k verts). UV = rest-state 2D coords/ fabric repeat (so woven texture follows grain). Fabric texture: PBR maps (albedo/normal/roughness) from CC0 libraries; `MeshPhysicalMaterial` with `sheen` for fabrics.
- Layers: mannequin (MeshStandardMaterial, matte), garment, seam LineSegments, annotation sprites (notches/labels), measurement ruler gizmo. Export: GLB via `GLTFExporter` (and in Rust `gltf-json`), USDZ later (AR on iOS), `<model-viewer>`.
- Performance: render only on dirty frames; sim in Worker w/ `SharedArrayBuffer` (if cross-origin isolated) else `postMessage` of transferable `Float32Array` (ping-pong double buffers).

---------------------------------------------------------------------------
## 5. Recommended architecture & repo layout

### 5.1 Architecture (diagram in words)
```
          ┌──────────── browser (TS UI, Svelte/React) ────────────┐
          │  2D editor (SVG/Canvas) │ 3D viewer (three.js) │ forms │
          │            ▲ typed JSON / Float32Array views           │
          │   Web Worker A: pattern-wasm (core+draft+export)       │
          │   Web Worker B: sim-wasm (cloth XPBD + mannequin)      │
          └───────▲───────────────────────────────▲────────────────┘
                  │ REST/WS (axum)                │ static assets (CDN)
          ┌───────┴────────────┐          ┌───────┴───────┐
          │ server (axum)      │          │ wasm + JS     │
          │ auth, storage,     │          └───────────────┘
          │ sharing, jobs,     │  uses same `core`, `draft`, `export` crates natively
          │ PDF/DXF, nesting   │
          └────────────────────┘          (optional: Tauri shell = same web UI + native core)
```
Principles: (1) **one geometry kernel, many hosts**; (2) document model is pure data + pure functions (deterministic, tested natively, run in WASM); (3) parametric *scripts* produce pieces; pieces are editable and operations are recorded; (4) simulation is a separate crate with no dependency on pattern editing, taking `TriMesh + seam pairs + body`; (5) all unit tests/golden files run natively in CI (`cargo test`), WASM smoke tests via `wasm-pack test --headless`.

### 5.2 Repo layout (Cargo workspace + pnpm workspace)
```
garmentcad/
├─ Cargo.toml                # workspace, resolver 2, profile.release opt-level="z" for wasm crates
├─ rust-toolchain.toml
├─ crates/
│  ├─ gc-core/               # data model (Pattern, Piece, Outline, Node, Notch, Dart, Grade), serde, ops, undo
│  ├─ gc-geom/               # kurbo/geo/i_overlay wrappers: flatten, arclen, offset, SA, boolean, hit-test, dart-fold
│  ├─ gc-draft/              # parametric blocks: DSL + expr eval, bodice/skirt/trouser/sleeve, constraint solver, size charts
│  ├─ gc-grade/              # grade rules, regrade, validation
│  ├─ gc-mesh/               # triangulation (spade/lyon), UVs, seam pairing, mannequin loft mesh
│  ├─ gc-sim/                # XPBD cloth, collision, stitches (no_std-friendly where possible, optional rayon)
│  ├─ gc-export/             # SVG, PDF (pdf-writer/krilla/printpdf), DXF, GLB; tiling, fonts
│  ├─ gc-wasm/               # wasm-bindgen façade (editor API) + tsify types; builds pkg to web/
│  ├─ gc-sim-wasm/           # wasm façade for sim worker (separate module → smaller main bundle)
│  ├─ gc-server/             # axum app: routes, auth, db (sqlx), jobs, openapi (utoipa)
│  ├─ gc-cli/                # `gc draft|grade|export|validate` headless; used in CI & golden tests
│  └─ gc-testdata/           # golden patterns, measurement fixtures, expected SVG
├─ apps/
│  ├─ web/                   # Vite + TS + Svelte/React; workers, three.js viewer, 2D editor, UI
│  └─ desktop/               # (later) Tauri 2 shell reusing apps/web + native crates
├─ packages/
│  ├─ schema/                # generated JSON-Schema + TS types (from schemars/tsify)
│  └─ ui-kit/                # shared components
├─ docs/                     # drafting-method specs (constants, sources), ADRs
├─ xtask/                    # build scripts: wasm-pack, wasm-opt, codegen, release
└─ .github/workflows/        # cargo test/clippy/fmt, wasm build, web e2e (Playwright), size budget
```
Build: `wasm-pack build crates/gc-wasm --target web` (or `cargo build --target wasm32-unknown-unknown` + `wasm-bindgen`), `wasm-opt -Oz`; Vite plugin `vite-plugin-wasm` + top-level-await. Feature flags: `gc-core` has `serde`, `ts`, `native-only`.

### 5.3 Build order / milestones
1. **M1 (2-4 wks)**: gc-geom + gc-core + basic Piece editing in browser, SVG/PDF 1:1 tiled export, seam allowance, notches, grainline. Immediately useful.
2. **M2 (3-5 wks)**: gc-draft with bodice/skirt/sleeve/trouser blocks + measurements form + validity checks; calibrate vs published blocks and physically toile one; dart rotation tools.
3. **M3 (2-3 wks)**: grading (regrade from blocks, point rules for imported), DXF I/O.
4. **M4 (4-6 wks)**: mannequin loft + spade meshing + static wrap view; then XPBD sewing/drape.
5. **M5**: accounts/cloud save, sharing, marketplace, nesting, Tauri.

### 5.4 Key risks & mitigations
- **Drafting correctness/IP**: formulas are method knowledge but book *tables/text* are copyrighted; implement own constants calibrated from measured fit, cite methods, avoid copying tables verbatim; prefer open references (FreeSewing designs are open source—check licences before reuse).
- Fit variance of generic blocks: expose ease/adjust sliders, toile workflow, and "alterations" ops (FBA/SBA, sway back, round back, broad shoulders -> slash & spread).
- Offset robustness: test with proptest (self-intersection, tiny arcs), always fall back to polygon offset + simplify.
- WASM memory/perf: Worker isolation, avoid cloning big structures across boundary (pass handles, typed arrays).
- 3D realism expectations: position as "fit/drape preview", not a CLO3D replacement; show strain/ease maps which are most useful for pattern makers.
