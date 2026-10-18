# Spec-driven garment drafters (`src/garments.rs`)

Drafts the two production pattern sets found in the sample Optitex files from
**finished-garment (spec / POM) measurements**, not body measurements.

| Garment | Sample | Pieces (qty, as in the XML) | Sizes | Base |
|---|---|---|---|---|
| `draft_shirt` | 52abc29d.xml, men's regular short-sleeve shirt 1078375 | FRT 2, back 1, back YK 2, CLR 1 (fold), BND TOP 1 (fold), BND IN 1 (fold), Sleeve 2 | S..3XL | L |
| `draft_pant_detailed` | 61dcbea7.xml, women's cross-pocket pant (CL1086464 / PDS 1074664) | WAIST- BELT, FRONT, BACK, PKT-IN, FACING, DRAWSTRING, FACING1 | XS..XL | S |

All lengths are cm; "half" means half-garment, as in the spec sheets.

## Method

1. **Anchor points** are `base + linear grade coefficient x spec delta`. The
   base is the sample base size (shirt L, pant S), so the default spec
   reproduces the sample exactly at base.
2. **Edge shapes** are digitised templates taken from the MARKER svg outlines
   (sew path, 100 units/cm). Each template is a chord plus (t, d) offsets, refit
   between the moved anchors (`tpl_line`, `tpl_sim`). The sleeve cap has its own
   depth scale. Bezier handles are Catmull-Rom, limited to a third of the
   adjacent segment; template points closer than 0.8 cm are dropped to avoid
   loops in the offset cut line.
3. **Pant leg widths** are piecewise linear in y from the hem/knee/thigh/seat
   control values. The crotch end point is found by bisection so the crotch arc
   length equals the spec rise (front arc = rise - waistband + 0.507,
   back = +0.333).
4. **Calibration** (documented, fitted to the XML grading): `K_THIGH 1.09`,
   `K_SEAT 0.55`, `K_KNEE 1.0`; pocket bag extents grow by x `4.0 x d(22145)`,
   y `2.08 x d(22165)`; FACING x `1.02 x d22145`, y `1.96 x d22165`; FACING1
   y `2.0 x d22165`, x constant. Shirt front/back chest and hem growth is split
   0.5 / 0.5.
5. Seams use the `sm()` tag pattern: shared tags per edge, `Seam` records for
   each join, fold seams (same piece and tag both sides, tag `cb`, SA 0) for
   CLR/BND TOP/BND IN. The shirt placket fold edge is tagged `placket_fold` so
   it is not treated as a fold piece.
6. Sleeve cap is split into `cap_front / cap_yoke / cap_back`; the band neck
   seam into `neck_back / neck_front`; belt waist into `waist_front /
   waist_back`; back outseam into `outseam_top` (pocket length) and `outseam`.

## Seam allowances

`GarmentOpts { sa: 1.0, shirt_hem: 3.5, sleeve_hem: 1.5, pant_hem: 1.5, sample_sa: true }`

With `sample_sa = true` the per-edge allowances measured from the sample are
used (e.g. shirt back side 1.7, FRT side 0.8, belt top 1.3, fold edges 0);
with `false` every edge gets `sa` except hems and folds.

## ShirtSpec (defaults = size L)

half_chest 61.12, half_hem 60.01, across_chest 49.78, across_back 48.10,
across_shoulder 51.93, body_length_hps 74.07, back_length_cb 75.53,
armhole_drop 25.98, shoulder_slope 6.39, shoulder_slope_back 4.71,
front_neck_width 8.62, back_neck_width 9.18, front_neck_depth 6.57,
back_neck_depth 5.23, yoke_depth 12.04, placket_width 3.5, hem_curve 1.30,
sleeve_length 26.50, bicep 21.93, sleeve_opening 19.915,
sleeve_underarm_height 9.99, neck_size 49.62, stand_height 3.31,
collar_height_cb 4.79, collar_point_length 6.007.

`ShirtSpec::from_map` takes normalised snake_case names plus aliases (`chest`,
`hem_sweep`, `body_length`, `collar_size`, `placket`, ...). Derived defaults:
back length follows body length, across chest/back follow across shoulder, neck
widths follow neck size at 0.2 per cm.

## PantSpec (defaults = size S of CL1086464.xlsx)

| Field | POM | Default |
|---|---|---|
| half_waist | 20125 | 35 |
| half_waist_stretched | 20245 | 49 |
| hip_pos_side / hip_pos_cf | 20305-A / 20305-B | 17 / 16 |
| half_seat | 20865 | 52 |
| thigh | 21505 | 33 |
| front_rise | 21545 | 30.5 |
| back_rise | 20905 | 41 |
| knee | 21125 | 30 |
| leg_opening | 21885 | 30 |
| hem_height | 30210 | 2.8 |
| inseam | 20265 | 78 |
| waistband_width | 22565 | 5.2 |
| pocket_opening_waist / _length | 22145 / 22165 | 3 / 15.5 |
| pocket_bag_depth | 30845 | 24 |
| drawcord_length | (name only) | 30 |

`PantSpec::from_pom` accepts POM codes, canonical names or aliases in one map;
missing keys give defaults; `from_pom_checked` also returns warnings for unknown
keys and non-finite values. `to_pom` / `to_map` round-trip.

Note: the POM code to field assignment for the less obvious rows (hip positions,
hem height, pocket bag) was inferred from the xlsx row order and the test
asserts the values of the S..XL columns; check codes against your own chart.

## Pieces, quantities, materials

Pair-cut pieces: qty 1 with `mirror = true` (export doubles them). Fold pieces
(CLR, BND TOP, BND IN, WAIST- BELT): qty as in the XML, `mirror = true`, fold edge
tag `cb` on x = 0. DRAWSTRING: qty 1, no mirror. `piece_meta(pattern)` returns
`PieceMeta { name, qty, material, half, rotation_ok, opposite }`; `half` is true
for HALF=CLOSE pieces (sample SIZE is the half piece, AREA/PERIM the closed one).
Grain lines are stored in `Piece.grain`.

## Achieved accuracy (diagnostic table, `cargo test -- --nocapture diagnostic`)

Compared against the XML GEOM_INFO for every piece and size: SIZE_X, SIZE_Y,
AREA, PERIMETER, SEW_AREA, SEW_PERIMETER. Errors in % of the XML.

| Piece | Worst SIZE_X/Y | Worst area | Worst cut perimeter | Worst sew area | Worst sew perimeter |
|---|---|---|---|---|---|
| FRT | 0.03 | +2.0 (3XL), base +0.1 | 0.0 | +2.2 (3XL) | 0.1 |
| back | 0.03 | +1.5 (3XL) | 0.0 | +1.5 | 0.0 |
| back YK | 0.12 | +0.5 | 0.2 | 0.6 | 0.2 |
| CLR | 0.14 | 0.8 | 0.2 | 1.4 | 0.2 |
| BND TOP / BND IN | 0.7 | 0.4 | 0.0 | 0.3 | 0.0 |
| Sleeve | 2.1 (Y, 3XL), base 0.0 | 1.1 | **+2.6** | 0.8 | 0.8 |
| WAIST- BELT | 0.00 | 0.0 | 0.0 | 0.0 | 0.0 |
| FRONT | 0.33 | 0.9 | 0.5 | 0.9 | 0.5 |
| BACK | 0.29 | 0.3 | 0.1 | 0.3 | 0.1 |
| PKT-IN | 0.06 | 1.3 | 0.8 | 1.5 | 0.9 |
| FACING | 1.2 | 1.7 | 1.0 | 2.3 | 0.1 |
| FACING1 | 1.2 | 3.9 | 1.1 | **5.1** (XL) | 0.1 |
| DRAWSTRING | 0 | 0 | 0 | n/a | n/a |

Base sizes: main pieces within 0.3 % in every metric; sew dimensions of all
pieces are within the requested 3 % at every size.

## Honest limitations

* **Sleeve cut perimeter is +2.1..2.6 % high** at every size (the offset
  miter geometry on the cap differs from Optitex); sew perimeter is within
  0.8 %. Sleeve SIZE_Y is -1.1..+2.1 % at the extremes.
* **FACING / FACING1** are small curved pieces: extents 1.2 % short, FACING1 area
  up to -3.9 % and sew area -5.1 % at XL. FRT area is +2 % at 3XL.
* **The shirt has no spec chart.** The shirt size columns in the tests are implied
  from the XML's own grading increments, so the shirt grading result is
  circular (it proves the model can reproduce the XML, not that the spec
  to pattern mapping is independent). The pant columns come from the xlsx.
* Pant growth coefficients above are fitted to the XML. The PDS pant 1074664 and
  the xlsx CL1086464 are the same family but increments differ slightly
  (front SIZE_X deltas 2.0, 2.3, 2.3, 2.29 in the XML vs 2.0, 2.0, 2.3, 2.3 from
  the chart); that is why FRONT drifts -0.3 % from M up.
* Sample sew widths differ slightly from POM values (leg opening sew 30.55 vs
  spec 30, thigh 33.6 vs 33); the drafter reproduces the sample, not the POM.
* Seam lengths are not all equal in the sample either: collar neckseam 22.74 vs
  band top 21.55; belt 51.5 vs gathered waist 45.7. The pairing of back
  `outseam_top` with PKT-IN opening (16.0 vs 26.0) is inferred.
* Sleeve cap ease is 3.93 cm, matching the sample.
* `opposite` in `PieceMeta` is by piece name; there is no per-piece rotation data.

## API

```rust
pub struct GarmentOpts { pub sa: f64, pub shirt_hem: f64, pub sleeve_hem: f64, pub pant_hem: f64, pub sample_sa: bool }
pub struct ShirtSpec { /* 25 f64 fields */ }
pub struct PantSpec  { /* 17 f64 fields */ }
impl ShirtSpec { fn from_map(&BTreeMap<String,f64>) -> Self; fn from_map_checked(..) -> (Self, Vec<String>);
                 fn to_map(&self); fn get(&self,&str)->Option<f64>; fn set(&mut self,&str,f64)->bool;
                 fn validate(&self)->Result<(),String>; fn field_names()->Vec<&'static str> }
impl PantSpec  { fn from_pom(&BTreeMap<String,f64>) -> Self; fn from_pom_checked(..) -> (Self, Vec<String>);
                 fn to_pom(&self); fn to_map(&self); fn get; fn set; fn validate; fn field_names }
pub fn draft_shirt(&ShirtSpec, &GarmentOpts) -> Result<Pattern,String>;
pub fn draft_pant_detailed(&PantSpec, &GarmentOpts) -> Result<Pattern,String>;   // alias draft_pant
pub fn check_pattern(&Pattern) -> Result<(),String>;
pub struct PieceMeta { name, qty, material, half, rotation_ok, opposite }
pub fn piece_meta(&Pattern) -> Vec<PieceMeta>;
pub fn grade_garment(kind:&str, base:&BTreeMap<String,f64>, per_size:&[(String,BTreeMap<String,f64>)]) -> Result<Vec<(String,Pattern)>,String>;
pub fn grade_garment_opts(.., &GarmentOpts) -> ..;
pub struct GeomInfo; pub fn geom_info(&Piece) -> GeomInfo; pub fn garment_checks(&Pattern) -> Vec<Check>;
pub mod reference { SHIRT_REF, PANT_REF, SHIRT_SIZES, PANT_SIZES }   // XML GEOM_INFO data
```

`grade_garment` kinds: `shirt`, `pant` (alias `trousers`). Each size's map is
laid over `base`, which is laid over the sample defaults; the shirt keys are
snake_case names, the pant keys POM codes or names.
