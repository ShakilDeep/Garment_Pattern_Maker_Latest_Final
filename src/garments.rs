//! Spec-driven garment drafters that reproduce the production pattern sets found in two
//! real Optitex files: the men's regular short-sleeve shirt 1078375 and the women's
//! cross-pocket pant 1074664 (see `docs/GARMENTS.md`).
//!
//! Unlike `draft.rs` (body measurements -> block), everything here is driven by
//! FINISHED-GARMENT measurements (spec / POM values, cm, half-garment where the chart says
//! half).  Each piece is built from a handful of *anchor points* whose positions are linear
//! functions of the spec, joined by edge shapes (curves) that were digitised from the real
//! marker outlines and are re-fitted between the moving anchors.  At the default spec the
//! anchors sit exactly on the sample's sew-line vertices, so the base size reproduces the
//! production piece; other sizes are obtained by moving the anchors (spec increments).
//!
//! Conventions (same as `model.rs`): cm, y up, grain vertical.  Fold pieces ("HALF=CLOSE" in
//! the XML) are drawn as ONE half with a fold edge tagged `cb` (x = 0) and joined to
//! themselves by a fold seam.  Pieces that the sample cuts as an L/R pair use `mirror = true`
//! and `qty = XML quantity / 2`, so `export::dxf_aama` (which doubles mirrored pieces)
//! reports the sample quantity.  `piece_meta` returns the sample quantities directly.
use crate::draft::Check;
use crate::geom::*;
use crate::model::*;
use std::collections::BTreeMap;

// ---------------------------------------------------------------------------------------
// edge-shape templates (digitised from the marker outlines, see docs/GARMENTS.md)
// ---------------------------------------------------------------------------------------

/// Interior points of an edge expressed in the frame of its chord: `t` = fraction of the
/// chord length along the chord, `d` = offset (cm, at the sample size) to the LEFT of the
/// chord direction.  `base` = chord length at the sample size.
#[derive(Clone, Copy)]
struct Tpl {
    base: f64,
    pts: &'static [(f64, f64)],
}

const MIN_PT_GAP: f64 = 0.8;

/// Full point list (start anchor, interior, end anchor); `rd` scales the offsets.
fn tpl_line(a: V2, b: V2, t: &Tpl, rd: f64) -> Vec<V2> {
    let ch = b - a;
    let l = ch.len();
    let u = ch.norm();
    let n = u.perp();
    let mut v = vec![a];
    for &(tt, d) in t.pts {
        let p = a + u * (tt * l) + n * (d * rd);
        // drop digitised points that crowd an end anchor (they create sub-allowance loops in the cut line)
        if p.dist(*v.last().unwrap()) >= MIN_PT_GAP && p.dist(b) >= MIN_PT_GAP {
            v.push(p);
        }
    }
    v.push(b);
    v
}
/// Similarity scaling: offsets follow the chord length.
fn tpl_sim(a: V2, b: V2, t: &Tpl) -> Vec<V2> {
    tpl_line(a, b, t, (b - a).len() / t.base)
}

/// Tiny stub edge length that replaces a "folded mitre" corner (see `fold_corner_in/out`).
const STUB_EPS: f64 = 0.04;

/// Optitex cuff corners are not plain mitres: the cut line follows the side seam's offset line up
/// to the hem SEW line and is mirrored back out to the hem offset line (a folded mitre; measured on
/// the sleeve of the sample: the bevel line lies exactly one side-seam allowance from the corner
/// and runs along the mirror image of the side edge).  The offset routine of this crate can
/// only mitre or bevel, so the corner vertex is replaced by a stub edge of length ~STUB_EPS that is
/// parallel to that bevel line and carries the side allowance; its offset line IS the bevel.
/// Side edge arrives at `a` (from `prev`), hem leaves towards `next`.  Returns the stub ends.
fn fold_corner_in(prev: V2, a: V2, next: V2) -> Option<(V2, V2)> {
    let c = (a - prev).norm();
    let h = (next - a).norm();
    let cr = h * (2.0 * c.dot(h)) - c; // c mirrored about the hem line
    let den = h.cross(cr);
    if den.abs() < 1e-9 {
        return None;
    }
    let d2 = -STUB_EPS * c.cross(cr) / den;
    if !(d2 > 1e-6) {
        return None;
    }
    Some((a - c * STUB_EPS, a + h * d2))
}
/// Hem arrives at `a` (from `prev`), the side edge leaves towards `next`.
fn fold_corner_out(prev: V2, a: V2, next: V2) -> Option<(V2, V2)> {
    let h = (a - prev).norm();
    let d = (next - a).norm();
    let ur = h * (2.0 * d.dot(h)) - d;
    let den = h.cross(ur);
    if den.abs() < 1e-9 {
        return None;
    }
    let dh = -STUB_EPS * d.cross(ur) / den;
    if !(dh > 1e-6) {
        return None;
    }
    Some((a - h * dh, a + d * STUB_EPS))
}


const T_FRT_HEM: Tpl = Tpl { base: 30.8370, pts: &[(0.21059, -0.2819), (0.38894, -0.4021), (0.56745, -0.4024), (0.7783, -0.2542)] };
const T_FRT_ARMHOLE: Tpl = Tpl { base: 20.6308, pts: &[(0.02134, 0.8867), (0.04652, 1.7577), (0.07614, 2.5563), (0.11146, 3.2635), (0.15093, 3.8476), (0.19455, 4.277), (0.24172, 4.5769), (0.31466, 4.7961), (0.38777, 4.7718), (0.46015, 4.5736), (0.55463, 4.0983), (0.67016, 3.3111), (0.75977, 2.5636), (0.8689, 1.4725)] };
const T_FRT_NECK: Tpl = Tpl { base: 9.6148, pts: &[(0.13818, 0.6878), (0.28328, 1.2859), (0.38455, 1.5799), (0.4892, 1.7476), (0.59362, 1.7667), (0.69569, 1.6153), (0.79469, 1.2859), (0.88687, 0.7988)] };
const T_BACK_HEM: Tpl = Tpl { base: 29.2289, pts: &[(0.2051, -0.2469), (0.39328, -0.3616), (0.58132, -0.3461), (0.82096, -0.1774)] };
const T_BACK_ARMHOLE: Tpl = Tpl { base: 15.4164, pts: &[(0.04054, 0.7843), (0.08674, 1.4907), (0.14042, 2.0543), (0.20014, 2.4731), (0.263, 2.7434), (0.32755, 2.8633), (0.4256, 2.8204), (0.52186, 2.5732), (0.64705, 2.0405), (0.82985, 1.0352)] };
const T_YOKE_ARMHOLE: Tpl = Tpl { base: 12.7219, pts: &[(0.27445, 0.261), (0.54928, 0.3609), (0.68434, 0.3758)] };
const T_YOKE_NECK: Tpl = Tpl { base: 10.5653, pts: &[(0.10765, 0.9863), (0.18318, 1.579), (0.26542, 2.0738), (0.35519, 2.3851), (0.45004, 2.4471), (0.54457, 2.281), (0.67753, 1.7569), (0.9308, 0.3935)] };
const T_COLLAR_NECKSEAM: Tpl = Tpl { base: 22.7296, pts: &[(0.24175, -0.2407), (0.4618, -0.3361), (0.68172, -0.2912), (0.94569, -0.0571)] };
const T_COLLAR_OUTER: Tpl = Tpl { base: 21.4960, pts: &[(0.18514, 0.3691), (0.34803, 0.5871), (0.51076, 0.6747), (0.65021, 0.5932), (0.84346, 0.3208)] };
const T_BAND_NECKSEAM: Tpl = Tpl { base: 24.6271, pts: &[(0.22103, -0.7164), (0.36287, -1.0837), (0.48439, -1.2785), (0.58586, -1.322), (0.68727, -1.2341), (0.78839, -0.9835), (0.88871, -0.5886)] };
const T_BAND_END: Tpl = Tpl { base: 3.6702, pts: &[(0.10097, -0.3389), (0.32573, -0.9096), (0.59216, -1.1053), (0.8283, -0.6347)] };
const T_BAND_TOP: Tpl = Tpl { base: 21.4902, pts: &[(0.16194, 0.3846), (0.32453, 0.6168), (0.4873, 0.6977), (0.65022, 0.6175), (0.81296, 0.4069)] };
const T_SLEEVE_UNDER_L: Tpl = Tpl { base: 8.4275, pts: &[(0.41536, -0.1299), (0.71217, -0.1251)] };
const T_SLEEVE_CAP: Tpl = Tpl { base: 43.8600, pts: &[(0.03169, 0.61), (0.06156, 1.31), (0.08846, 2.17), (0.11286, 3.18), (0.14227, 4.71), (0.17579, 6.8), (0.22116, 9.82), (0.24875, 11.46), (0.27132, 12.6), (0.29571, 13.63), (0.32285, 14.51), (0.35271, 15.24), (0.38486, 15.8), (0.4186, 16.19), (0.45326, 16.43), (0.4886, 16.51), (0.52394, 16.42), (0.5586, 16.18), (0.59234, 15.79), (0.62449, 15.24), (0.65481, 14.54), (0.68285, 13.69), (0.70839, 12.71), (0.7394, 11.24), (0.77474, 9.22), (0.82923, 5.89), (0.85796, 4.31), (0.88919, 2.89), (0.91518, 1.95), (0.94368, 1.16), (0.98472, 0.29)] };
const T_SLEEVE_UNDER_R: Tpl = Tpl { base: 8.4243, pts: &[(0.29656, -0.1246), (0.65166, -0.116)] };
const T_PF_INSEAM: Tpl = Tpl { base: 80.9455, pts: &[(0.03508, -0.053), (0.2883, -0.401), (0.45508, -0.5278), (0.59716, -0.5114), (0.77015, -0.344)] };
const T_PF_CROTCH: Tpl = Tpl { base: 24.8287, pts: &[(0.00892, -0.4483), (0.03557, -1.2047), (0.06975, -1.7554), (0.10776, -2.0964), (0.14761, -2.2364), (0.2285, -2.1659), (0.41181, -1.7172)] };
const T_PB_INSEAM: Tpl = Tpl { base: 80.7057, pts: &[(0.03521, -0.2487), (0.52581, -1.9387), (0.59391, -2.1466), (0.64339, -2.1911), (0.69914, -2.1001), (0.76727, -1.8476), (0.82902, -1.4898), (0.88451, -1.0273), (0.97071, -0.2252)] };
const T_PB_CROTCH: Tpl = Tpl { base: 32.4851, pts: &[(0.03408, -1.667), (0.06229, -2.86), (0.0936, -3.9613), (0.12901, -4.9225), (0.16866, -5.7079), (0.19689, -6.1046), (0.22685, -6.3863), (0.27257, -6.5813), (0.31887, -6.5352), (0.38007, -6.2496), (0.45965, -5.6824), (0.51262, -5.1581)] };
const PF_OUTSEAM: &[(f64, f64)] = &[(29.860, 90.800), (29.160, 56.810), (28.990, 43.310), (28.940, 28.810), (28.960, 3.810), (28.950, 0.020)];
const PB_OUTSEAM: &[(f64, f64)] = &[(38.820, 106.300), (37.790, 81.320), (37.470, 70.820), (37.240, 58.820), (37.110, 44.320), (37.060, 20.320), (37.030, 0.000)];
const PKT_IN_POLY: &[(f64, f64)] = &[(32.260, 25.080), (32.520, 18.580), (32.590, 14.080), (32.510, 7.080), (32.430, 3.370), (31.440, 3.210), (30.480, 2.940), (29.180, 2.210), (27.910, 1.380), (26.570, 0.700), (25.630, 0.390), (24.160, 0.140), (21.630, 0.020), (17.620, 0.000), (14.640, 0.100), (10.140, 0.440), (8.130, 0.670), (6.680, 1.010), (5.750, 1.370), (4.460, 2.130), (2.840, 3.350), (2.000, 3.870), (1.080, 4.220), (0.000, 4.470), (0.320, 10.660), (6.360, 25.480), (10.330, 24.870), (13.320, 24.520), (15.810, 24.360), (18.300, 24.360), (27.790, 24.780)];
const FACING_POLY: &[(f64, f64)] = &[(4.920, 0.000), (0.000, 22.850), (5.490, 23.140), (8.740, 23.360), (8.990, 16.870), (9.070, 11.870), (8.990, 4.870), (8.920, 1.650), (7.920, 1.500), (6.970, 1.220), (5.670, 0.480)];
const FACING1_POLY: &[(f64, f64)] = &[(7.100, 0.000), (0.000, 21.380), (3.110, 21.540), (8.160, 6.350), (8.040, 0.140)];

// ---------------------------------------------------------------------------------------
// options & specs
// ---------------------------------------------------------------------------------------

/// Construction options shared by the spec drafters.
#[derive(Clone, Debug)]
pub struct GarmentOpts {
    /// General seam allowance (cm).
    pub sa: f64,
    /// Shirt body hem allowance (sample: 3.5).
    pub shirt_hem: f64,
    /// Sleeve hem allowance (sample: 1.5).
    pub sleeve_hem: f64,
    /// Pant leg hem allowance (sample: 1.5).
    pub pant_hem: f64,
    /// Re-apply the per-edge allowances measured from the sample's cut vs sew outlines
    /// (front side 0.8 / back side 1.7 / sleeve cap 2.0 / collar 1.3 / belt 1.3 ...).
    /// `false` = uniform `sa` everywhere except hems and folds.
    pub sample_sa: bool,
}
impl Default for GarmentOpts {
    fn default() -> Self {
        GarmentOpts { sa: 1.0, shirt_hem: 3.5, sleeve_hem: 1.5, pant_hem: 1.5, sample_sa: true }
    }
}

/// Normalise a spec key: lower case, every run of non-alphanumerics becomes `_`.
pub fn norm_key(s: &str) -> String {
    let mut out = String::new();
    let mut last_us = true;
    for c in s.trim().chars() {
        if c.is_ascii_alphanumeric() {
            out.push(c.to_ascii_lowercase());
            last_us = false;
        } else if !last_us {
            out.push('_');
            last_us = true;
        }
    }
    while out.ends_with('_') {
        out.pop();
    }
    out
}

fn bad(v: f64) -> bool {
    !v.is_finite()
}

/// Finished-garment spec of the men's regular short-sleeve shirt (cm).  `Default` is the
/// sample's base size L (values read from the sew lines of the L marker; the tech pack of
/// style 1078375 carries no measurement chart).  Widths marked "half" are flat half
/// measurements; `bicep` and `sleeve_opening` are flat halves too (the sleeve pattern is 2x).
#[derive(Clone, Debug, PartialEq)]
pub struct ShirtSpec {
    /// Chest, half, at the underarm point (front + back).
    pub half_chest: f64,
    /// Hem sweep, half, along the sew line (front + back).
    pub half_hem: f64,
    /// Front armhole-top to armhole-top (full) = twice the front shoulder-tip distance from CF.
    pub across_chest: f64,
    /// Back across the yoke seam / back armhole top (full).
    pub across_back: f64,
    /// Shoulder tip to shoulder tip (full).
    pub across_shoulder: f64,
    /// Front body length HPS to hem at CF (sew lines, excl. hem allowance).
    pub body_length_hps: f64,
    /// Back length at CB, neck seam to hem (sew lines).
    pub back_length_cb: f64,
    /// HPS down to the underarm point.
    pub armhole_drop: f64,
    /// Front shoulder drop, HPS to shoulder tip.
    pub shoulder_slope: f64,
    /// Back (yoke) shoulder drop.
    pub shoulder_slope_back: f64,
    /// Neck width HPS to CF (half of the front neck opening).
    pub front_neck_width: f64,
    /// Neck width HPS to CB.
    pub back_neck_width: f64,
    pub front_neck_depth: f64,
    pub back_neck_depth: f64,
    /// Yoke depth at CB.
    pub yoke_depth: f64,
    /// Finished placket width (tech pack: 3.5); the sew-line extension is 0.3 less.
    pub placket_width: f64,
    /// Rise of the hem toward the side seam (curved hem).
    pub hem_curve: f64,
    /// Sleeve length: hem line to the crest of the cap (sew lines).
    pub sleeve_length: f64,
    /// Bicep / muscle, flat half (pattern width at the bicep line = 2x).
    pub bicep: f64,
    /// Sleeve opening, flat half.
    pub sleeve_opening: f64,
    /// Height of the bicep line above the sleeve hem (underarm sleeve length).
    pub sleeve_underarm_height: f64,
    /// Neck / collar size: full length of the stand along the neck seam.
    pub neck_size: f64,
    /// Stand height at CB.
    pub stand_height: f64,
    /// Collar height at CB.
    pub collar_height_cb: f64,
    /// Collar point length.
    pub collar_point_length: f64,
}

impl Default for ShirtSpec {
    fn default() -> Self {
        ShirtSpec {
            half_chest: 61.12,
            half_hem: 60.01,
            across_chest: 49.78,
            across_back: 48.10,
            across_shoulder: 51.93,
            body_length_hps: 74.07,
            back_length_cb: 75.53,
            armhole_drop: 25.98,
            shoulder_slope: 6.39,
            shoulder_slope_back: 4.71,
            front_neck_width: 8.62,
            back_neck_width: 9.18,
            front_neck_depth: 6.57,
            back_neck_depth: 5.23,
            yoke_depth: 12.04,
            placket_width: 3.5,
            hem_curve: 1.30,
            sleeve_length: 26.50,
            bicep: 21.93,
            sleeve_opening: 19.915,
            sleeve_underarm_height: 9.99,
            neck_size: 49.62,
            stand_height: 3.31,
            collar_height_cb: 4.79,
            collar_point_length: 6.007,
        }
    }
}

/// Half-length of the sample's collar band top seam (cm); pairs with the sample `neck_size` 49.62.
const SAMPLE_BAND_HALF: f64 = 21.55;
/// Sleeve length (cm) from which the sleeve is treated as a long sleeve (underarm seam follows the length).
const LONG_SLEEVE: f64 = 40.0;

const SHIRT_ALIASES: &[(&str, &str)] = &[
    ("chest", "half_chest"), ("half_chest", "half_chest"), ("1_2_chest", "half_chest"), ("chest_half", "half_chest"),
    ("hem", "half_hem"), ("hem_sweep", "half_hem"), ("half_hem", "half_hem"), ("bottom_opening", "half_hem"), ("sweep", "half_hem"),
    ("across_chest", "across_chest"), ("across_back", "across_back"),
    ("across_shoulder", "across_shoulder"), ("shoulder", "across_shoulder"), ("shoulder_width", "across_shoulder"),
    ("body_length", "body_length_hps"), ("body_length_hps", "body_length_hps"), ("length_hps", "body_length_hps"), ("hps_length", "body_length_hps"), ("length", "body_length_hps"),
    ("back_length", "back_length_cb"), ("back_length_cb", "back_length_cb"), ("cb_length", "back_length_cb"),
    ("armhole_drop", "armhole_drop"), ("armhole_depth", "armhole_drop"),
    ("shoulder_slope", "shoulder_slope"), ("slope", "shoulder_slope"), ("shoulder_slope_back", "shoulder_slope_back"),
    ("front_neck_width", "front_neck_width"), ("back_neck_width", "back_neck_width"), ("neck_width", "back_neck_width"),
    ("front_neck_depth", "front_neck_depth"), ("back_neck_depth", "back_neck_depth"), ("neck_drop", "front_neck_depth"),
    ("yoke", "yoke_depth"), ("yoke_depth", "yoke_depth"), ("yoke_height", "yoke_depth"),
    ("placket", "placket_width"), ("placket_width", "placket_width"),
    ("hem_curve", "hem_curve"),
    ("sleeve", "sleeve_length"), ("sleeve_length", "sleeve_length"),
    ("bicep", "bicep"), ("muscle", "bicep"), ("sleeve_width", "bicep"),
    ("cuff", "sleeve_opening"), ("sleeve_opening", "sleeve_opening"), ("cuff_opening", "sleeve_opening"),
    ("sleeve_underarm_height", "sleeve_underarm_height"), ("sleeve_inseam", "sleeve_underarm_height"),
    ("neck", "neck_size"), ("collar", "neck_size"), ("collar_size", "neck_size"), ("neck_size", "neck_size"),
    ("stand", "stand_height"), ("stand_height", "stand_height"), ("collar_stand", "stand_height"),
    ("collar_height", "collar_height_cb"), ("collar_height_cb", "collar_height_cb"),
    ("collar_point", "collar_point_length"), ("collar_point_length", "collar_point_length"),
    // canonical names produced by the spec importer (spec.rs)
    ("half_bicep", "bicep"), ("collar_stand_height", "stand_height"), ("shoulder_drop", "shoulder_slope"),
    ("half_sleeve_opening", "sleeve_opening"), ("armhole", "armhole_drop"),
];

impl ShirtSpec {
    fn slots(&mut self) -> Vec<(&'static str, &mut f64)> {
        vec![
            ("half_chest", &mut self.half_chest), ("half_hem", &mut self.half_hem),
            ("across_chest", &mut self.across_chest), ("across_back", &mut self.across_back),
            ("across_shoulder", &mut self.across_shoulder), ("body_length_hps", &mut self.body_length_hps),
            ("back_length_cb", &mut self.back_length_cb), ("armhole_drop", &mut self.armhole_drop),
            ("shoulder_slope", &mut self.shoulder_slope), ("shoulder_slope_back", &mut self.shoulder_slope_back),
            ("front_neck_width", &mut self.front_neck_width), ("back_neck_width", &mut self.back_neck_width),
            ("front_neck_depth", &mut self.front_neck_depth), ("back_neck_depth", &mut self.back_neck_depth),
            ("yoke_depth", &mut self.yoke_depth), ("placket_width", &mut self.placket_width),
            ("hem_curve", &mut self.hem_curve), ("sleeve_length", &mut self.sleeve_length),
            ("bicep", &mut self.bicep), ("sleeve_opening", &mut self.sleeve_opening),
            ("sleeve_underarm_height", &mut self.sleeve_underarm_height), ("neck_size", &mut self.neck_size),
            ("stand_height", &mut self.stand_height), ("collar_height_cb", &mut self.collar_height_cb),
            ("collar_point_length", &mut self.collar_point_length),
        ]
    }
    /// Canonical field names in declaration order.
    pub fn field_names() -> Vec<&'static str> {
        ShirtSpec::default().slots().into_iter().map(|(n, _)| n).collect()
    }
    pub fn get(&self, key: &str) -> Option<f64> {
        let mut c = self.clone();
        let k = Self::canon(key)?;
        c.slots().into_iter().find(|(n, _)| *n == k).map(|(_, v)| *v)
    }
    pub fn set(&mut self, key: &str, v: f64) -> bool {
        let Some(k) = Self::canon(key) else { return false };
        for (n, r) in self.slots() {
            if n == k {
                *r = v;
                return true;
            }
        }
        false
    }
    fn canon(key: &str) -> Option<&'static str> {
        let k = norm_key(key);
        SHIRT_ALIASES.iter().find(|(a, _)| *a == k).map(|(_, f)| *f)
    }
    /// Canonical name -> value map (round-trips through `from_map`).
    pub fn to_map(&self) -> BTreeMap<String, f64> {
        let mut c = self.clone();
        c.slots().into_iter().map(|(n, v)| (n.to_string(), *v)).collect()
    }
    /// Build from a map keyed by normalised snake_case names (aliases such as `chest`, `hem_sweep`,
    /// `muscle`, `collar_size` are accepted).  Missing keys keep the sample (size L) defaults, except
    /// that a few dependent quantities follow their driver when they are not given themselves:
    /// `back_length_cb` follows `body_length_hps`; `across_chest`/`across_back` follow
    /// `across_shoulder`; the neck widths follow `neck_size` (0.2 cm per cm of neck size).
    /// Unknown or non-finite entries are ignored (see `from_map_checked`).
    pub fn from_map(m: &BTreeMap<String, f64>) -> ShirtSpec {
        Self::from_map_checked(m).0
    }
    pub fn from_map_checked(m: &BTreeMap<String, f64>) -> (ShirtSpec, Vec<String>) {
        let d = ShirtSpec::default();
        let mut s = d.clone();
        let mut warn = Vec::new();
        let mut given: Vec<&'static str> = Vec::new();
        let mut cap_height: Option<f64> = None;
        for (k, v) in m {
            // derived quantities that are not a 1:1 field (see docs/SHIRT-CHART.md)
            match (norm_key(k).as_str(), v.is_finite()) {
                ("neck_width", true) | ("neck_width_full", true) => {
                    // chart value is the full HPS-to-HPS opening; the drafter uses half-widths
                    s.front_neck_width = *v / 2.0;
                    s.back_neck_width = *v / 2.0 + (d.back_neck_width - d.front_neck_width);
                    given.push("front_neck_width"); given.push("back_neck_width");
                    continue;
                }
                ("cuff_opening_full", true) => {
                    // chart value is the full cuff edge-to-edge; the drafter's sleeve opening is a half-width
                    s.sleeve_opening = *v / 2.0;
                    given.push("sleeve_opening");
                    continue;
                }
                ("sleeve_cap_height", true) => {
                    cap_height = Some(*v);
                    continue;
                }
                ("collar_length", true) | ("collar_half_length", true) => {
                    // half collar-band length (collar buttoned). Calibrated on the sample: band top half-length
                    // 21.55 cm <-> neck_size 49.62.
                    s.neck_size = 2.0 * *v + (d.neck_size - 2.0 * SAMPLE_BAND_HALF);
                    given.push("neck_size");
                    continue;
                }
                _ => {}
            }
            match Self::canon(k) {
                Some(f) if v.is_finite() => {
                    s.set(f, *v);
                    given.push(f);
                }
                Some(_) => warn.push(format!("non-finite value for '{}' ignored", k)),
                None => warn.push(format!("unknown shirt spec key '{}' ignored", k)),
            }
        }
        let has = |n: &str| given.contains(&n);
        // the sleeve cap keeps its height: the underarm seam is what grows with the sleeve length
        // (long sleeves; short sleeves keep the sample underarm height unless the cap height is given)
        if let Some(ch) = cap_height {
            if !has("sleeve_underarm_height") { s.sleeve_underarm_height = (s.sleeve_length - ch).max(5.0); }
        } else if has("sleeve_length") && !has("sleeve_underarm_height") && s.sleeve_length >= LONG_SLEEVE {
            s.sleeve_underarm_height = s.sleeve_length - (d.sleeve_length - d.sleeve_underarm_height);
        }
        if has("body_length_hps") && !has("back_length_cb") {
            s.back_length_cb = d.back_length_cb + (s.body_length_hps - d.body_length_hps);
        }
        if has("across_shoulder") {
            if !has("across_chest") { s.across_chest = d.across_chest + (s.across_shoulder - d.across_shoulder); }
            if !has("across_back") { s.across_back = d.across_back + (s.across_shoulder - d.across_shoulder); }
        }
        if has("neck_size") {
            let dn = 0.2 * (s.neck_size - d.neck_size);
            if !has("front_neck_width") { s.front_neck_width = d.front_neck_width + dn; }
            if !has("back_neck_width") { s.back_neck_width = d.back_neck_width + dn; }
        }
        (s, warn)
    }
    pub fn validate(&self) -> Result<(), String> {
        let mut c = self.clone();
        for (n, v) in c.slots() {
            if bad(*v) || *v <= 0.0 {
                return Err(format!("shirt spec '{}' must be a positive finite number (got {})", n, v));
            }
        }
        let r = |n: &str, v: f64, lo: f64, hi: f64| -> Result<(), String> {
            if v < lo || v > hi { Err(format!("shirt spec '{}' = {} outside the supported range {}..{} cm", n, v, lo, hi)) } else { Ok(()) }
        };
        r("half_chest", self.half_chest, 35.0, 90.0)?;
        r("half_hem", self.half_hem, 35.0, 90.0)?;
        r("across_shoulder", self.across_shoulder, 30.0, 70.0)?;
        r("across_chest", self.across_chest, 28.0, 70.0)?;
        r("across_back", self.across_back, 28.0, 70.0)?;
        r("body_length_hps", self.body_length_hps, 45.0, 110.0)?;
        r("back_length_cb", self.back_length_cb, 45.0, 115.0)?;
        r("armhole_drop", self.armhole_drop, 15.0, 40.0)?;
        r("shoulder_slope", self.shoulder_slope, 1.0, 12.0)?;
        r("shoulder_slope_back", self.shoulder_slope_back, 0.5, 12.0)?;
        r("front_neck_width", self.front_neck_width, 5.0, 14.0)?;
        r("back_neck_width", self.back_neck_width, 5.0, 14.0)?;
        r("front_neck_depth", self.front_neck_depth, 3.0, 14.0)?;
        r("back_neck_depth", self.back_neck_depth, 1.0, 10.0)?;
        r("yoke_depth", self.yoke_depth, 6.0, 25.0)?;
        r("placket_width", self.placket_width, 1.5, 6.0)?;
        r("hem_curve", self.hem_curve, 0.0, 4.0)?;
        r("sleeve_length", self.sleeve_length, 15.0, 70.0)?;
        r("bicep", self.bicep, 12.0, 40.0)?;
        r("sleeve_opening", self.sleeve_opening, 8.0, 35.0)?;
        r("sleeve_underarm_height", self.sleeve_underarm_height, 4.0, 65.0)?;
        r("neck_size", self.neck_size, 30.0, 70.0)?;
        r("stand_height", self.stand_height, 1.5, 7.0)?;
        r("collar_height_cb", self.collar_height_cb, 2.5, 9.0)?;
        r("collar_point_length", self.collar_point_length, 3.0, 10.0)?;
        if self.back_length_cb - self.yoke_depth < 20.0 {
            return Err("yoke_depth leaves less than 20 cm of back below the yoke".into());
        }
        if self.armhole_drop > self.body_length_hps - 20.0 {
            return Err("armhole_drop leaves less than 20 cm of side seam".into());
        }
        if self.sleeve_length - self.sleeve_underarm_height < 4.0 {
            return Err("sleeve_length must exceed sleeve_underarm_height by at least 4 cm (cap height)".into());
        }
        if self.sleeve_underarm_height < 5.0 {
            return Err("sleeve_underarm_height must be at least 5 cm".into());
        }
        Ok(())
    }
}

/// Finished-garment spec of the women's cross-pocket elastic-waist wide-leg pant.  `Default`
/// is base size S of the graded chart `CL1086464.xlsx` (POM codes in the field docs); halves
/// are flat half measurements as printed in the chart.
#[derive(Clone, Debug, PartialEq)]
pub struct PantSpec {
    /// 20125 - 1/2 waist at top edge, relaxed.
    pub half_waist: f64,
    /// 20245 - 1/2 waist at top edge, stretched (drives the waistband length).
    pub half_waist_stretched: f64,
    /// 20305-A - hip position below the top edge at the side seam.
    pub hip_pos_side: f64,
    /// 20305-B - hip position below the top edge at centre front.
    pub hip_pos_cf: f64,
    /// 20305 - 1/2 seat.
    pub half_seat: f64,
    /// 20865 - thigh, 1 cm below the crotch point.
    pub thigh: f64,
    /// 21505 - front rise to top edge (curved).
    pub front_rise: f64,
    /// 21545 - back rise to top edge (curved).
    pub back_rise: f64,
    /// 20905 - knee width (12" below the crotch).
    pub knee: f64,
    /// 21125 - 1/2 leg opening (straight).
    pub leg_opening: f64,
    /// 30210 - bottom hem height (fold).
    pub hem_height: f64,
    /// 21885 - inseam along the seam.
    pub inseam: f64,
    /// 20265 - waistband width (finished).
    pub waistband_width: f64,
    /// 22145 - front pocket opening along the waistband.
    pub pocket_opening_waist: f64,
    /// 22165 - front pocket opening length down the outseam.
    pub pocket_opening_length: f64,
    /// 22565 - pocket bag depth.
    pub pocket_bag_depth: f64,
    /// 30845 - 1/2 drawcord length (fold to end) = hanging part.
    pub drawcord_length: f64,
}

impl Default for PantSpec {
    fn default() -> Self {
        PantSpec {
            half_waist: 35.0,
            half_waist_stretched: 49.0,
            hip_pos_side: 17.0,
            hip_pos_cf: 16.0,
            half_seat: 52.0,
            thigh: 33.0,
            front_rise: 30.5,
            back_rise: 41.0,
            knee: 30.0,
            leg_opening: 30.0,
            hem_height: 2.8,
            inseam: 78.0,
            waistband_width: 5.2,
            pocket_opening_waist: 3.0,
            pocket_opening_length: 15.5,
            pocket_bag_depth: 24.0,
            drawcord_length: 30.0,
        }
    }
}

/// (POM code, canonical name) for every `PantSpec` field.
pub const PANT_POMS: &[(&str, &str)] = &[
    ("20125", "half_waist"), ("20245", "half_waist_stretched"), ("20305-A", "hip_pos_side"),
    ("20305-B", "hip_pos_cf"), ("20305", "half_seat"), ("20865", "thigh"), ("21505", "front_rise"),
    ("21545", "back_rise"), ("20905", "knee"), ("21125", "leg_opening"), ("30210", "hem_height"),
    ("21885", "inseam"), ("20265", "waistband_width"), ("22145", "pocket_opening_waist"),
    ("22165", "pocket_opening_length"), ("22565", "pocket_bag_depth"), ("30845", "drawcord_length"),
];

const PANT_ALIASES: &[(&str, &str)] = &[
    ("waist", "half_waist"), ("half_waist_relaxed", "half_waist"), ("waist_stretched", "half_waist_stretched"),
    ("seat", "half_seat"), ("hip", "half_seat"), ("rise_front", "front_rise"), ("rise_back", "back_rise"),
    ("hem", "hem_height"), ("bottom_hem_height", "hem_height"), ("waistband", "waistband_width"),
    ("waist_band_width", "waistband_width"), ("opening_waist", "pocket_opening_waist"),
    ("opening_length", "pocket_opening_length"), ("bag_depth", "pocket_bag_depth"),
    ("drawcord", "drawcord_length"), ("drawstring", "drawcord_length"), ("leg_opening_half", "leg_opening"),
];

impl PantSpec {
    fn slots(&mut self) -> Vec<(&'static str, &mut f64)> {
        vec![
            ("half_waist", &mut self.half_waist), ("half_waist_stretched", &mut self.half_waist_stretched),
            ("hip_pos_side", &mut self.hip_pos_side), ("hip_pos_cf", &mut self.hip_pos_cf),
            ("half_seat", &mut self.half_seat), ("thigh", &mut self.thigh), ("front_rise", &mut self.front_rise),
            ("back_rise", &mut self.back_rise), ("knee", &mut self.knee), ("leg_opening", &mut self.leg_opening),
            ("hem_height", &mut self.hem_height), ("inseam", &mut self.inseam),
            ("waistband_width", &mut self.waistband_width), ("pocket_opening_waist", &mut self.pocket_opening_waist),
            ("pocket_opening_length", &mut self.pocket_opening_length), ("pocket_bag_depth", &mut self.pocket_bag_depth),
            ("drawcord_length", &mut self.drawcord_length),
        ]
    }
    pub fn field_names() -> Vec<&'static str> {
        PantSpec::default().slots().into_iter().map(|(n, _)| n).collect()
    }
    fn canon(key: &str) -> Option<&'static str> {
        let k = norm_key(key);
        for (code, name) in PANT_POMS {
            if norm_key(code) == k || *name == k {
                return Some(name);
            }
        }
        PANT_ALIASES.iter().find(|(a, _)| *a == k).map(|(_, f)| *f)
    }
    pub fn get(&self, key: &str) -> Option<f64> {
        let mut c = self.clone();
        let k = Self::canon(key)?;
        c.slots().into_iter().find(|(n, _)| *n == k).map(|(_, v)| *v)
    }
    pub fn set(&mut self, key: &str, v: f64) -> bool {
        let Some(k) = Self::canon(key) else { return false };
        for (n, r) in self.slots() {
            if n == k {
                *r = v;
                return true;
            }
        }
        false
    }
    /// Canonical-name map (round-trips through `from_pom`).
    pub fn to_map(&self) -> BTreeMap<String, f64> {
        let mut c = self.clone();
        c.slots().into_iter().map(|(n, v)| (n.to_string(), *v)).collect()
    }
    /// POM-code map ("20125" -> value ...).
    pub fn to_pom(&self) -> BTreeMap<String, f64> {
        let mut out = BTreeMap::new();
        for (code, name) in PANT_POMS {
            out.insert((*code).to_string(), self.get(name).unwrap());
        }
        out
    }
    /// Build from POM-keyed values (`"20125"`, `"20305-A"`, `"30845"` ...) and/or canonical
    /// names; missing keys keep the sample defaults (base size S).  Unknown keys are ignored.
    pub fn from_pom(m: &BTreeMap<String, f64>) -> PantSpec {
        Self::from_pom_checked(m).0
    }
    pub fn from_pom_checked(m: &BTreeMap<String, f64>) -> (PantSpec, Vec<String>) {
        let mut s = PantSpec::default();
        let mut warn = Vec::new();
        for (k, v) in m {
            match Self::canon(k) {
                Some(f) if v.is_finite() => {
                    s.set(f, *v);
                }
                Some(_) => warn.push(format!("non-finite value for '{}' ignored", k)),
                None => warn.push(format!("unknown pant POM/key '{}' ignored", k)),
            }
        }
        (s, warn)
    }
    pub fn validate(&self) -> Result<(), String> {
        let mut c = self.clone();
        for (n, v) in c.slots() {
            if bad(*v) || *v <= 0.0 {
                return Err(format!("pant spec '{}' must be a positive finite number (got {})", n, v));
            }
        }
        let r = |n: &str, v: f64, lo: f64, hi: f64| -> Result<(), String> {
            if v < lo || v > hi { Err(format!("pant spec '{}' = {} outside the supported range {}..{} cm", n, v, lo, hi)) } else { Ok(()) }
        };
        r("half_waist", self.half_waist, 20.0, 80.0)?;
        r("half_waist_stretched", self.half_waist_stretched, 25.0, 90.0)?;
        r("half_seat", self.half_seat, 35.0, 90.0)?;
        r("thigh", self.thigh, 20.0, 60.0)?;
        r("front_rise", self.front_rise, 15.0, 50.0)?;
        r("back_rise", self.back_rise, 20.0, 60.0)?;
        r("knee", self.knee, 15.0, 60.0)?;
        r("leg_opening", self.leg_opening, 12.0, 60.0)?;
        r("hem_height", self.hem_height, 0.0001, 8.0)?;
        r("inseam", self.inseam, 40.0, 100.0)?;
        r("waistband_width", self.waistband_width, 2.0, 12.0)?;
        r("pocket_opening_waist", self.pocket_opening_waist, 1.0, 10.0)?;
        r("pocket_opening_length", self.pocket_opening_length, 8.0, 30.0)?;
        r("pocket_bag_depth", self.pocket_bag_depth, 12.0, 40.0)?;
        r("drawcord_length", self.drawcord_length, 5.0, 80.0)?;
        if self.front_rise - self.waistband_width < 12.0 || self.back_rise - self.waistband_width < 18.0 {
            return Err("rises minus waistband width leave too short a crotch curve".into());
        }
        if self.inseam < 3.0 * self.hem_height + 10.0 {
            return Err("inseam too short for the hem height".into());
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------------------
// construction helpers
// ---------------------------------------------------------------------------------------

/// Outline builder: appends edges (point runs) and computes Catmull-Rom Bezier handles for
/// the smooth ones.  Interior vertices of smooth runs are smooth; run ends are corners.
struct Chain {
    nodes: Vec<Node>,
    pend: V2,
}
impl Chain {
    fn new() -> Chain {
        Chain { nodes: Vec::new(), pend: V2::default() }
    }
    /// `pts` = start anchor, interior points, end anchor.  One tag/SA per run.
    fn edge(&mut self, pts: &[V2], tag: &str, sa: f64, smooth: bool) {
        let tags: Vec<(&str, f64)> = vec![(tag, sa); pts.len() - 1];
        self.edge_tags(pts, &tags, smooth);
    }
    /// Like `edge` but every segment start node carries its own (tag, SA).
    fn edge_tags(&mut self, pts: &[V2], tags: &[(&str, f64)], smooth: bool) {
        let n = pts.len();
        debug_assert!(n >= 2 && tags.len() == n - 1);
        let curved = smooth && n > 2;
        for k in 0..n - 1 {
            let mut nd = Node { p: pts[k], edge: tags[k].0.to_string(), sa: Some(tags[k].1), ..Default::default() };
            if k == 0 {
                nd.hin = self.pend;
                if curved {
                    nd.hout = (pts[1] - pts[0]) * (1.0 / 3.0);
                }
            } else if curved {
                // Catmull-Rom tangent, limited to a third of each adjacent segment so that
                // closely spaced points (e.g. a split point) cannot produce loops
                let dir = (pts[k + 1] - pts[k - 1]).norm();
                let base = (pts[k + 1] - pts[k - 1]).len() / 6.0;
                nd.hout = dir * base.min(pts[k].dist(pts[k + 1]) / 3.0);
                nd.hin = dir * -base.min(pts[k].dist(pts[k - 1]) / 3.0);
            }
            self.nodes.push(nd);
        }
        self.pend = if curved { (pts[n - 1] - pts[n - 2]) * (-1.0 / 3.0) } else { V2::default() };
    }
    fn finish(mut self) -> Vec<Node> {
        if let Some(f) = self.nodes.first_mut() {
            f.hin = self.pend;
        }
        self.nodes
    }
}

fn new_piece(name: &str, zone: &str, nodes: Vec<Node>, qty: u32, mirror: bool, material: &str) -> Piece {
    Piece {
        name: name.into(),
        zone: zone.into(),
        nodes,
        grain: (v2(0.0, 0.0), v2(0.0, -10.0)),
        notches: vec![],
        darts: vec![],
        internal: vec![],
        drills: vec![],
        sa: 1.0,
        mirror,
        qty,
        material: if material.is_empty() { "SELF".into() } else { material.into() },
    }
}

/// Notch on a run of edges `tags` (in outline order) at arc fraction `frac` of the whole run.
fn notch_on(p: &mut Piece, tags: &[&str], frac: f64, kind: &str) {
    let idx: Vec<usize> = (0..p.nodes.len()).filter(|&i| tags.contains(&p.nodes[i].edge.as_str())).collect();
    if idx.is_empty() {
        return;
    }
    let lens: Vec<f64> = idx.iter().map(|&i| p.edge_len(i)).collect();
    let total: f64 = lens.iter().sum();
    let mut want = frac.clamp(0.0, 1.0) * total;
    for (k, &i) in idx.iter().enumerate() {
        if want <= lens[k] || k + 1 == idx.len() {
            let t = if lens[k] > 1e-9 { (want / lens[k]).clamp(0.0, 1.0) } else { 0.0 };
            p.notches.push(Notch { node: i, t, kind: kind.into() });
            return;
        }
        want -= lens[k];
    }
}

fn sm_tag(a: &str, at: &str, b: &str, bt: &str, rev: bool) -> Seam {
    Seam { a_piece: a.into(), a_tag: at.into(), b_piece: b.into(), b_tag: bt.into(), rev }
}

fn pl_clamp(knots: &[(f64, f64)], x: f64) -> f64 {
    if x <= knots[0].0 {
        return knots[0].1;
    }
    for w in knots.windows(2) {
        if x <= w[1].0 {
            let t = if (w[1].0 - w[0].0).abs() < 1e-12 { 0.0 } else { (x - w[0].0) / (w[1].0 - w[0].0) };
            return w[0].1 + (w[1].1 - w[0].1) * t;
        }
    }
    knots[knots.len() - 1].1
}
/// Piecewise-linear map that continues with slope 1 beyond the last knot.
fn pl_remap(knots: &[(f64, f64)], x: f64) -> f64 {
    let last = knots[knots.len() - 1];
    if x > last.0 {
        return last.1 + (x - last.0);
    }
    pl_clamp(knots, x)
}

fn poly_len(p: &[V2]) -> f64 {
    p.windows(2).map(|w| w[0].dist(w[1])).sum()
}

/// Split a polyline at the given arc-length fractions (ascending, in 0..1); returns the
/// polyline with the split points inserted and the indices of those points.
fn split_poly(pts: &[V2], fr: &[f64]) -> (Vec<V2>, Vec<usize>) {
    let total = poly_len(pts);
    let mut out = vec![pts[0]];
    let mut idx = Vec::new();
    let mut acc = 0.0;
    let mut fi = 0;
    for w in pts.windows(2) {
        let l = w[0].dist(w[1]);
        while fi < fr.len() && acc + l >= fr[fi] * total - 1e-9 && l > 1e-12 {
            let t = ((fr[fi] * total - acc) / l).clamp(0.0, 1.0);
            let p = w[0].lerp(w[1], t);
            // snap to an existing vertex when closer than MIN_PT_GAP (keeps the curve free of tiny segments)
            if p.dist(w[0]) < MIN_PT_GAP {
                idx.push(out.len() - 1);
            } else if p.dist(w[1]) < MIN_PT_GAP {
                out.push(w[1]);
                idx.push(out.len() - 1);
            } else {
                out.push(p);
                idx.push(out.len() - 1);
            }
            fi += 1;
        }
        if w[1].dist(*out.last().unwrap()) > 1e-9 {
            out.push(w[1]);
        }
        acc += l;
    }
    (out, idx)
}

// ---------------------------------------------------------------------------------------
// shirt
// ---------------------------------------------------------------------------------------

/// Sew-line placket extension is the finished placket minus this (sample: 3.5 -> 3.2).
const PLACKET_SEW_DIFF: f64 = 0.3;

struct ShirtSa {
    placket: f64, hem: f64, f_side: f64, b_side: f64, armhole: f64, seam: f64, collar: f64,
    cap: f64, ua_l: f64, ua_r: f64, sleeve_hem: f64,
}
fn shirt_sa(o: &GarmentOpts) -> ShirtSa {
    if o.sample_sa {
        ShirtSa { placket: 1.7, hem: o.shirt_hem, f_side: 0.8, b_side: 1.7, armhole: 0.8, seam: o.sa, collar: 1.3, cap: 2.0, ua_l: 0.8, ua_r: 1.7, sleeve_hem: o.sleeve_hem }
    } else {
        ShirtSa { placket: o.sa, hem: o.shirt_hem, f_side: o.sa, b_side: o.sa, armhole: o.sa, seam: o.sa, collar: o.sa, cap: o.sa, ua_l: o.sa, ua_r: o.sa, sleeve_hem: o.sleeve_hem }
    }
}

// base-size (L) anchor constants of the sample, piece frames: x across (CF/CB fold at 0), y up
// front / back parts of the sample half hem and half chest; spec increments are shared equally
const F_HEM0: f64 = 30.81;
const F_CHEST0: f64 = 31.36;
const B_HEM0: f64 = 29.20;
const B_CHEST0: f64 = 29.76;
const PLACKET_RISE: f64 = 2.21; // placket top above the CF neck point
const FRONT_NECK_STRAIGHT: f64 = 1.60; // CF-ward straight part of the front neck
const BACK_ARMHOLE_END_DROP: f64 = 1.07; // back armhole end below the CB yoke-seam corner
const CAP_H0: f64 = 16.51; // sample cap height
const SLEEVE_CHAMFER: f64 = 0.66;

/// Draft the men's short-sleeve shirt: pieces `FRT`, `back`, `back YK`, `CLR`, `BND TOP`,
/// `BND IN`, `Sleeve` (names and quantities of the sample).
pub fn draft_shirt(s: &ShirtSpec, o: &GarmentOpts) -> Result<Pattern, String> {
    let pat = build_shirt(s, o)?;
    check_pattern(&pat)?;
    Ok(pat)
}

fn build_shirt(s: &ShirtSpec, o: &GarmentOpts) -> Result<Pattern, String> {
    s.validate()?;
    if bad(o.sa) || o.sa < 0.0 || o.sa > 5.0 || o.shirt_hem < 0.0 || o.sleeve_hem < 0.0 {
        return Err("invalid seam/hem allowance".into());
    }
    let sa = shirt_sa(o);
    let dflt = ShirtSpec::default();
    let ua_y = s.body_length_hps - s.armhole_drop;

    // ---- FRT (one front, cut as a pair; grown-on placket) ----
    let pw = s.placket_width - PLACKET_SEW_DIFF;
    let y_neck = s.body_length_hps - s.front_neck_depth;
    let y_pk = y_neck + PLACKET_RISE;
    let f0 = v2(-pw, y_pk);
    let f1 = v2(-pw, 0.0);
    let f2 = v2(0.0, 0.0);
    let f3 = v2(F_HEM0 + 0.5 * (s.half_hem - dflt.half_hem), s.hem_curve);
    let f4 = v2(F_CHEST0 + 0.5 * (s.half_chest - dflt.half_chest), ua_y);
    let f5 = v2(s.across_chest / 2.0, s.body_length_hps - s.shoulder_slope);
    let f6 = v2(s.front_neck_width, s.body_length_hps);
    let f7 = v2(FRONT_NECK_STRAIGHT.min(s.front_neck_width * 0.8), y_neck);
    let f8 = v2(0.0, y_neck);
    let f9 = v2(0.0, y_pk);
    let mut c = Chain::new();
    c.edge(&[f0, f1], "placket", sa.placket, false);
    c.edge(&[f1, f2], "hem", sa.hem, false);
    c.edge(&tpl_sim(f2, f3, &T_FRT_HEM), "hem", sa.hem, true);
    c.edge(&[f3, f4], "side", sa.f_side, false);
    c.edge(&tpl_sim(f4, f5, &T_FRT_ARMHOLE), "armhole", sa.armhole, true);
    c.edge(&[f5, f6], "shoulder", sa.seam, false);
    c.edge(&tpl_sim(f6, f7, &T_FRT_NECK), "neck", sa.seam, true);
    c.edge(&[f7, f8], "neck", sa.seam, false);
    c.edge(&[f8, f9], "placket_fold", 0.0, false);
    c.edge(&[f9, f0], "placket_top", sa.seam, false);
    let mut frt = new_piece("FRT", "upper", c.finish(), 1, true, "");
    frt.internal.push(vec![v2(0.0, 0.0), v2(0.0, y_pk)]);
    frt.grain = (v2(f3.x * 0.45, s.body_length_hps - 12.0), v2(f3.x * 0.45, 8.0));

    // ---- back (on fold at CB) ----
    let b0 = v2(0.0, s.back_length_cb - s.yoke_depth);
    let b1 = v2(0.0, 0.0);
    let b2 = v2(B_HEM0 + 0.5 * (s.half_hem - dflt.half_hem), s.hem_curve);
    let b3 = v2(B_CHEST0 + 0.5 * (s.half_chest - dflt.half_chest), ua_y);
    let b4 = v2(s.across_back / 2.0, b0.y - BACK_ARMHOLE_END_DROP);
    let mut c = Chain::new();
    c.edge(&[b0, b1], "cb", 0.0, false);
    c.edge(&tpl_sim(b1, b2, &T_BACK_HEM), "hem", sa.hem, true);
    c.edge(&[b2, b3], "side", sa.b_side, false);
    c.edge(&tpl_sim(b3, b4, &T_BACK_ARMHOLE), "armhole", sa.armhole, true);
    c.edge(&[b4, b0], "yokeseam", sa.seam, false);
    let mut back = new_piece("back", "upper", c.finish(), 1, true, "");
    back.grain = (v2(0.0, -2.69), v2(0.0, b0.y + 6.35));

    // ---- yoke (on fold, 2 pcs: outer + inner) ----
    let yd = s.yoke_depth;
    let y0 = v2(0.0, yd);
    let y1 = v2(0.0, 0.0);
    let y2 = v2(s.across_back / 2.0 - 0.05, 0.0);
    let y4 = v2(s.back_neck_width, yd + s.back_neck_depth);
    let y3 = v2(s.across_shoulder / 2.0, y4.y - s.shoulder_slope_back);
    let mut c = Chain::new();
    c.edge(&[y0, y1], "cb", 0.0, false);
    c.edge(&[y1, y2], "yokeseam", sa.seam, false);
    c.edge(&tpl_sim(y2, y3, &T_YOKE_ARMHOLE), "armhole", sa.armhole, true);
    c.edge(&[y3, y4], "shoulder", sa.seam, false);
    c.edge(&tpl_sim(y4, y0, &T_YOKE_NECK), "neck", sa.seam, true);
    let mut yoke = new_piece("back YK", "upper", c.finish(), 2, true, "");
    yoke.grain = (v2(0.0, -1.2), v2(0.0, yd + 1.21));
    notch_on(&mut yoke, &["shoulder"], 0.915, "slit");

    // ---- collar (on fold, 2 pcs: upper + under collar) ----
    let dneck = (s.neck_size - dflt.neck_size) / 2.0;
    let xe = 22.70 + dneck;
    let c1 = v2(0.0, 0.0);
    let c0 = v2(0.0, s.collar_height_cb);
    let c6 = v2(xe, 1.16 * xe / 22.70); // the neck-seam rise grows with the collar length
    let c7 = c6 + v2(-0.2197, 0.9756) * s.collar_point_length;
    let mut c = Chain::new();
    c.edge(&[c0, c1], "cb", 0.0, false);
    c.edge(&tpl_sim(c1, c6, &T_COLLAR_NECKSEAM), "neckseam", sa.collar, true);
    c.edge(&[c6, c7], "point", sa.collar, false);
    c.edge(&tpl_sim(c7, c0, &T_COLLAR_OUTER), "outer", sa.collar, true);
    let mut collar = new_piece("CLR", "upper", c.finish(), 2, true, "");
    collar.grain = (v2(0.0, -0.48), v2(0.0, s.collar_height_cb + 0.48));

    // ---- collar stand: BND TOP and BND IN (identical shapes, on fold) ----
    let dst = s.stand_height - dflt.stand_height;
    let xb = 24.38 + dneck;
    let n1 = v2(0.0, 0.0);
    let n0 = v2(0.0, s.stand_height);
    let n9 = v2(xb, 3.48 * xb / 24.38); // end rise grows with the stand length
    let n14 = n9 + v2(-3.01, 2.10 + dst);
    // the stand's neck seam is split where the back (yoke) neck ends and the front neck begins
    let neck_b = yoke.tag_len("neck");
    let neck_f = frt.tag_len("neck");
    let band_seam = tpl_sim(n1, n9, &T_BAND_NECKSEAM);
    let band_fr = (neck_b / (neck_b + neck_f + 0.93)).clamp(0.2, 0.8);
    let (band_seam, band_cut) = split_poly(&band_seam, &[band_fr]);
    let band_tags: Vec<(&str, f64)> = (0..band_seam.len() - 1).map(|k| (if k < band_cut[0] { "neck_back" } else { "neck_front" }, sa.collar)).collect();
    let mk_band = |name: &str| -> Piece {
        let mut c = Chain::new();
        c.edge(&[n0, n1], "cb", 0.0, false);
        c.edge_tags(&band_seam, &band_tags, true);
        c.edge(&tpl_sim(n9, n14, &T_BAND_END), "end", sa.collar, true);
        c.edge(&tpl_sim(n14, n0, &T_BAND_TOP), "top", sa.collar, true);
        let mut p = new_piece(name, "upper", c.finish(), 1, true, "");
        p.grain = (v2(0.0, -0.33), v2(0.0, s.stand_height + 0.33));
        p
    };
    let band_top = mk_band("BND TOP");
    let band_in = mk_band("BND IN");

    // ---- sleeve (pair; cap split in front / yoke / back parts that follow the real armholes) ----
    let uh = s.sleeve_underarm_height;
    let ow = s.sleeve_opening;
    let cham = ow - SLEEVE_CHAMFER;
    let sc_r = v2(cham, 2.0);
    let sh_r = v2(ow, 0.0);
    let sh_l = v2(-ow, 0.0);
    let sc_l = v2(-cham, 2.0);
    let ub_l = v2(-s.bicep, uh);
    let ub_r = v2(s.bicep, uh);
    let rd_cap = (s.sleeve_length - uh) / CAP_H0;
    let cap = tpl_line(ub_l, ub_r, &T_SLEEVE_CAP, rd_cap);
    let arm_f = frt.tag_len("armhole");
    let arm_y = yoke.tag_len("armhole");
    let arm_b = back.tag_len("armhole");
    let tot = arm_f + arm_y + arm_b;
    let (capp, cut_idx) = split_poly(&cap, &[arm_f / tot, (arm_f + arm_y) / tot]);
    let mut cap_tags: Vec<(&str, f64)> = Vec::new();
    for k in 0..capp.len() - 1 {
        let tg = if k < cut_idx[0] { "cap_front" } else if k < cut_idx[1] { "cap_yoke" } else { "cap_back" };
        cap_tags.push((tg, sa.cap));
    }
    let mut c = Chain::new();
    let folded = if o.sample_sa { (fold_corner_in(sc_r, sh_r, sh_l), fold_corner_out(sh_r, sh_l, sc_l)) } else { (None, None) };
    match folded {
        (Some((r1, r2)), Some((l1, l2))) => {
            c.edge(&[sc_r, r1], "cuff_r", sa.ua_r, false);
            c.edge(&[r1, r2], "cuff_r", sa.ua_r, false);
            c.edge(&[r2, l1], "hem", sa.sleeve_hem, false);
            c.edge(&[l1, l2], "cuff_l", sa.ua_l, false);
            c.edge(&[l2, sc_l], "cuff_l", sa.ua_l, false);
        }
        _ => {
            c.edge(&[sc_r, sh_r], "cuff_r", sa.ua_r, false);
            c.edge(&[sh_r, sh_l], "hem", sa.sleeve_hem, false);
            c.edge(&[sh_l, sc_l], "cuff_l", sa.ua_l, false);
        }
    }
    // the underarm edges end in a straight run: a long last segment keeps the cut line from
    // spiking at the corner to the cuff (tiny flattened segments overshoot a concave offset corner)
    let ul = tpl_sim(sc_l, ub_l, &T_SLEEVE_UNDER_L);
    c.edge(&ul[..ul.len() - 1], "underarm_l", sa.ua_l, true);
    c.edge(&ul[ul.len() - 2..], "underarm_l", sa.ua_l, false);
    c.edge_tags(&capp, &cap_tags, true);
    let ur = tpl_sim(ub_r, sc_r, &T_SLEEVE_UNDER_R);
    c.edge(&ur[..ur.len() - 1], "underarm_r", sa.ua_r, true);
    c.edge(&ur[ur.len() - 2..], "underarm_r", sa.ua_r, false);
    let mut sleeve = new_piece("Sleeve", "sleeve", c.finish(), 1, true, "");
    sleeve.grain = (v2(0.0, s.sleeve_length - 2.0), v2(0.0, 2.0));
    notch_on(&mut sleeve, &["cap_front", "cap_yoke", "cap_back"], 0.494, "slit");

    let pieces = vec![frt, back, yoke, collar, band_top, band_in, sleeve];
    let seams = vec![
        sm_tag("FRT", "side", "back", "side", false),
        sm_tag("FRT", "shoulder", "back YK", "shoulder", false),
        sm_tag("back", "yokeseam", "back YK", "yokeseam", true),
        sm_tag("back", "cb", "back", "cb", false),
        sm_tag("back YK", "cb", "back YK", "cb", false),
        sm_tag("CLR", "cb", "CLR", "cb", false),
        sm_tag("BND TOP", "cb", "BND TOP", "cb", false),
        sm_tag("BND IN", "cb", "BND IN", "cb", false),
        // armhole: the sleeve cap runs front underarm -> shoulder tip -> back underarm
        sm_tag("FRT", "armhole", "Sleeve", "cap_front", false),
        sm_tag("back YK", "armhole", "Sleeve", "cap_yoke", true),
        sm_tag("back", "armhole", "Sleeve", "cap_back", true),
        sm_tag("Sleeve", "underarm_l", "Sleeve", "underarm_r", true),
        // collar: upper collar between the two stand pieces; inner stand to the neckline
        sm_tag("CLR", "neckseam", "BND TOP", "top", true),
        sm_tag("BND TOP", "top", "BND IN", "top", false),
        sm_tag("FRT", "neck", "BND IN", "neck_front", false),
        sm_tag("back YK", "neck", "BND IN", "neck_back", true),
    ];
    Ok(Pattern { style: "shirt-1078375".into(), size: "BASE".into(), garment: "shirt".into(), pieces, seams })
}

// ---------------------------------------------------------------------------------------
// pant
// ---------------------------------------------------------------------------------------

// base-size (S) anchors of the sample front/back, frame x = across (inseam/crotch side at 0), y up
const PF_A0X: f64 = 0.94;
const PF_H0: f64 = 80.94; // crotch point height
const PF_CF: (f64, f64) = (4.32, 105.39); // CF waist corner
const PF_WAIST_TILT: f64 = 0.61; // side corner above CF corner
const PF_A4: (f64, f64) = (29.86, 90.80); // end of the pocket opening on the outseam
const PF_ARC_EXTRA: f64 = 0.507; // crotch arc = rise - waistband + this
const PB_A0X: f64 = 3.93;
const PB_H0: f64 = 80.62;
const PB_CB: (f64, f64) = (13.86, 110.0);
const PB_SIDE_X: f64 = 38.82;
const PB_SIDE_DROP: f64 = 3.70; // side corner below the CB corner
const PB_ARC_EXTRA: f64 = 0.333;
const PB_W0: f64 = 106.30;
/// Hem (and knee) width growth per cm of half-leg-opening growth, front and back alike: the PDS rule
/// table grows both pieces by exactly the spec step (front + back = the full opening circumference).
const K_HEM: f64 = 1.0;
const KNEE_DROP: f64 = 38.4; // knee grading vertex below the crotch point (decoded rule table; not the 12" of the spec)
// grading coefficients: sew-line growth per cm of spec growth (calibrated on the sample grading)
const K_THIGH: f64 = 1.10;
const K_SEAT: f64 = 0.55;
const K_KNEE: f64 = 1.0;
const POCKET_DX0: f64 = 5.04; // sample pocket-opening run along the waist (spec 3.0)
const POCKET_DY0: f64 = 15.2; // sample pocket-opening run down the outseam (spec 15.5)
/// Fixed length of the string channel inside the waist (sample total 165 = 2 * 30 + 105).
const DRAWCORD_INSIDE: f64 = 105.0;
const DRAWCORD_WIDTH: f64 = 4.0;
const BELT_OVERLAP: f64 = 2.5; // belt half-length = stretched half waist + this (sample)

/// Crotch end point of a curve whose polyline length equals `arc` (bisection on the height).
fn crotch_end(tpl: &Tpl, a1: V2, x: f64, arc: f64) -> V2 {
    let len_at = |y: f64| poly_len(&tpl_sim(a1, v2(x, y), tpl));
    let (mut lo, mut hi) = (a1.y + 1.0, a1.y + 120.0);
    for _ in 0..80 {
        let mid = 0.5 * (lo + hi);
        if len_at(mid) < arc { lo = mid } else { hi = mid }
    }
    v2(x, 0.5 * (lo + hi))
}

fn knots(mut k: Vec<(f64, f64)>) -> Vec<(f64, f64)> {
    k.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let mut out: Vec<(f64, f64)> = Vec::new();
    for p in k {
        if let Some(l) = out.last() {
            if p.0 - l.0 < 1e-6 {
                continue;
            }
        }
        out.push(p);
    }
    out
}

// Calibrated shirt growth coefficients (cm of spec value per cm of the implied XML increment;
// see docs/CALIBRATION.md).  The shirt chart has no graded columns, so these absorb the
// grade-rule behaviour that the XML geometry implies.
const SHIRT_SLEEVE_OPENING_GROWTH: f64 = 0.8272;
const SHIRT_ARMHOLE_DROP_GROWTH: f64 = 0.5438;
const SHIRT_SHOULDER_SLOPE_GROWTH: f64 = 0.1424;
const SHIRT_UNDERARM_HEIGHT_GROWTH: f64 = -0.226;

struct LegDeltas { h: f64, k: f64, t: f64, s: f64 }

/// A grading rule point on a closed template polygon: located `off` cm of arc length after
/// template vertex `v`, with a displacement of (`kx`, `ky`) rule units per grade step.
/// Between rule points the displacement is interpolated by arc length, exactly like the
/// Optitex grading of the sample (vertices without a rule interpolate between the rule points
/// on either side of them).
#[derive(Clone, Copy)]
struct RuleKnot {
    v: usize,
    off: f64,
    kx: f64,
    ky: f64,
}
const fn rk(v: usize, off: f64, kx: f64, ky: f64) -> RuleKnot {
    RuleKnot { v, off, kx, ky }
}

/// Displace a closed template polygon by arc-interpolated rule knots; one rule unit is `ux`
/// cm along x and `uy` cm along y.  The result is moved so its bounding box starts at (0,0).
fn rule_grade(base: &[(f64, f64)], knots: &[RuleKnot], ux: f64, uy: f64) -> Vec<V2> {
    let pts: Vec<V2> = base.iter().map(|&(x, y)| v2(x, y)).collect();
    let n = pts.len();
    let mut s = vec![0.0; n];
    for i in 1..n {
        s[i] = s[i - 1] + pts[i - 1].dist(pts[i]);
    }
    let total = s[n - 1] + pts[n - 1].dist(pts[0]);
    let mut ks: Vec<(f64, f64, f64)> = knots.iter().map(|k| (s[k.v] + k.off, k.kx, k.ky)).collect();
    ks.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let m = ks.len();
    let mut out: Vec<V2> = Vec::with_capacity(n);
    for i in 0..n {
        let mut x = s[i];
        if x < ks[0].0 {
            x += total;
        }
        let mut val = (ks[m - 1].1, ks[m - 1].2);
        for j in 0..m {
            let a = ks[j];
            let b = if j + 1 < m { ks[j + 1] } else { (ks[0].0 + total, ks[0].1, ks[0].2) };
            if x >= a.0 - 1e-9 && x <= b.0 + 1e-9 {
                let t = if b.0 - a.0 > 1e-12 { ((x - a.0) / (b.0 - a.0)).clamp(0.0, 1.0) } else { 0.0 };
                val = (a.1 + (b.1 - a.1) * t, a.2 + (b.2 - a.2) * t);
                break;
            }
        }
        out.push(v2(pts[i].x + val.0 * ux, pts[i].y + val.1 * uy));
    }
    let (mut lx, mut ly) = (f64::MAX, f64::MAX);
    for p in &out {
        lx = lx.min(p.x);
        ly = ly.min(p.y);
    }
    out.iter().map(|p| v2(p.x - lx, p.y - ly)).collect()
}

// grade rules of the pocket pieces (rule units per grade step; one step = 0.5 cm of spec change,
// 1 unit = 2 cm per cm of spec): fitted to the decoded PDS rule table, see docs/CALIBRATION.md
const PKT_RULES: &[RuleKnot] = &[rk(0, 0.0, 1.0, 0.0), rk(0, 15.51, 1.0, 0.0), rk(4, 0.0, 1.0, -1.0), rk(23, 0.0, -1.0, -1.0), rk(24, 0.0, -1.0, 0.0), rk(25, 0.0, -1.0, 0.0), rk(25, 21.23, 1.0, 0.0)];
const FACING_RULES: &[RuleKnot] = &[rk(0, 0.0, 0.0, -1.0), rk(1, 0.0, -0.5, 0.0), rk(1, 4.01, -0.5, 0.0), rk(3, 0.0, 0.0, 0.0), rk(3, 15.51, 0.0, 0.0), rk(7, 0.0, 0.0, -1.0)];
const FACING1_RULES: &[RuleKnot] = &[rk(0, 0.0, 0.0, -1.0), rk(1, 0.0, 0.0, 0.0), rk(3, 0.0, 0.0, 0.0), rk(4, 0.0, 0.0, -1.0)];
/// Pocket piece growth: cm of displacement per rule unit per cm of spec change.
const POCKET_UNIT: f64 = 2.0;
/// The facings' short end edge lies on the waist line and carries the waist allowance in the sample.
const FACING_END_SA: f64 = 1.3;
/// Back side seam top minus PKT-IN opening (decoded 26.3 vs 25.99).
const BAG_OPENING_EASE: f64 = 0.3;

/// Draft the women's cross-pocket pant: pieces `WAIST- BELT`, `FRONT`, `BACK`, `PKT-IN`,
/// `FACING`, `DRAWSTRING`, `FACING1` (names and quantities of the sample).
pub fn draft_pant_detailed(s: &PantSpec, o: &GarmentOpts) -> Result<Pattern, String> {
    let pat = build_pant(s, o)?;
    check_pattern(&pat)?;
    Ok(pat)
}

fn build_pant(s: &PantSpec, o: &GarmentOpts) -> Result<Pattern, String> {
    s.validate()?;
    if bad(o.sa) || o.sa < 0.0 || o.sa > 5.0 || o.pant_hem < 0.0 {
        return Err("invalid seam/hem allowance".into());
    }
    let d = PantSpec::default();
    let (sa_all, sa_waist) = if o.sample_sa { (o.sa, 1.3) } else { (o.sa, o.sa) };
    let dd = |a: f64, b: f64| a - b;
    let d_lo = dd(s.leg_opening, d.leg_opening);
    let d_in = dd(s.inseam, d.inseam) + dd(s.hem_height, d.hem_height);
    let d_th = dd(s.thigh, d.thigh);
    let d_kn = dd(s.knee, d.knee);
    let d_se = dd(s.half_seat, d.half_seat);
    let d_p1 = dd(s.pocket_opening_waist, d.pocket_opening_waist);
    let d_p2 = dd(s.pocket_opening_length, d.pocket_opening_length);
    let wb = s.waistband_width;

    // ---------------- FRONT ----------------
    let front_d = LegDeltas { h: K_HEM * d_lo, k: K_KNEE * d_kn, t: K_THIGH * d_th, s: K_SEAT * d_se };
    let h_f = PF_H0 + d_in;
    let a1 = v2(0.0, h_f);
    let arc_f = s.front_rise - wb + PF_ARC_EXTRA;
    let a2 = crotch_end(&T_PF_CROTCH, a1, PF_CF.0, arc_f);
    let w_f = a2.y + PF_WAIST_TILT;
    let a4y = w_f - (POCKET_DY0 + d_p2);
    let knots_y_f = knots(vec![(0.0, 0.0), (PF_H0, h_f), (106.0, w_f)]);
    let dk_f = |y: f64| -> f64 {
        let ys = knots(vec![(0.0, front_d.h), (h_f - KNEE_DROP, front_d.k), (h_f - 1.0, front_d.t), (a4y, front_d.s)]);
        pl_clamp(&ys, y)
    };
    let a4 = v2(PF_A4.0 + dk_f(a4y), a4y);
    let a3 = v2(a4.x - (POCKET_DX0 + d_p1), w_f);
    let a0 = v2(PF_A0X, 0.0);
    let a5 = v2(28.95 + dk_f(0.0), 0.0);
    let mut out_pts = vec![a4];
    for &(x0, y0) in &PF_OUTSEAM[1..PF_OUTSEAM.len() - 1] {
        let y = pl_remap(&knots_y_f, y0);
        out_pts.push(v2(x0 + dk_f(y), y));
    }
    out_pts.push(a5);
    let hem_mid = v2(0.5 * (a0.x + a5.x), 0.0);
    let mut c = Chain::new();
    c.edge(&tpl_sim(a0, a1, &T_PF_INSEAM), "inseam", sa_all, true);
    c.edge(&tpl_sim(a1, a2, &T_PF_CROTCH), "crotch", sa_all, true);
    c.edge(&[a2, a3], "waist", sa_waist, false);
    c.edge(&[a3, a4], "pocket", sa_all, false);
    c.edge(&out_pts, "outseam", sa_all, true);
    c.edge(&[a5, hem_mid, a0], "hem", o.pant_hem, false);
    let mut front = new_piece("FRONT", "trouser", c.finish(), 1, true, "A");
    front.grain = (v2(hem_mid.x, w_f - 6.0), v2(hem_mid.x, 8.0));

    // ---------------- pocket bag / facings (rule-graded templates) ----------------
    let sa_end = if o.sample_sa { FACING_END_SA } else { sa_all };
    let (ux, uy) = (POCKET_UNIT * d_p1, POCKET_UNIT * d_p2);
    let pk = rule_grade(PKT_IN_POLY, PKT_RULES, ux, uy + (s.pocket_bag_depth - d.pocket_bag_depth));
    let mut c = Chain::new();
    c.edge(&[pk[0], pk[1], pk[2], pk[3], pk[4]], "top", sa_all, false);
    c.edge(&pk[4..=23], "curve", sa_all, true);
    c.edge(&[pk[23], pk[24], pk[25]], "diag", sa_all, true);
    let mut run: Vec<V2> = pk[25..].to_vec();
    run.push(pk[0]);
    c.edge(&run, "opening", if o.sample_sa { 1.3 } else { sa_all }, true);
    let mut pkt = new_piece("PKT-IN", "trouser", c.finish(), 1, true, "A");
    let (ex, ey) = (pk.iter().fold(0.0f64, |m, p| m.max(p.x)), pk.iter().fold(0.0f64, |m, p| m.max(p.y)));
    pkt.grain = (v2(ex * 0.5, ey - 3.0), v2(ex * 0.5, 3.0));
    notch_on(&mut pkt, &["opening"], 0.82, "slit");
    notch_on(&mut pkt, &["top"], 0.71, "slit");

    let fc = rule_grade(FACING_POLY, FACING_RULES, ux, uy);
    let mut c = Chain::new();
    c.edge(&[fc[0], fc[1]], "long", sa_all, false);
    c.edge(&[fc[1], fc[2], fc[3]], "end", sa_end, false);
    c.edge(&fc[3..=7], "bag", sa_all, true);
    c.edge(&[fc[7], fc[8], fc[9], fc[10], fc[0]], "corner", sa_all, true);
    let mut facing = new_piece("FACING", "trouser", c.finish(), 1, true, "");
    let (fx, fy) = (fc.iter().fold(0.0f64, |m, p| m.max(p.x)), fc.iter().fold(0.0f64, |m, p| m.max(p.y)));
    facing.grain = (v2(fx * 0.5, fy - 3.0), v2(fx * 0.5, 3.0));
    notch_on(&mut facing, &["end"], 0.46, "slit");
    notch_on(&mut facing, &["bag"], 0.71, "slit");

    let f1 = rule_grade(FACING1_POLY, FACING1_RULES, ux, uy);
    let mut c = Chain::new();
    c.edge(&[f1[0], f1[1]], "long", sa_all, false);
    c.edge(&[f1[1], f1[2]], "end", sa_end, false);
    c.edge(&[f1[2], f1[3]], "opening", sa_all, false);
    c.edge(&[f1[3], f1[4]], "bottom", sa_all, false);
    c.edge(&[f1[4], f1[0]], "close", sa_all, false);
    let mut facing1 = new_piece("FACING1", "trouser", c.finish(), 1, true, "");
    let (f1x, f1y) = (f1.iter().fold(0.0f64, |m, p| m.max(p.x)), f1.iter().fold(0.0f64, |m, p| m.max(p.y)));
    facing1.grain = (v2(f1x * 0.5, f1y - 3.0), v2(f1x * 0.5, 3.0));

    // ---------------- BACK ----------------
    let back_d = LegDeltas { h: K_HEM * d_lo, k: K_KNEE * d_kn, t: K_THIGH * d_th, s: K_SEAT * d_se };
    let h_b = PB_H0 + d_in;
    let b1 = v2(0.0, h_b);
    let arc_b = s.back_rise - wb + PB_ARC_EXTRA;
    let b2 = crotch_end(&T_PB_CROTCH, b1, PB_CB.0, arc_b);
    let w_b = b2.y - PB_SIDE_DROP;
    let knots_y_b = knots(vec![(0.0, 0.0), (PB_H0, h_b), (PB_W0, w_b)]);
    let dk_b = |y: f64| -> f64 {
        let ys = knots(vec![(0.0, back_d.h), (h_b - KNEE_DROP, back_d.k), (h_b - 1.0, back_d.t), (w_b, back_d.s)]);
        pl_clamp(&ys, y)
    };
    let b3 = v2(PB_SIDE_X + dk_b(w_b), w_b);
    let b0 = v2(PB_A0X, 0.0);
    let b5 = v2(37.03 + dk_b(0.0), 0.0);
    let mut out_b = vec![b3];
    for &(x0, y0) in &PB_OUTSEAM[1..PB_OUTSEAM.len() - 1] {
        let y = pl_remap(&knots_y_b, y0);
        out_b.push(v2(x0 + dk_b(y), y));
    }
    out_b.push(b5);
    // the top of the back side seam is sewn to the pocket bag opening.  The decoded BACK has a
    // grading vertex 26.3 cm below the waist corner while the front pocket opening is only
    // 16.0 cm, and the PKT-IN opening is 25.99 cm: the seam is as long as the bag opening plus
    // a 0.3 cm ease (see docs/CALIBRATION.md, item 18)
    let pocket_len = pkt.tag_len("opening") + BAG_OPENING_EASE;
    let (out_b, out_cut) = split_poly(&out_b, &[(pocket_len / poly_len(&out_b)).clamp(0.05, 0.6)]);
    let out_tags: Vec<(&str, f64)> = (0..out_b.len() - 1).map(|k| (if k < out_cut[0] { "outseam_top" } else { "outseam" }, sa_all)).collect();
    let mut c = Chain::new();
    c.edge(&tpl_sim(b0, b1, &T_PB_INSEAM), "inseam", sa_all, true);
    c.edge(&tpl_sim(b1, b2, &T_PB_CROTCH), "crotch", sa_all, true);
    c.edge(&[b2, b3], "waist", sa_waist, false);
    c.edge_tags(&out_b, &out_tags, true);
    c.edge(&[b5, b0], "hem", o.pant_hem, false);
    let mut back = new_piece("BACK", "trouser", c.finish(), 1, true, "A");
    let mid_b = 0.5 * (b0.x + b5.x);
    back.grain = (v2(mid_b, w_b - 6.0), v2(mid_b, 8.0));

    // ---------------- waistband (half, on fold) ----------------
    let hl = s.half_waist_stretched + BELT_OVERLAP;
    let bh = 2.0 * wb;
    let mut c = Chain::new();
    c.edge(&[v2(0.0, 0.0), v2(0.0, bh)], "cb", 0.0, false);
    c.edge(&[v2(0.0, bh), v2(hl, bh)], "top", sa_waist, false);
    c.edge(&[v2(hl, bh), v2(hl, 0.0)], "end", sa_waist, false);
    // waist seam: front part first (from the end), then the back part up to the fold (back centre)
    let wf = front.tag_len("waist");
    let wbk = back.tag_len("waist");
    let split = v2(hl * wbk / (wf + wbk), 0.0);
    c.edge_tags(&[v2(hl, 0.0), split, v2(0.0, 0.0)], &[("waist_front", sa_waist), ("waist_back", sa_waist)], false);
    let mut belt = new_piece("WAIST- BELT", "trouser", c.finish(), 1, true, "A");
    belt.internal.push(vec![v2(0.0, wb), v2(hl, wb)]);
    belt.grain = (v2(0.0, -1.04), v2(0.0, bh + 1.04));

    // ---------------- drawstring (cut only) ----------------
    let dl = 2.0 * s.drawcord_length + DRAWCORD_INSIDE;
    let mut c = Chain::new();
    c.edge(&[v2(0.0, 0.0), v2(dl, 0.0)], "edge_a", 0.0, false);
    c.edge(&[v2(dl, 0.0), v2(dl, DRAWCORD_WIDTH)], "edge_b", 0.0, false);
    c.edge(&[v2(dl, DRAWCORD_WIDTH), v2(0.0, DRAWCORD_WIDTH)], "edge_c", 0.0, false);
    c.edge(&[v2(0.0, DRAWCORD_WIDTH), v2(0.0, 0.0)], "edge_d", 0.0, false);
    let mut cord = new_piece("DRAWSTRING", "trouser", c.finish(), 1, false, "");
    cord.grain = (v2(dl * 0.05, DRAWCORD_WIDTH / 2.0), v2(dl * 0.95, DRAWCORD_WIDTH / 2.0));

    let pieces = vec![belt, front, back, pkt, facing, cord, facing1];
    let seams = vec![
        sm_tag("FRONT", "outseam", "BACK", "outseam", false),
        sm_tag("FRONT", "inseam", "BACK", "inseam", false),
        sm_tag("FRONT", "crotch", "FRONT", "crotch", false),
        sm_tag("BACK", "crotch", "BACK", "crotch", false),
        sm_tag("WAIST- BELT", "cb", "WAIST- BELT", "cb", false),
        sm_tag("FRONT", "waist", "WAIST- BELT", "waist_front", false),
        sm_tag("BACK", "waist", "WAIST- BELT", "waist_back", true),
        sm_tag("BACK", "outseam_top", "PKT-IN", "opening", false),
        sm_tag("FRONT", "pocket", "FACING1", "opening", false),
        sm_tag("FACING", "bag", "PKT-IN", "top", false),
    ];
    Ok(Pattern { style: "pant-1074664".into(), size: "BASE".into(), garment: "pant".into(), pieces, seams })
}

/// Alias of `draft_pant_detailed`.
pub fn draft_pant(s: &PantSpec, o: &GarmentOpts) -> Result<Pattern, String> {
    draft_pant_detailed(s, o)
}

// ---------------------------------------------------------------------------------------
// validation, metadata, geometry report
// ---------------------------------------------------------------------------------------

/// The sanity checks used for every draft: finite coordinates, positive area, simple
/// (non-self-intersecting) sew and cut outlines, every seam tag present on both pieces.
pub fn check_pattern(p: &Pattern) -> Result<(), String> {
    for pc in &p.pieces {
        if pc.nodes.len() < 3 {
            return Err(format!("{}: fewer than 3 nodes", pc.name));
        }
        for n in &pc.nodes {
            let all = [n.p.x, n.p.y, n.hin.x, n.hin.y, n.hout.x, n.hout.y];
            if all.iter().any(|v| !v.is_finite()) {
                return Err(format!("{}: non-finite coordinate", pc.name));
            }
        }
        let (sew, cut) = crate::export::cut_outline(pc);
        if signed_area(&sew).abs() < 1.0 {
            return Err(format!("{}: degenerate area", pc.name));
        }
        if crate::mesh::self_intersects(&sew) {
            return Err(format!("{}: sew outline self-intersects", pc.name));
        }
        if cut.iter().any(|q| !q.x.is_finite() || !q.y.is_finite()) || signed_area(&cut).abs() < signed_area(&sew).abs() * 0.999 {
            return Err(format!("{}: invalid cut outline", pc.name));
        }
        if crate::mesh::self_intersects(&cut) {
            return Err(format!("{}: cut outline self-intersects (check seam allowances)", pc.name));
        }
    }
    for s in &p.seams {
        for (pn, tg) in [(&s.a_piece, &s.a_tag), (&s.b_piece, &s.b_tag)] {
            match p.piece(pn) {
                Some(pc) if pc.find_edge(tg).is_some() => {}
                _ => return Err(format!("seam references missing edge {}:{}", pn, tg)),
            }
        }
    }
    Ok(())
}

/// Production metadata of a piece (from the sample's PIECE records).
#[derive(Clone, Debug, PartialEq)]
pub struct PieceMeta {
    pub name: String,
    /// Total quantity per garment (both sides counted), as in the sample.
    pub qty: u32,
    /// Material code ("A" = main, "SELF" when blank in the sample).
    pub material: String,
    /// Sample flag HALF=CLOSE: drawn as one half and cut on the fold.
    pub half: bool,
    /// NESTING_ENABLES rotation allowed (the sample allows 180 deg).
    pub rotation_ok: bool,
    /// NESTING_ENABLES OPPOSITE="Up/Down": the piece may be flipped for opposite pairs.
    pub opposite: bool,
}

pub fn is_fold_piece(p: &Piece) -> bool {
    p.nodes.iter().any(|n| n.edge == "cb" || n.edge == "cf")
}

/// Per-piece production metadata of a drafted shirt/pant pattern (quantities as in the sample).
pub fn piece_meta(p: &Pattern) -> Vec<PieceMeta> {
    p.pieces
        .iter()
        .map(|pc| {
            let half = is_fold_piece(pc);
            let qty = if half { pc.qty } else { pc.qty * if pc.mirror { 2 } else { 1 } };
            // OPPOSITE="Up/Down" in the sample for every pair-cut piece and the two-ply yoke/collar
            let opposite = match (p.garment.as_str(), pc.name.as_str()) {
                ("shirt", "back") | ("shirt", "BND TOP") | ("shirt", "BND IN") => false,
                ("pant", "WAIST- BELT") | ("pant", "DRAWSTRING") => false,
                _ => true,
            };
            PieceMeta { name: pc.name.clone(), qty, material: pc.material.clone(), half, rotation_ok: true, opposite }
        })
        .collect()
}

/// Geometry report comparable to Optitex `GEOM_INFO`.
#[derive(Clone, Debug)]
pub struct GeomInfo {
    /// Cut-outline bounding box of the drawn piece (the half for fold pieces).
    pub width: f64,
    pub height: f64,
    /// Cut area in m^2 (closed full piece for fold pieces).
    pub area_m2: f64,
    /// Cut perimeter (closed full piece for fold pieces).
    pub perimeter: f64,
    /// Sew-line area in m^2 and perimeter.
    pub sew_area_m2: f64,
    pub sew_perimeter: f64,
    pub fold: bool,
}

pub fn geom_info(pc: &Piece) -> GeomInfo {
    let (sew, cut) = crate::export::cut_outline(pc);
    let fold = is_fold_piece(pc);
    let (mut lo, mut hi) = (cut[0], cut[0]);
    for q in &cut {
        lo = v2(lo.x.min(q.x), lo.y.min(q.y));
        hi = v2(hi.x.max(q.x), hi.y.max(q.y));
    }
    let perim = |p: &[V2]| -> f64 { (0..p.len()).map(|i| p[i].dist(p[(i + 1) % p.len()])).sum() };
    let (mut a_cut, mut p_cut) = (signed_area(&cut).abs(), perim(&cut));
    let (mut a_sew, mut p_sew) = (signed_area(&sew).abs(), perim(&sew));
    if fold {
        let fold_sew: f64 = (0..pc.nodes.len()).filter(|&i| pc.nodes[i].edge == "cb" || pc.nodes[i].edge == "cf").map(|i| pc.edge_len(i)).sum();
        let on: Vec<f64> = cut.iter().filter(|q| q.x.abs() < 1e-7).map(|q| q.y).collect();
        let fold_cut = if on.len() >= 2 {
            on.iter().cloned().fold(f64::MIN, f64::max) - on.iter().cloned().fold(f64::MAX, f64::min)
        } else {
            fold_sew
        };
        a_cut *= 2.0;
        a_sew *= 2.0;
        p_cut = 2.0 * (p_cut - fold_cut);
        p_sew = 2.0 * (p_sew - fold_sew);
    }
    GeomInfo { width: hi.x - lo.x, height: hi.y - lo.y, area_m2: a_cut / 1e4, perimeter: p_cut, sew_area_m2: a_sew / 1e4, sew_perimeter: p_sew, fold }
}

/// Fit / consistency checks of a drafted shirt or pant (seam-length matches, cap ease ...).
pub fn garment_checks(p: &Pattern) -> Vec<Check> {
    let mut c = Vec::new();
    let len = |pn: &str, tag: &str| p.piece(pn).map(|x| x.tag_len(tag));
    let mut add = |name: &str, v: Option<f64>, e: Option<f64>, tol: f64| {
        if let (Some(v), Some(e)) = (v, e) {
            c.push(Check { name: name.into(), value: v, expected: e, tol });
        }
    };
    if p.garment == "shirt" {
        add("Side seam (FRT vs back)", len("FRT", "side"), len("back", "side"), 0.3);
        add("Shoulder seam (FRT vs yoke)", len("FRT", "shoulder"), len("back YK", "shoulder"), 0.6);
        add("Yoke seam (back vs yoke)", len("back", "yokeseam"), len("back YK", "yokeseam"), 0.3);
        add("Stand pieces equal", len("BND TOP", "neck_front"), len("BND IN", "neck_front"), 0.01);
        let arm = len("FRT", "armhole").zip(len("back", "armhole")).zip(len("back YK", "armhole")).map(|((a, b), c)| a + b + c);
        let cap = ["cap_front", "cap_yoke", "cap_back"].iter().map(|t| len("Sleeve", t)).sum::<Option<f64>>();
        add("Sleeve cap ease (cap - armhole, sample 3.9)", cap.zip(arm).map(|(c, a)| c - a), Some(3.93), 2.5);
        let neck = len("FRT", "neck").zip(len("back YK", "neck")).map(|(a, b)| a + b);
        add("Neck opening vs stand (sample: stand 0.94 longer)", len("BND IN", "neck_front").zip(len("BND IN", "neck_back")).zip(neck).map(|((f, b), n)| f + b - n), Some(0.94), 2.0);
    } else if p.garment == "pant" {
        add("Inseam (FRONT vs BACK)", len("FRONT", "inseam"), len("BACK", "inseam"), 0.6);
        // the full side seam: FRONT outseam + pocket opening vs BACK outseam + outseam_top
        add("Side seam (FRONT outseam+pocket vs BACK outseam+outseam_top)", len("FRONT", "outseam").zip(len("FRONT", "pocket")).map(|(a, b)| a + b), len("BACK", "outseam").zip(len("BACK", "outseam_top")).map(|(a, b)| a + b), 1.0);
        add("Pocket bag opening (PKT-IN vs BACK side-seam top, sample +0.3)", len("PKT-IN", "opening").map(|v| v + BAG_OPENING_EASE), len("BACK", "outseam_top"), 0.3);
        add("Pocket facing (PKT-IN diag vs FACING1 long, sample 0.3)", len("PKT-IN", "diag"), len("FACING1", "long").map(|v| v - 0.3), 0.6);
        add("Pocket opening (FRONT vs FACING1)", len("FRONT", "pocket"), len("FACING1", "opening"), 1.0);
        add("Pocket bag top (FACING vs PKT-IN)", len("FACING", "bag"), len("PKT-IN", "top"), 0.3);
    }
    c
}

// ---------------------------------------------------------------------------------------
// grading
// ---------------------------------------------------------------------------------------

/// Draft every size from its spec column.  `kind` = "shirt" | "pant" (also "pants",
/// "trousers").  `base` holds spec values shared by all sizes (may be empty); each
/// `per_size` entry (size label, spec map) overrides/extends it.  Maps are keyed like
/// `ShirtSpec::from_map` / `PantSpec::from_pom`.  Returns (size label, pattern) in order.
pub fn grade_garment(kind: &str, base: &BTreeMap<String, f64>, per_size: &[(String, BTreeMap<String, f64>)]) -> Result<Vec<(String, Pattern)>, String> {
    grade_garment_opts(kind, base, per_size, &GarmentOpts::default())
}

pub fn grade_garment_opts(kind: &str, base: &BTreeMap<String, f64>, per_size: &[(String, BTreeMap<String, f64>)], o: &GarmentOpts) -> Result<Vec<(String, Pattern)>, String> {
    let k = norm_key(kind);
    let is_shirt = match k.as_str() {
        "shirt" => true,
        "pant" | "pants" | "trouser" | "trousers" => false,
        _ => return Err(format!("unknown garment kind '{}' (shirt | pant)", kind)),
    };
    if per_size.is_empty() {
        return Err("grade_garment needs at least one size".into());
    }
    let mut out = Vec::new();
    for (size, m) in per_size {
        let mut merged = base.clone();
        for (k, v) in m {
            merged.insert(k.clone(), *v);
        }
        let mut pat = if is_shirt {
            let (spec, warn) = ShirtSpec::from_map_checked(&merged);
            let _ = warn;
            draft_shirt(&spec, o).map_err(|e| format!("size {}: {}", size, e))?
        } else {
            let (spec, warn) = PantSpec::from_pom_checked(&merged);
            let _ = warn;
            draft_pant_detailed(&spec, o).map_err(|e| format!("size {}: {}", size, e))?
        };
        pat.size = size.clone();
        out.push((size.clone(), pat));
    }
    Ok(out)
}

// ---------------------------------------------------------------------------------------
// reference data: GEOM_INFO of the two sample XML files (Optitex 21.4 "Piece info" export)
// ---------------------------------------------------------------------------------------

/// Per-piece, per-size `GEOM_INFO` of the sample files, used to validate the drafters.
/// `x`/`y` are SIZE_X/SIZE_Y (cut outline bounding box; the HALF piece for HALF=CLOSE),
/// `area` in m^2 and `per` in cm are those of the closed full piece; `sew_*` are NaN when the
/// piece has no sew line (DRAWSTRING).
pub mod reference {
    #[derive(Clone, Copy, Debug)]
    pub struct RefRow {
        pub size: &'static str,
        pub x: f64,
        pub y: f64,
        pub area: f64,
        pub per: f64,
        pub sew_area: f64,
        pub sew_per: f64,
    }
    #[derive(Clone, Copy, Debug)]
    pub struct RefPiece {
        pub name: &'static str,
        /// SIZE_X is the extent along this crate's y axis (length direction) when true.
        pub x_is_height: bool,
        pub half: bool,
        pub qty: u32,
        pub rows: &'static [RefRow],
    }
    pub const SHIRT_SIZES: [&str; 6] = ["S", "M", "L", "XL", "XXL", "3XL"];
    pub const PANT_SIZES: [&str; 5] = ["XS", "S", "M", "L", "XL"];
pub const SHIRT_REF: &[RefPiece] = &[
        RefPiece { name: "FRT", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "S", x: 75.9019, y: 35.0750, area: 0.2363, per: 214.1949, sew_area: 0.2041, sew_per: 199.7011 },
            RefRow { size: "M", x: 77.3943, y: 36.0749, area: 0.2474, per: 218.8856, sew_area: 0.2144, sew_per: 204.4013 },
            RefRow { size: "L", x: 78.8880, y: 37.0748, area: 0.2588, per: 223.5822, sew_area: 0.2250, sew_per: 209.1049 },
            RefRow { size: "XL", x: 80.8817, y: 38.5747, area: 0.2751, per: 230.1417, sew_area: 0.2402, sew_per: 215.6613 },
            RefRow { size: "XXL", x: 81.8785, y: 40.0746, area: 0.2879, per: 234.7061, sew_area: 0.2521, sew_per: 220.2213 },
            RefRow { size: "3XL", x: 82.8778, y: 41.5746, area: 0.3008, per: 239.2757, sew_area: 0.2643, sew_per: 224.7846 },
        ] },
        RefPiece { name: "back", x_is_height: true, half: true, qty: 1, rows: &[
            RefRow { size: "S", x: 64.9969, y: 29.4688, area: 0.3594, per: 235.8176, sew_area: 0.3165, sew_per: 220.5344 },
            RefRow { size: "M", x: 66.4960, y: 30.4679, area: 0.3797, per: 242.5326, sew_area: 0.3356, sew_per: 227.2589 },
            RefRow { size: "L", x: 67.9952, y: 31.4670, area: 0.4005, per: 249.2749, sew_area: 0.3552, sew_per: 234.0001 },
            RefRow { size: "XL", x: 68.9942, y: 32.9676, area: 0.4254, per: 256.8224, sew_area: 0.3786, sew_per: 241.4680 },
            RefRow { size: "XXL", x: 69.9934, y: 34.4670, area: 0.4494, per: 264.2825, sew_area: 0.4013, sew_per: 248.8841 },
            RefRow { size: "3XL", x: 70.9927, y: 35.9665, area: 0.4737, per: 271.7593, sew_area: 0.4243, sew_per: 256.3084 },
        ] },
        RefPiece { name: "back YK", x_is_height: true, half: true, qty: 2, rows: &[
            RefRow { size: "S", x: 19.4861, y: 25.3786, area: 0.0791, per: 133.7766, sew_area: 0.0667, sew_per: 125.9974 },
            RefRow { size: "M", x: 19.4866, y: 26.1795, area: 0.0814, per: 136.8171, sew_area: 0.0687, sew_per: 129.0398 },
            RefRow { size: "L", x: 19.4871, y: 26.9803, area: 0.0837, per: 139.8603, sew_area: 0.0707, sew_per: 132.0860 },
            RefRow { size: "XL", x: 20.4874, y: 27.9772, area: 0.0920, per: 145.7008, sew_area: 0.0784, sew_per: 137.9110 },
            RefRow { size: "XXL", x: 20.4875, y: 28.9742, area: 0.0951, per: 149.5365, sew_area: 0.0812, sew_per: 141.7512 },
            RefRow { size: "3XL", x: 20.4875, y: 29.9718, area: 0.0983, per: 153.3787, sew_area: 0.0839, sew_per: 145.5980 },
        ] },
        RefPiece { name: "CLR", x_is_height: false, half: true, qty: 2, rows: &[
            RefRow { size: "S", x: 22.2968, y: 9.6583, area: 0.0336, per: 103.2895, sew_area: 0.0209, sew_per: 92.5413 },
            RefRow { size: "M", x: 23.2960, y: 9.7545, area: 0.0351, per: 107.3040, sew_area: 0.0219, sew_per: 96.5645 },
            RefRow { size: "L", x: 24.2953, y: 9.8538, area: 0.0366, per: 111.3196, sew_area: 0.0229, sew_per: 100.5879 },
            RefRow { size: "XL", x: 25.2946, y: 9.9536, area: 0.0382, per: 115.3362, sew_area: 0.0239, sew_per: 104.6116 },
            RefRow { size: "XXL", x: 26.2940, y: 10.0534, area: 0.0397, per: 119.3535, sew_area: 0.0248, sew_per: 108.6354 },
            RefRow { size: "3XL", x: 27.2934, y: 10.1532, area: 0.0412, per: 123.3715, sew_area: 0.0258, sew_per: 112.6593 },
        ] },
        RefPiece { name: "BND TOP", x_is_height: false, half: true, qty: 1, rows: &[
            RefRow { size: "S", x: 23.9288, y: 8.0877, area: 0.0273, per: 102.5696, sew_area: 0.0145, sew_per: 93.4403 },
            RefRow { size: "M", x: 24.9287, y: 8.2377, area: 0.0285, per: 106.6323, sew_area: 0.0152, sew_per: 97.5033 },
            RefRow { size: "L", x: 25.9286, y: 8.3878, area: 0.0298, per: 110.6953, sew_area: 0.0160, sew_per: 101.5666 },
            RefRow { size: "XL", x: 26.9285, y: 8.5379, area: 0.0311, per: 114.7587, sew_area: 0.0167, sew_per: 105.6300 },
            RefRow { size: "XXL", x: 27.9285, y: 8.6879, area: 0.0324, per: 118.8223, sew_area: 0.0175, sew_per: 109.6936 },
            RefRow { size: "3XL", x: 28.9284, y: 8.8380, area: 0.0337, per: 122.8861, sew_area: 0.0182, sew_per: 113.7573 },
        ] },
        RefPiece { name: "BND IN", x_is_height: false, half: true, qty: 1, rows: &[
            RefRow { size: "S", x: 23.9288, y: 8.0876, area: 0.0273, per: 102.5695, sew_area: 0.0145, sew_per: 93.4401 },
            RefRow { size: "M", x: 24.9287, y: 8.2377, area: 0.0285, per: 106.6322, sew_area: 0.0152, sew_per: 97.5032 },
            RefRow { size: "L", x: 25.9286, y: 8.3877, area: 0.0298, per: 110.6952, sew_area: 0.0160, sew_per: 101.5664 },
            RefRow { size: "XL", x: 26.9285, y: 8.5378, area: 0.0311, per: 114.7585, sew_area: 0.0167, sew_per: 105.6299 },
            RefRow { size: "XXL", x: 27.9284, y: 8.6879, area: 0.0324, per: 118.8222, sew_area: 0.0175, sew_per: 109.6935 },
            RefRow { size: "3XL", x: 28.9284, y: 8.8379, area: 0.0337, per: 122.8860, sew_area: 0.0182, sew_per: 113.7572 },
        ] },
        RefPiece { name: "Sleeve", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "S", x: 29.0049, y: 43.2359, area: 0.0922, per: 121.2855, sew_area: 0.0729, sew_per: 109.8292 },
            RefRow { size: "M", x: 29.5047, y: 45.4216, area: 0.0980, per: 125.5410, sew_area: 0.0778, sew_per: 113.9688 },
            RefRow { size: "L", x: 30.0048, y: 47.6049, area: 0.1039, per: 129.8272, sew_area: 0.0829, sew_per: 118.1380 },
            RefRow { size: "XL", x: 30.5062, y: 50.9131, area: 0.1118, per: 135.6950, sew_area: 0.0897, sew_per: 123.7409 },
            RefRow { size: "XXL", x: 31.0095, y: 54.2195, area: 0.1199, per: 141.6601, sew_area: 0.0967, sew_per: 129.4279 },
            RefRow { size: "3XL", x: 31.5153, y: 57.5241, area: 0.1283, per: 147.7086, sew_area: 0.1039, sew_per: 135.1876 },
        ] },
    ];

    pub const PANT_REF: &[RefPiece] = &[
        RefPiece { name: "WAIST- BELT", x_is_height: false, half: true, qty: 1, rows: &[
            RefRow { size: "XS", x: 50.7999, y: 13.0000, area: 0.1321, per: 229.1997, sew_area: 0.1030, sew_per: 218.7997 },
            RefRow { size: "S", x: 52.7999, y: 13.0000, area: 0.1373, per: 237.1997, sew_area: 0.1071, sew_per: 226.7997 },
            RefRow { size: "M", x: 54.7999, y: 13.0000, area: 0.1425, per: 245.1997, sew_area: 0.1113, sew_per: 234.7997 },
            RefRow { size: "L", x: 57.2999, y: 13.0000, area: 0.1490, per: 255.1997, sew_area: 0.1165, sew_per: 244.7997 },
            RefRow { size: "XL", x: 59.7999, y: 13.0000, area: 0.1555, per: 265.1997, sew_area: 0.1217, sew_per: 254.7997 },
        ] },
        RefPiece { name: "FRONT", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "XS", x: 106.8282, y: 30.7801, area: 0.3044, per: 265.7734, sew_area: 0.2764, sew_per: 256.3480 },
            RefRow { size: "S", x: 108.8272, y: 31.8795, area: 0.3192, per: 271.5314, sew_area: 0.2905, sew_per: 262.0949 },
            RefRow { size: "M", x: 111.1265, y: 32.9790, area: 0.3352, per: 277.8832, sew_area: 0.3057, sew_per: 268.4301 },
            RefRow { size: "L", x: 113.4257, y: 34.3786, area: 0.3549, per: 284.8386, sew_area: 0.3245, sew_per: 275.3694 },
            RefRow { size: "XL", x: 115.7249, y: 35.7782, area: 0.3751, per: 291.7976, sew_area: 0.3439, sew_per: 282.3128 },
        ] },
        RefPiece { name: "BACK", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "XS", x: 110.9391, y: 39.9052, area: 0.3640, per: 285.9713, sew_area: 0.3335, sew_per: 275.9798 },
            RefRow { size: "S", x: 112.9337, y: 41.0004, area: 0.3797, per: 291.6278, sew_area: 0.3486, sew_per: 281.6504 },
            RefRow { size: "M", x: 115.2291, y: 42.0947, area: 0.3966, per: 297.8944, sew_area: 0.3648, sew_per: 287.9280 },
            RefRow { size: "L", x: 117.5233, y: 43.4896, area: 0.4174, per: 304.7685, sew_area: 0.3848, sew_per: 294.8121 },
            RefRow { size: "XL", x: 119.8180, y: 44.8852, area: 0.4387, per: 311.6537, sew_area: 0.4054, sew_per: 301.7053 },
        ] },
        RefPiece { name: "PKT-IN", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "XS", x: 27.8864, y: 34.6248, area: 0.0836, per: 112.0363, sew_area: 0.0720, sew_per: 104.0761 },
            RefRow { size: "S", x: 27.8864, y: 34.6248, area: 0.0836, per: 112.0363, sew_area: 0.0720, sew_per: 104.0761 },
            RefRow { size: "M", x: 28.9132, y: 36.6185, area: 0.0925, per: 118.0288, sew_area: 0.0803, sew_per: 110.0605 },
            RefRow { size: "L", x: 28.9132, y: 36.6185, area: 0.0925, per: 118.0288, sew_area: 0.0803, sew_per: 110.0605 },
            RefRow { size: "XL", x: 29.9714, y: 38.6138, area: 0.1018, per: 124.0292, sew_area: 0.0890, sew_per: 116.0525 },
        ] },
        RefPiece { name: "FACING", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "XS", x: 26.3589, y: 11.3571, area: 0.0213, per: 67.4850, sew_area: 0.0147, sew_per: 58.2476 },
            RefRow { size: "S", x: 26.3589, y: 11.3571, area: 0.0213, per: 67.4850, sew_area: 0.0147, sew_per: 58.2476 },
            RefRow { size: "M", x: 27.3429, y: 11.8727, area: 0.0228, per: 70.0596, sew_area: 0.0160, sew_per: 60.8308 },
            RefRow { size: "L", x: 27.3429, y: 11.8727, area: 0.0228, per: 70.0596, sew_area: 0.0160, sew_per: 60.8308 },
            RefRow { size: "XL", x: 28.3290, y: 12.3875, area: 0.0244, per: 72.6394, sew_area: 0.0173, sew_per: 63.4172 },
        ] },
        RefPiece { name: "DRAWSTRING", x_is_height: false, half: false, qty: 1, rows: &[
            RefRow { size: "XS", x: 165.0000, y: 4.0000, area: 0.0660, per: 338.0000, sew_area: f64::NAN, sew_per: f64::NAN },
            RefRow { size: "S", x: 165.0000, y: 4.0000, area: 0.0660, per: 338.0000, sew_area: f64::NAN, sew_per: f64::NAN },
            RefRow { size: "M", x: 165.0000, y: 4.0000, area: 0.0660, per: 338.0000, sew_area: f64::NAN, sew_per: f64::NAN },
            RefRow { size: "L", x: 165.0000, y: 4.0000, area: 0.0660, per: 338.0000, sew_area: f64::NAN, sew_per: f64::NAN },
            RefRow { size: "XL", x: 165.0000, y: 4.0000, area: 0.0660, per: 338.0000, sew_area: f64::NAN, sew_per: f64::NAN },
        ] },
        RefPiece { name: "FACING1", x_is_height: true, half: false, qty: 2, rows: &[
            RefRow { size: "XS", x: 23.9863, y: 10.6209, area: 0.0115, per: 57.2847, sew_area: 0.0061, sew_per: 48.7982 },
            RefRow { size: "S", x: 23.9863, y: 10.6209, area: 0.0115, per: 57.2847, sew_area: 0.0061, sew_per: 48.7982 },
            RefRow { size: "M", x: 24.9880, y: 10.5980, area: 0.0122, per: 59.2189, sew_area: 0.0065, sew_per: 50.7492 },
            RefRow { size: "L", x: 24.9880, y: 10.5980, area: 0.0122, per: 59.2189, sew_area: 0.0065, sew_per: 50.7492 },
            RefRow { size: "XL", x: 25.9896, y: 10.5774, area: 0.0128, per: 61.1590, sew_area: 0.0070, sew_per: 52.7041 },
        ] },
    ];
    }

/// Shirt spec columns S..3XL (public so `calib` and the tests share one definition).
/// The shirt tech pack has no graded chart, so the columns are the base spec plus the
/// size increments implied by the XML grading (documented in docs/GARMENTS.md); the shirt
/// validation is therefore reproductive, not an independent spec->pattern check.
pub fn shirt_columns() -> Vec<(String, BTreeMap<String, f64>)> {
    let d = ShirtSpec::default();
    // cumulative offsets relative to L for sizes S, M, L, XL, XXL, 3XL
    let chest = [-4.0, -2.0, 0.0, 3.0, 6.0, 9.0];
    let shoulder = [-3.2, -1.6, 0.0, 2.0, 4.0, 6.0];
    let length = [-3.0, -1.5, 0.0, 2.0, 3.0, 4.0];
    let yoke = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0];
    let sleeve = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5];
    let bicep = [-2.18, -1.09, 0.0, 1.655, 3.31, 4.965];
    let neck = [-4.0, -2.0, 0.0, 2.0, 4.0, 6.0];
    let stand = [0.0; 6];
    let point = [-0.10, -0.05, 0.0, 0.05, 0.10, 0.15];
    let mut out = Vec::new();
    for (i, sz) in reference::SHIRT_SIZES.iter().enumerate() {
        let mut mm = BTreeMap::new();
        mm.insert("half_chest".into(), d.half_chest + chest[i]);
        mm.insert("half_hem".into(), d.half_hem + chest[i]);
        mm.insert("across_shoulder".into(), d.across_shoulder + shoulder[i]);
        mm.insert("across_chest".into(), d.across_chest + shoulder[i]);
        mm.insert("across_back".into(), d.across_back + shoulder[i]);
        mm.insert("body_length_hps".into(), d.body_length_hps + length[i]);
        mm.insert("back_length_cb".into(), d.back_length_cb + length[i]);
        mm.insert("yoke_depth".into(), d.yoke_depth + yoke[i]);
        mm.insert("sleeve_length".into(), d.sleeve_length + sleeve[i]);
        mm.insert("bicep".into(), d.bicep + bicep[i]);
        mm.insert("sleeve_opening".into(), d.sleeve_opening + SHIRT_SLEEVE_OPENING_GROWTH * bicep[i]);
        mm.insert("neck_size".into(), d.neck_size + neck[i]);
        mm.insert("front_neck_width".into(), d.front_neck_width + 0.2 * neck[i]);
        mm.insert("back_neck_width".into(), d.back_neck_width + 0.2 * neck[i]);
        mm.insert("stand_height".into(), d.stand_height + stand[i]);
        mm.insert("armhole_drop".into(), d.armhole_drop + SHIRT_ARMHOLE_DROP_GROWTH * chest[i]);
        mm.insert("shoulder_slope".into(), d.shoulder_slope + SHIRT_SHOULDER_SLOPE_GROWTH * shoulder[i]);
        mm.insert("sleeve_underarm_height".into(), d.sleeve_underarm_height + SHIRT_UNDERARM_HEIGHT_GROWTH * bicep[i]);
        mm.insert("collar_point_length".into(), d.collar_point_length + point[i]);
        out.push((sz.to_string(), mm));
    }
    out
}

/// Pant spec columns XS..XL from the graded chart CL1086464.xlsx (POM-keyed).  Note: that
/// xlsx is a DIFFERENT, related style than the PDS pant 1074664, so its grading increments
/// differ slightly from the PDS's own (see docs/CALIBRATION.md); the base size S coincides.
pub fn pant_columns() -> Vec<(String, BTreeMap<String, f64>)> {
    let rows: &[(&str, [f64; 5])] = &[
        ("20125", [33.0, 35.0, 37.0, 39.5, 42.0]),
        ("20245", [47.0, 49.0, 51.0, 53.5, 56.0]),
        ("20305-A", [16.5, 17.0, 17.5, 18.0, 18.5]),
        ("20305-B", [15.5, 16.0, 16.5, 17.0, 17.5]),
        ("20305", [50.0, 52.0, 54.0, 56.5, 59.0]),
        ("20865", [32.0, 33.0, 34.0, 35.3, 36.6]),
        ("21505", [29.5, 30.5, 31.5, 32.8, 34.1]),
        ("21545", [40.0, 41.0, 42.0, 43.3, 44.6]),
        ("20905", [29.3, 30.0, 30.7, 31.7, 32.7]),
        ("21125", [29.3, 30.0, 30.7, 31.7, 32.7]),
        ("30210", [2.8; 5]),
        ("21885", [77.0, 78.0, 79.0, 80.0, 81.0]),
        ("20265", [5.2; 5]),
        ("22145", [3.0, 3.0, 3.5, 3.5, 4.0]),
        ("22165", [15.5, 15.5, 16.0, 16.0, 16.5]),
        ("22565", [24.0; 5]),
        ("30845", [30.0; 5]),
    ];
    reference::PANT_SIZES
        .iter()
        .enumerate()
        .map(|(i, sz)| (sz.to_string(), rows.iter().map(|(k, v)| (k.to_string(), v[i])).collect()))
        .collect()
}

/// Pant spec columns IMPLIED BY THE PDS'S OWN GRADING.  The xlsx chart (`pant_columns`) belongs
/// to a related but different style: widths (seat, thigh, leg opening, pockets) grade the same
/// way, but the PDS grows front and back length by 2.0 / 2.3 / 2.3 / 2.29 cm per size step
/// (inseam +1.0 each, so rise +1.0 / +1.3 / +1.3 / +1.29) where the chart has rise steps
/// 1.0 / 1.0 / 1.3 / 1.3.  This set corrects exactly those two rows (front and back rise) so
/// the drafter can be judged against the PDS without the chart mismatch.
pub fn pant_columns_pds() -> Vec<(String, BTreeMap<String, f64>)> {
    let mut cols = pant_columns();
    let front = [29.5, 30.5, 31.8, 33.1, 34.39];
    let back = [40.0, 41.0, 42.3, 43.6, 44.89];
    for (i, (_, m)) in cols.iter_mut().enumerate() {
        m.insert("21505".into(), front[i]);
        m.insert("21545".into(), back[i]);
    }
    cols
}

#[cfg(test)]
mod tests {
    use super::reference::*;
    use super::*;

    /// Shirt spec columns S..3XL (delegates to the public `shirt_columns`).
    pub fn shirt_columns() -> Vec<(String, BTreeMap<String, f64>)> {
        super::shirt_columns()
    }

    /// Pant spec columns XS..XL (delegates to the public `pant_columns`).
    pub fn pant_columns() -> Vec<(String, BTreeMap<String, f64>)> {
        super::pant_columns()
    }

    fn rel(a: f64, b: f64) -> f64 {
        100.0 * (a - b) / b
    }

    fn table(kind: &str, refs: &[RefPiece], cols: &[(String, BTreeMap<String, f64>)]) -> (String, Vec<(String, String, [f64; 6])>) {
        let graded = grade_garment(kind, &BTreeMap::new(), cols).expect("grading");
        let mut s = String::new();
        let mut errs = Vec::new();
        s += &format!("{:<12}{:<5}{:>8}{:>8} |{:>7}{:>7} |{:>7}{:>7} |{:>7}{:>7} |{:>7}{:>7} |{:>7}{:>7} |{:>7}{:>7}\n", "piece", "size", "X", "Xref", "Y", "Yref", "area", "ref", "per", "ref", "sarea", "ref", "sper", "ref", "dX%", "dY%");
        for rp in refs {
            for row in rp.rows {
                let pat = &graded.iter().find(|(sz, _)| sz == row.size).unwrap().1;
                let pc = pat.piece(rp.name).unwrap_or_else(|| panic!("missing piece {}", rp.name));
                let g = geom_info(pc);
                let (x, y) = if rp.x_is_height { (g.height, g.width) } else { (g.width, g.height) };
                let e = [rel(x, row.x), rel(y, row.y), rel(g.area_m2, row.area), rel(g.perimeter, row.per),
                    if row.sew_area.is_nan() { 0.0 } else { rel(g.sew_area_m2, row.sew_area) },
                    if row.sew_per.is_nan() { 0.0 } else { rel(g.sew_perimeter, row.sew_per) }];
                s += &format!("{:<12}{:<5}{:>8.2}{:>8.2} |{:>7.2}{:>7.2} |{:>7.4}{:>7.4} |{:>7.1}{:>7.1} |{:>7.4}{:>7.4} |{:>7.1}{:>7.1} |{:>7.2}{:>7.2}  area {:+.1}% per {:+.1}% sarea {:+.1}% sper {:+.1}%\n",
                    rp.name, row.size, x, row.x, y, row.y, g.area_m2, row.area, g.perimeter, row.per, g.sew_area_m2, row.sew_area, g.sew_perimeter, row.sew_per, e[0], e[1], e[2], e[3], e[4], e[5]);
                errs.push((rp.name.to_string(), row.size.to_string(), e));
            }
        }
        (s, errs)
    }

    #[test]
    fn diagnostic_tables() {
        let (st, _) = table("shirt", SHIRT_REF, &shirt_columns());
        println!("=== SHIRT 1078375 vs XML GEOM_INFO (errors in % of XML) ===\n{}", st);
        let (pt, _) = table("pant", PANT_REF, &pant_columns());
        println!("=== PANT 1074664 vs XML GEOM_INFO ===\n{}", pt);
    }

    /// Achieved error bounds, asserted: every piece, every size of both sample files.
    #[test]
    fn geometry_matches_xml_within_documented_error() {
        // Limits sit just above the residuals reached by the calibration (docs/CALIBRATION.md) so
        // that regressions are caught.  [dX, dY, area, perimeter, sew area, sew perimeter] in %.
        let cases: [(&str, &[RefPiece], Vec<(String, BTreeMap<String, f64>)>, [f64; 6]); 3] = [
            ("shirt", SHIRT_REF, shirt_columns(), [1.3, 1.3, 1.0, 1.1, 1.6, 1.0]),
            ("pant", PANT_REF, pant_columns(), [0.45, 0.2, 0.6, 0.5, 0.6, 0.5]),
            ("pant", PANT_REF, pant_columns_pds(), [0.4, 0.2, 0.4, 0.3, 0.6, 0.3]),
        ];
        for (kind, refs, cols, lim) in cases.iter() {
            let (_, errs) = table(kind, refs, cols);
            for (piece, size, e) in errs {
                for k in 0..6 {
                    assert!(e[k].abs() <= lim[k], "{} {} {}: metric {} off by {:+.2}% (limit {})", kind, piece, size, k, e[k], lim[k]);
                }
            }
        }
    }

    #[test]
    fn base_sizes_are_valid_drafts_with_sample_names_and_quantities() {
        let o = GarmentOpts::default();
        for (pat, refs) in [(draft_shirt(&ShirtSpec::default(), &o).unwrap(), SHIRT_REF), (draft_pant_detailed(&PantSpec::default(), &o).unwrap(), PANT_REF)] {
            let meta = piece_meta(&pat);
            assert_eq!(meta.len(), refs.len());
            for (m, r) in meta.iter().zip(refs) {
                assert_eq!(m.name, r.name);
                assert_eq!(m.qty, r.qty, "{}", m.name);
                assert_eq!(m.half, r.half, "{}", m.name);
                assert!(m.rotation_ok);
            }
            // the fold pieces are joined to themselves, the others are pairs/mirrored
            for pc in &pat.pieces {
                assert!(pc.area() > 10.0 || pc.name == "DRAWSTRING", "{}", pc.name);
                let (pts, _) = pc.flatten(16);
                assert!(!crate::mesh::self_intersects(&pts), "{} self-intersects", pc.name);
                assert!(pts.iter().all(|p| p.x.is_finite() && p.y.is_finite()));
                if is_fold_piece(pc) {
                    assert!(pat.seams.iter().any(|s| s.a_piece == pc.name && s.b_piece == pc.name && s.a_tag == s.b_tag), "{} has no fold seam", pc.name);
                    // the fold edge lies on x = 0
                    assert!(pc.nodes.iter().filter(|n| n.edge == "cb").all(|n| n.p.x.abs() < 1e-9));
                }
            }
            for c in garment_checks(&pat) {
                assert!(c.ok(), "{}: {} vs {} (tol {})", c.name, c.value, c.expected, c.tol);
            }
        }
        // sample details
        let shirt = draft_shirt(&ShirtSpec::default(), &o).unwrap();
        assert_eq!(shirt.pieces.iter().map(|p| p.name.as_str()).collect::<Vec<_>>(), ["FRT", "back", "back YK", "CLR", "BND TOP", "BND IN", "Sleeve"]);
        assert!(!shirt.piece("back YK").unwrap().notches.is_empty() && !shirt.piece("Sleeve").unwrap().notches.is_empty());
        let pant = draft_pant_detailed(&PantSpec::default(), &o).unwrap();
        assert_eq!(pant.pieces.iter().map(|p| p.name.as_str()).collect::<Vec<_>>(), ["WAIST- BELT", "FRONT", "BACK", "PKT-IN", "FACING", "DRAWSTRING", "FACING1"]);
        assert_eq!(pant.piece("PKT-IN").unwrap().notches.len(), 2);
        assert_eq!(pant.piece("FACING").unwrap().notches.len(), 2);
        // hems / allowances measured from the sample: shirt hem 3.5, sleeve hem 1.5, belt 1.3, pant hem 1.5
        let hem = |p: &Pattern, n: &str, tag: &str| p.piece(n).unwrap().nodes.iter().find(|x| x.edge == tag).and_then(|x| x.sa).unwrap();
        assert_eq!(hem(&shirt, "FRT", "hem"), 3.5);
        assert_eq!(hem(&shirt, "Sleeve", "hem"), 1.5);
        assert_eq!(hem(&shirt, "back", "side"), 1.7);
        assert_eq!(hem(&shirt, "FRT", "side"), 0.8);
        assert_eq!(hem(&pant, "FRONT", "hem"), 1.5);
        assert_eq!(hem(&pant, "WAIST- BELT", "top"), 1.3);
        assert_eq!(hem(&pant, "BACK", "outseam"), 1.0);
    }

    #[test]
    fn every_size_valid_and_grading_is_monotonic() {
        let shirt = grade_garment("shirt", &BTreeMap::new(), &shirt_columns()).unwrap();
        let pant = grade_garment("pant", &BTreeMap::new(), &pant_columns()).unwrap();
        assert_eq!(shirt.len(), 6);
        assert_eq!(pant.len(), 5);
        assert_eq!(shirt[2].0, "L");
        assert_eq!(shirt[2].1.size, "L");
        for (_, pat) in shirt.iter().chain(pant.iter()) {
            check_pattern(pat).unwrap();
        }
        let mono = |g: &[(String, Pattern)], piece: &str, f: &dyn Fn(&GeomInfo) -> f64, strict: bool| {
            let v: Vec<f64> = g.iter().map(|(_, p)| f(&geom_info(p.piece(piece).unwrap()))).collect();
            assert!(v.windows(2).all(|w| if strict { w[1] > w[0] } else { w[1] >= w[0] - 1e-9 }), "{} not monotonic: {:?}", piece, v);
        };
        for p in ["FRT", "back", "back YK", "CLR", "BND TOP", "Sleeve"] {
            mono(&shirt, p, &|g| g.area_m2, true);
            mono(&shirt, p, &|g| g.sew_perimeter, true);
        }
        mono(&shirt, "FRT", &|g| g.height, true);
        mono(&shirt, "back", &|g| g.width, true);
        mono(&shirt, "Sleeve", &|g| g.width, true);
        mono(&shirt, "CLR", &|g| g.width, true);
        for p in ["WAIST- BELT", "FRONT", "BACK"] {
            mono(&pant, p, &|g| g.area_m2, true);
        }
        for p in ["PKT-IN", "FACING", "FACING1"] {
            mono(&pant, p, &|g| g.area_m2, false);
        }
        mono(&pant, "FRONT", &|g| g.height, true);
        mono(&pant, "WAIST- BELT", &|g| g.width, true);
        // bigger spec -> bigger pattern for single-parameter changes too
        let o = GarmentOpts::default();
        let d = ShirtSpec::default();
        let big = draft_shirt(&ShirtSpec { half_chest: d.half_chest + 4.0, half_hem: d.half_hem + 4.0, ..d.clone() }, &o).unwrap();
        let base = draft_shirt(&d, &o).unwrap();
        assert!(geom_info(big.piece("FRT").unwrap()).width > geom_info(base.piece("FRT").unwrap()).width + 1.5);
        let pd = PantSpec::default();
        let long = draft_pant_detailed(&PantSpec { inseam: pd.inseam + 5.0, ..pd.clone() }, &o).unwrap();
        let pb = draft_pant_detailed(&pd, &o).unwrap();
        let hgt = |p: &Pattern| geom_info(p.piece("BACK").unwrap()).height;
        assert!((hgt(&long) - hgt(&pb) - 5.0).abs() < 0.2);
    }

    #[test]
    fn drafting_is_deterministic() {
        let o = GarmentOpts::default();
        let a = draft_shirt(&ShirtSpec::default(), &o).unwrap().to_json().to_string();
        let b = draft_shirt(&ShirtSpec::default(), &o).unwrap().to_json().to_string();
        assert_eq!(a, b);
        let cols = pant_columns();
        let g1 = grade_garment("pant", &BTreeMap::new(), &cols).unwrap();
        let g2 = grade_garment("pant", &BTreeMap::new(), &cols).unwrap();
        for ((_, p1), (_, p2)) in g1.iter().zip(&g2) {
            assert_eq!(p1.to_json().to_string(), p2.to_json().to_string());
        }
        // spec given by POM code, by name, or as a struct gives the same pattern
        let by_name = PantSpec::from_pom(&cols[2].1.iter().map(|(k, v)| (PANT_POMS.iter().find(|(c, _)| c == k).unwrap().1.to_string(), *v)).collect());
        let by_pom = PantSpec::from_pom(&cols[2].1);
        assert_eq!(by_name, by_pom);
        let p1 = draft_pant_detailed(&by_name, &o).unwrap().to_json().to_string();
        let p2 = draft_pant_detailed(&by_pom, &o).unwrap().to_json().to_string();
        assert_eq!(p1, p2);
    }

    #[test]
    fn pom_mapping_with_the_chart_rows() {
        let cols = pant_columns();
        // base size S of the chart is exactly the default
        assert_eq!(PantSpec::from_pom(&cols[1].1), PantSpec::default());
        // size L column of CL1086464.xlsx
        let l = PantSpec::from_pom(&cols[3].1);
        assert_eq!(l.half_waist, 39.5);
        assert_eq!(l.half_waist_stretched, 53.5);
        assert_eq!(l.half_seat, 56.5);
        assert_eq!(l.thigh, 35.3);
        assert_eq!(l.front_rise, 32.8);
        assert_eq!(l.back_rise, 43.3);
        assert_eq!(l.knee, 31.7);
        assert_eq!(l.leg_opening, 31.7);
        assert_eq!(l.inseam, 80.0);
        assert_eq!(l.hem_height, 2.8);
        assert_eq!(l.waistband_width, 5.2);
        assert_eq!(l.pocket_opening_waist, 3.5);
        assert_eq!(l.pocket_opening_length, 16.0);
        assert_eq!(l.pocket_bag_depth, 24.0);
        assert_eq!(l.drawcord_length, 30.0);
        assert_eq!(l.hip_pos_side, 18.0);
        assert_eq!(l.hip_pos_cf, 17.0);
        // XS and XL end points of the 1/2 waist (20125) and the stretched waist (20245)
        assert_eq!(PantSpec::from_pom(&cols[0].1).half_waist, 33.0);
        assert_eq!(PantSpec::from_pom(&cols[4].1).half_waist, 42.0);
        assert_eq!(PantSpec::from_pom(&cols[0].1).half_waist_stretched, 47.0);
        // missing keys -> defaults; names and POM codes mix; unknown keys are reported
        let mut m = BTreeMap::new();
        m.insert("20865".to_string(), 36.6);
        m.insert("Front Rise".to_string(), 34.1);
        m.insert("99999".to_string(), 1.0);
        let (s, warn) = PantSpec::from_pom_checked(&m);
        assert_eq!(s.thigh, 36.6);
        assert_eq!(s.front_rise, 34.1);
        assert_eq!(s.inseam, PantSpec::default().inseam);
        assert_eq!(warn.len(), 1);
        // round trips
        assert_eq!(PantSpec::from_pom(&s.to_pom()), s);
        assert_eq!(PantSpec::from_pom(&s.to_map()), s);
        assert_eq!(PantSpec::field_names().len(), PANT_POMS.len());
        // every POM code of the chart is known
        for code in ["20125", "20245", "20305-A", "20305-B", "20305", "20865", "21505", "21545", "20905", "21125", "30210", "21885", "20265", "22145", "22165", "22565", "30845"] {
            assert!(PantSpec::default().get(code).is_some(), "{}", code);
        }
    }

    #[test]
    fn shirt_map_aliases_derivations_and_roundtrip() {
        let d = ShirtSpec::default();
        let s = ShirtSpec::from_map(&[("Chest", 63.0), ("hem sweep", 62.0), ("body-length", 76.0), ("collar_size", 51.62), ("Placket", 3.5)].iter().map(|(k, v)| (k.to_string(), *v)).collect());
        assert_eq!(s.half_chest, 63.0);
        assert_eq!(s.half_hem, 62.0);
        assert_eq!(s.body_length_hps, 76.0);
        assert!((s.back_length_cb - (d.back_length_cb + 1.93)).abs() < 1e-9, "back length follows body length");
        assert!((s.neck_size - 51.62).abs() < 1e-9);
        assert!((s.front_neck_width - (d.front_neck_width + 0.4)).abs() < 1e-9, "neck width follows neck size");
        assert_eq!(ShirtSpec::from_map(&BTreeMap::new()), d);
        assert_eq!(ShirtSpec::from_map(&s.to_map()), s);
        let (_, warn) = ShirtSpec::from_map_checked(&[("zzz".to_string(), 1.0), ("half_chest".to_string(), f64::NAN)].into_iter().collect());
        assert_eq!(warn.len(), 2);
        assert_eq!(ShirtSpec::field_names().len(), 25);
    }

    #[test]
    fn invalid_specs_and_kinds_are_rejected() {
        let o = GarmentOpts::default();
        let mut s = ShirtSpec::default();
        s.half_chest = -1.0;
        assert!(draft_shirt(&s, &o).is_err());
        s = ShirtSpec::default();
        s.bicep = f64::NAN;
        assert!(draft_shirt(&s, &o).is_err());
        s = ShirtSpec::default();
        s.yoke_depth = 60.0;
        assert!(draft_shirt(&s, &o).is_err());
        let mut p = PantSpec::default();
        p.waistband_width = 0.0;
        assert!(draft_pant_detailed(&p, &o).is_err());
        p = PantSpec::default();
        p.inseam = 400.0;
        assert!(draft_pant_detailed(&p, &o).is_err());
        assert!(grade_garment("cape", &BTreeMap::new(), &[("S".into(), BTreeMap::new())]).is_err());
        assert!(grade_garment("shirt", &BTreeMap::new(), &[]).is_err());
        let bad_o = GarmentOpts { sa: -1.0, ..o };
        assert!(draft_shirt(&ShirtSpec::default(), &bad_o).is_err());
    }

    #[test]
    fn grade_garment_uses_base_values_and_labels_sizes() {
        let mut base = BTreeMap::new();
        base.insert("sleeve_length".to_string(), 30.0);
        let sizes = vec![
            ("M".to_string(), [("half_chest".to_string(), 59.0)].into_iter().collect::<BTreeMap<_, _>>()),
            ("L".to_string(), [("half_chest".to_string(), 61.0), ("sleeve_length".to_string(), 31.0)].into_iter().collect()),
        ];
        let g = grade_garment("shirt", &base, &sizes).unwrap();
        assert_eq!(g[0].0, "M");
        assert_eq!(g[0].1.size, "M");
        let sl = |p: &Pattern| geom_info(p.piece("Sleeve").unwrap()).height;
        assert!(sl(&g[1].1) > sl(&g[0].1) + 0.9, "per-size value overrides the shared base value");
        let alias = grade_garment("trousers", &BTreeMap::new(), &[("S".into(), BTreeMap::new())]).unwrap();
        assert_eq!(alias[0].1.garment, "pant");
    }

    #[test]
    fn uniform_allowance_option_and_export_work() {
        let o = GarmentOpts { sample_sa: false, ..GarmentOpts::default() };
        let shirt = draft_shirt(&ShirtSpec::default(), &o).unwrap();
        let (sew, cut) = crate::export::cut_outline(shirt.piece("back").unwrap());
        assert!(signed_area(&cut).abs() > signed_area(&sew).abs());
        // every non-hem, non-fold allowance equals sa
        for pc in &shirt.pieces {
            for n in &pc.nodes {
                let sa = n.sa.unwrap();
                assert!(sa == 0.0 || sa == 1.0 || n.edge == "hem", "{} {} {}", pc.name, n.edge, sa);
            }
        }
        let dxf = crate::export::dxf_aama(&[("L".to_string(), &shirt)], "shirt");
        assert!(dxf.contains("Piece Name: FRT") && dxf.contains("Piece Name: back YK") && dxf.contains("Piece Name: Sleeve"));
        // quantities in the DXF equal the sample quantities (FRT 2, back YK 2, back 1)
        let q = |name: &str| -> String {
            let i = dxf.find(&format!("Piece Name: {}", name)).unwrap();
            let rest = &dxf[i..];
            let j = rest.find("Quantity: ").unwrap();
            rest[j + 10..].lines().next().unwrap().trim().to_string()
        };
        assert_eq!(q("FRT"), "2");
        assert_eq!(q("back YK"), "2");
        assert_eq!(q("back"), "1");
        assert_eq!(q("Sleeve"), "2");
        let pant = draft_pant_detailed(&PantSpec::default(), &GarmentOpts::default()).unwrap();
        let dxf = crate::export::dxf_aama(&[("S".to_string(), &pant)], "pant");
        let i = dxf.find("Piece Name: FRONT").unwrap();
        assert!(dxf[i..].contains("Quantity: 2"));
        let svg = crate::export::to_svg(&pant, true);
        assert!(svg.contains("<svg"));
        // JSON round trip keeps the structure
        let back = Pattern::from_json(&pant.to_json()).unwrap();
        assert_eq!(back.pieces.len(), 7);
        assert_eq!(back.seams.len(), pant.seams.len());
    }
}

#[cfg(test)]
mod dbg {
    use super::*;
    /// Development aid: when PF_DUMP=<dir> is set, write sew/cut outlines of the base drafts
    /// (even invalid ones) as text for plotting against the sample marker.
    #[test]
    fn dump_outlines() {
        let Ok(dir) = std::env::var("PF_DUMP") else { return };
        let o = GarmentOpts::default();
        let pats = [build_shirt(&ShirtSpec::default(), &o).unwrap(), build_pant(&PantSpec::default(), &o).unwrap()];
        for pat in pats {
            let mut txt = String::new();
            for pc in &pat.pieces {
                let (sew, cut) = crate::export::cut_outline(pc);
                txt += &format!("PIECE {}\nSEW {}\nCUT {}\n", pc.name,
                    sew.iter().map(|p| format!("{:.3},{:.3}", p.x, p.y)).collect::<Vec<_>>().join(" "),
                    cut.iter().map(|p| format!("{:.3},{:.3}", p.x, p.y)).collect::<Vec<_>>().join(" "));
                for n in &pc.notches {
                    let poly = pc.edge_polyline(n.node, 32);
                    let (pt, _) = point_at(&poly, n.t * poly_len(&poly));
                    txt += &format!("NOTCH {:.3},{:.3}\n", pt.x, pt.y);
                }
            }
            std::fs::write(format!("{}/{}.txt", dir, pat.garment), txt).unwrap();
        }
    }
}
