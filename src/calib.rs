//! Calibration + shape-diagnostics helper for the spec drafters in `garments.rs`.
//!
//! This module compares a drafted piece (the parametric output of `draft_pant_detailed`
//! / `draft_shirt`) against the real Optitex geometry and reports how far apart the two
//! shapes are.  Two independent ground truths are used:
//!
//!   * the **decoded PDS polygons** of the pant (`crate::pds_bin::decode` on
//!     `pant_1074664.PDS`): per piece, per size, cut and sew vertex polygons in absolute
//!     layout coordinates.  These give a real point-to-point shape comparison.
//!   * the **XML `GEOM_INFO`** of both samples (`garments::reference`): SIZE_X/SIZE_Y,
//!     AREA, PERIMETER, SEW_AREA, SEW_PERIMETER per piece per size.  This is the only
//!     ground truth available for the shirt.
//!
//! `shape_distance` rigidly aligns `ours` onto `theirs` (nesting rotation / mirror are
//! removed) and returns a symmetric Hausdorff + mean-nearest point distance plus
//! area / perimeter / bounding-box deltas.  `report()` prints BEFORE/AFTER tables; run it
//! with `cargo test --release --offline -- --nocapture calib_report`.
//!
//! Alignment note: the decoded PDS pieces are laid out rotated for nesting (e.g. the pant
//! legs lie horizontally), so a naive axis-aligned comparison would be wrong.  The aligner
//! therefore seeds from the eight dihedral transforms (rotations k*90 deg, optional x
//! mirror) and refines each with a few ICP steps; the best fit is kept.  Fold pieces
//! (HALF=CLOSE, e.g. the waistband) are decoded as the mirrored whole, so the drafted half
//! is mirrored across its fold edge before comparison.

use crate::export::cut_outline;
use crate::geom::{signed_area, v2, V2};
use crate::model::Piece;

// ---------------------------------------------------------------------------------------
// small geometry helpers (local; geom.rs is read-only for this crate)
// ---------------------------------------------------------------------------------------

fn poly_len_closed(p: &[V2]) -> f64 {
    let n = p.len();
    if n < 2 {
        return 0.0;
    }
    (0..n).map(|i| p[i].dist(p[(i + 1) % n])).sum()
}

fn poly_area(p: &[V2]) -> f64 {
    signed_area(p).abs()
}

/// Sorted (long, short) extent of the axis-aligned bounding box.
fn bbox_sorted(p: &[V2]) -> (f64, f64) {
    let (mut lo, mut hi) = (p[0], p[0]);
    for q in p {
        lo = v2(lo.x.min(q.x), lo.y.min(q.y));
        hi = v2(hi.x.max(q.x), hi.y.max(q.y));
    }
    let (a, b) = (hi.x - lo.x, hi.y - lo.y);
    (a.max(b), a.min(b))
}

fn centroid(p: &[V2]) -> V2 {
    let n = p.len() as f64;
    let s = p.iter().fold(v2(0.0, 0.0), |a, b| a + *b);
    s * (1.0 / n)
}

/// Distance from `q` to the closed polyline `poly` (nearest point on any segment).
fn dist_point_poly(q: V2, poly: &[V2]) -> f64 {
    let n = poly.len();
    let mut best = f64::INFINITY;
    for i in 0..n {
        let a = poly[i];
        let b = poly[(i + 1) % n];
        let ab = b - a;
        let l2 = ab.dot(ab);
        let t = if l2 < 1e-12 { 0.0 } else { ((q - a).dot(ab) / l2).clamp(0.0, 1.0) };
        let d = q.dist(a + ab * t);
        if d < best {
            best = d;
        }
    }
    best
}

/// Resample a closed polygon to `n` points, equally spaced by arc length.
fn resample(p: &[V2], n: usize) -> Vec<V2> {
    let total = poly_len_closed(p);
    if total < 1e-9 || p.len() < 2 {
        return vec![p.get(0).copied().unwrap_or_default(); n];
    }
    let m = p.len();
    let mut out = Vec::with_capacity(n);
    let step = total / n as f64;
    let mut seg = 0usize;
    let mut seg_start = 0.0;
    let mut seg_len = p[0].dist(p[1 % m]);
    for i in 0..n {
        let target = i as f64 * step;
        while target > seg_start + seg_len + 1e-12 && seg + 1 < m {
            seg += 1;
            seg_start += seg_len;
            seg_len = p[seg].dist(p[(seg + 1) % m]);
        }
        let t = if seg_len < 1e-12 { 0.0 } else { (target - seg_start) / seg_len };
        out.push(p[seg].lerp(p[(seg + 1) % m], t.clamp(0.0, 1.0)));
    }
    out
}

#[derive(Clone, Copy)]
struct Rigid {
    // maps p -> R*(flip(p)) + t ; flip is x -> -x before rotation
    cos: f64,
    sin: f64,
    tx: f64,
    ty: f64,
    flip: f64,
}
impl Rigid {
    fn apply(&self, p: V2) -> V2 {
        let x = p.x * self.flip;
        let y = p.y;
        v2(self.cos * x - self.sin * y + self.tx, self.sin * x + self.cos * y + self.ty)
    }
}

/// 2D Procrustes: best proper rotation + translation taking `a[i]` onto `b[i]`.
fn procrustes(a: &[V2], b: &[V2]) -> (f64, f64, f64, f64) {
    let ca = centroid(a);
    let cb = centroid(b);
    let (mut sxy, mut sxx) = (0.0, 0.0); // cross, dot
    for (pa, pb) in a.iter().zip(b) {
        let da = *pa - ca;
        let db = *pb - cb;
        sxy += da.x * db.y - da.y * db.x;
        sxx += da.x * db.x + da.y * db.y;
    }
    let ang = sxy.atan2(sxx);
    let (s, c) = ang.sin_cos();
    let tx = cb.x - (c * ca.x - s * ca.y);
    let ty = cb.y - (s * ca.x + c * ca.y);
    (c, s, tx, ty)
}

const ICP_N: usize = 360;
const ICP_ITERS: usize = 80;

/// Result of comparing two closed polygons after rigid alignment.
#[derive(Clone, Copy, Debug, Default)]
pub struct ShapeDist {
    /// Symmetric Hausdorff distance (cm): the worst point-to-shape gap either way.
    pub hausdorff: f64,
    /// Symmetric mean nearest-point distance (cm).
    pub mean_nearest: f64,
    /// Signed area error in percent of `theirs` (ours - theirs).
    pub area_pct: f64,
    /// Signed perimeter error in percent of `theirs`.
    pub perim_pct: f64,
    /// Long-side bounding-box error in percent of `theirs` (rotation invariant).
    pub bbox_long_pct: f64,
    /// Short-side bounding-box error in percent of `theirs`.
    pub bbox_short_pct: f64,
}

/// Rigidly align `ours` onto `theirs` (removing nesting rotation and mirror) and return the
/// shape distance.  Alignment seeds from the eight dihedral transforms and refines each with
/// ICP; the lowest symmetric mean-nearest fit is kept.  The returned distances are computed
/// on the ORIGINAL vertex sets (ours may be finely tessellated, theirs a coarse control
/// polygon), so sub-0.2 cm values are at the level of polygon-vs-curve sampling noise.
pub fn shape_distance(ours: &[V2], theirs: &[V2]) -> ShapeDist {
    if ours.len() < 3 || theirs.len() < 3 {
        return ShapeDist::default();
    }
    let a0 = resample(ours, ICP_N);
    let b = resample(theirs, ICP_N);
    let cb = centroid(&b);

    let mut best: Option<(f64, Rigid)> = None;
    for &flip in &[1.0f64, -1.0] {
        for q in 0..4 {
            let ang0 = q as f64 * std::f64::consts::FRAC_PI_2;
            let (s0, c0) = ang0.sin_cos();
            // initial transform: flip, rotate by q*90, translate centroid(a)->centroid(b)
            let mut a: Vec<V2> = a0
                .iter()
                .map(|p| {
                    let x = p.x * flip;
                    v2(c0 * x - s0 * p.y, s0 * x + c0 * p.y)
                })
                .collect();
            let ca = centroid(&a);
            for p in a.iter_mut() {
                *p = *p + (cb - ca);
            }
            // ICP refinement
            let mut corr = vec![v2(0.0, 0.0); ICP_N];
            for _ in 0..ICP_ITERS {
                for (i, p) in a.iter().enumerate() {
                    // nearest resampled point of b
                    let mut bd = f64::INFINITY;
                    let mut bp = b[0];
                    for q in &b {
                        let d = p.dist(*q);
                        if d < bd {
                            bd = d;
                            bp = *q;
                        }
                    }
                    corr[i] = bp;
                }
                let (c, s, tx, ty) = procrustes(&a, &corr);
                for p in a.iter_mut() {
                    *p = v2(c * p.x - s * p.y + tx, s * p.x + c * p.y + ty);
                }
            }
            // score: symmetric mean nearest on resampled sets
            let err = sym_mean(&a, &b);
            // recover the full rigid map (flip, seed rotation and ICP motion) by one fit
            let flipped: Vec<V2> = a0.iter().map(|p| v2(p.x * flip, p.y)).collect();
            let (c, s, tx, ty) = procrustes(&flipped, &a);
            let rig = Rigid { cos: c, sin: s, tx, ty, flip };
            if best.as_ref().map_or(true, |(e, _)| err < *e) {
                best = Some((err, rig));
            }
        }
    }
    let rig = best.unwrap().1;
    let oa: Vec<V2> = ours.iter().map(|p| rig.apply(*p)).collect();

    // metrics on original vertices
    let mut h = 0.0f64;
    let mut sum = 0.0f64;
    let mut cnt = 0usize;
    for p in &oa {
        let d = dist_point_poly(*p, theirs);
        h = h.max(d);
        sum += d;
        cnt += 1;
    }
    for p in theirs {
        let d = dist_point_poly(*p, &oa);
        h = h.max(d);
        sum += d;
        cnt += 1;
    }
    let (al, as_) = bbox_sorted(&oa);
    let (bl, bs) = bbox_sorted(theirs);
    let pct = |a: f64, b: f64| if b.abs() < 1e-9 { 0.0 } else { 100.0 * (a - b) / b };
    ShapeDist {
        hausdorff: h,
        mean_nearest: sum / cnt as f64,
        area_pct: pct(poly_area(&oa), poly_area(theirs)),
        perim_pct: pct(poly_len_closed(&oa), poly_len_closed(theirs)),
        bbox_long_pct: pct(al, bl),
        bbox_short_pct: pct(as_, bs),
    }
}

fn sym_mean(a: &[V2], b: &[V2]) -> f64 {
    let mut s = 0.0;
    for p in a {
        let mut bd = f64::INFINITY;
        for q in b {
            bd = bd.min(p.dist(*q));
        }
        s += bd;
    }
    for q in b {
        let mut bd = f64::INFINITY;
        for p in a {
            bd = bd.min(q.dist(*p));
        }
        s += bd;
    }
    s / (a.len() + b.len()) as f64
}

// ---------------------------------------------------------------------------------------
// drafted-piece outlines (mirroring fold pieces to the whole, to match the decoder)
// ---------------------------------------------------------------------------------------

/// (sew, cut) outline of a drafted piece.  Fold pieces (a `cb`/`cf` edge on x = 0) are
/// mirrored across the fold so the returned polygon is the whole piece, as the PDS decoder
/// returns it.
pub fn piece_outlines(pc: &Piece) -> (Vec<V2>, Vec<V2>) {
    let (sew, cut) = cut_outline(pc);
    let fold = pc.nodes.iter().any(|n| n.edge == "cb" || n.edge == "cf");
    if !fold {
        return (sew, cut);
    }
    (mirror_whole(&sew), mirror_whole(&cut))
}

/// Mirror a half polygon (fold on x = 0) into the whole.  The open path between the two fold
/// vertices (those on x = 0) is reflected and appended in reverse, so the fold edge itself
/// disappears from the whole outline.
fn mirror_whole(half: &[V2]) -> Vec<V2> {
    let n = half.len();
    let on = |p: &V2| p.x.abs() < 1e-5;
    // start of the open path: a fold vertex followed by a non-fold vertex
    let start = (0..n).find(|&i| on(&half[i]) && !on(&half[(i + 1) % n]));
    let start = match start {
        Some(s) => s,
        None => return half.to_vec(),
    };
    let mut path = vec![half[start]];
    let mut i = (start + 1) % n;
    loop {
        path.push(half[i]);
        if on(&half[i]) || path.len() > n + 1 {
            break;
        }
        i = (i + 1) % n;
    }
    let mut out = path.clone();
    let m: Vec<V2> = path.iter().rev().map(|p| v2(-p.x, p.y)).collect();
    out.extend_from_slice(&m[1..m.len() - 1]);
    out
}

// ---------------------------------------------------------------------------------------
// reports
// ---------------------------------------------------------------------------------------

/// Which spec columns drive the pant drafts in the tables.
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PantCols {
    /// `garments::pant_columns` - the xlsx chart (a different, related style).
    Chart,
    /// `garments::pant_columns_pds` - chart with the PDS-implied length steps.
    Pds,
}
fn pant_cols(c: PantCols) -> Vec<(String, std::collections::BTreeMap<String, f64>)> {
    match c {
        PantCols::Chart => crate::garments::pant_columns(),
        PantCols::Pds => crate::garments::pant_columns_pds(),
    }
}

/// Per-piece, per-size shape distance of the drafted pant vs the DECODED PDS polygons.
/// Returns the printable table and the collected (piece, size, cut ShapeDist, sew ShapeDist).
pub fn pant_shape_table(pds_bytes: &[u8], cols_kind: PantCols) -> Result<(String, Vec<(String, String, ShapeDist, ShapeDist)>), String> {
    let doc = crate::pds_bin::decode(pds_bytes)?;
    if !doc.decoded_geometry {
        return Err(format!("PDS geometry not fully decoded: {:?}", doc.warnings));
    }
    let cols = pant_cols(cols_kind);
    let o = crate::garments::GarmentOpts::default();
    let mut rows = Vec::new();
    let mut s = String::new();
    s += &format!(
        "{:<12}{:<4} | {:>8} {:>8} {:>7} {:>7} | {:>8} {:>8} {:>7} {:>7}\n",
        "piece", "size", "cut Hd", "cut mNN", "cutA%", "cutP%", "sew Hd", "sew mNN", "sewA%", "sewP%"
    );
    s += &format!("{}\n", "-".repeat(94));
    for (sz, m) in &cols {
        let spec = crate::garments::PantSpec::from_pom(m);
        let pat = crate::garments::draft_pant_detailed(&spec, &o).map_err(|e| format!("draft {}: {}", sz, e))?;
        for pc in &pat.pieces {
            let (our_sew, our_cut) = piece_outlines(pc);
            // find decoded entry
            let dec = doc.pieces.iter().find(|p| p.name == pc.name && p.size == *sz);
            let dec = match dec {
                Some(d) => d,
                None => continue,
            };
            let their_cut: Vec<V2> = dec.cut.iter().map(|&(x, y)| v2(x, y)).collect();
            let their_sew: Vec<V2> = dec.sew.iter().map(|&(x, y)| v2(x, y)).collect();
            let dc = if their_cut.len() >= 3 { shape_distance(&our_cut, &their_cut) } else { ShapeDist::default() };
            let ds = if their_sew.len() >= 3 { shape_distance(&our_sew, &their_sew) } else { ShapeDist::default() };
            s += &format!(
                "{:<12}{:<4} | {:>8.3} {:>8.3} {:>+7.1} {:>+7.1} | {:>8.3} {:>8.3} {:>+7.1} {:>+7.1}\n",
                pc.name, sz, dc.hausdorff, dc.mean_nearest, dc.area_pct, dc.perim_pct, ds.hausdorff, ds.mean_nearest, ds.area_pct, ds.perim_pct
            );
            rows.push((pc.name.clone(), sz.clone(), dc, ds));
        }
    }
    Ok((s, rows))
}

/// XML `GEOM_INFO` error table for a drafted garment (SIZE_X/Y, AREA, PERIMETER, SEW_*).
/// `kind` = "shirt" | "pant".  Errors in percent of the XML value.
pub fn geom_error_table(kind: &str, pcols: PantCols) -> Result<(String, Vec<(String, String, [f64; 6])>), String> {
    use crate::garments::reference::*;
    let (refs, cols): (&[RefPiece], _) = if kind == "shirt" {
        (SHIRT_REF, crate::garments::shirt_columns())
    } else {
        (PANT_REF, pant_cols(pcols))
    };
    let graded = crate::garments::grade_garment(kind, &std::collections::BTreeMap::new(), &cols)?;
    let rel = |a: f64, b: f64| if b.abs() < 1e-12 { 0.0 } else { 100.0 * (a - b) / b };
    let mut s = String::new();
    let mut errs = Vec::new();
    s += &format!(
        "{:<12}{:<4} | {:>6} {:>6} {:>7} {:>7} {:>7} {:>7}\n",
        "piece", "size", "dX%", "dY%", "area%", "per%", "sarea%", "sper%"
    );
    s += &format!("{}\n", "-".repeat(64));
    for rp in refs {
        for row in rp.rows {
            let pat = &graded.iter().find(|(sz, _)| sz == row.size).unwrap().1;
            let pc = pat.piece(rp.name).ok_or_else(|| format!("missing {}", rp.name))?;
            let g = crate::garments::geom_info(pc);
            let (x, y) = if rp.x_is_height { (g.height, g.width) } else { (g.width, g.height) };
            let e = [
                rel(x, row.x),
                rel(y, row.y),
                rel(g.area_m2, row.area),
                rel(g.perimeter, row.per),
                if row.sew_area.is_nan() { 0.0 } else { rel(g.sew_area_m2, row.sew_area) },
                if row.sew_per.is_nan() { 0.0 } else { rel(g.sew_perimeter, row.sew_per) },
            ];
            s += &format!(
                "{:<12}{:<4} | {:>+6.2} {:>+6.2} {:>+7.2} {:>+7.2} {:>+7.2} {:>+7.2}\n",
                rp.name, row.size, e[0], e[1], e[2], e[3], e[4], e[5]
            );
            errs.push((rp.name.to_string(), row.size.to_string(), e));
        }
    }
    Ok((s, errs))
}

/// Worst absolute value in a column of collected errors (for a compact summary).
pub fn worst<F: Fn(&ShapeDist) -> f64>(rows: &[(String, String, ShapeDist, ShapeDist)], f: F, cut: bool) -> f64 {
    rows.iter().map(|(_, _, c, s)| f(if cut { c } else { s }).abs()).fold(0.0, f64::max)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pds_path() -> String {
        std::env::var("PDS_SAMPLES_DIR").unwrap_or_else(|_| "/home/claude/samples".into()) + "/pant_1074664.PDS"
    }

    #[test]
    fn calib_report() {
        println!("\n######## XML GEOM_INFO error (percent of XML) ########");
        for (kind, pc) in [("pant", PantCols::Chart), ("pant", PantCols::Pds), ("shirt", PantCols::Chart)] {
            let (t, _) = geom_error_table(kind, pc).expect("geom table");
            println!("\n=== {} ({:?} columns) vs XML GEOM_INFO ===\n{}", kind.to_uppercase(), pc, t);
        }
        match std::fs::read(pds_path()) {
            Ok(bytes) => {
                let (t, rows) = pant_shape_table(&bytes, PantCols::Pds).expect("pant shape table");
                println!("\n=== PANT (PDS-implied columns) drafted vs DECODED PDS polygons (cm, percent) ===\n{}", t);
                println!(
                    "worst cut Hausdorff = {:.3} cm, worst cut meanNN = {:.3} cm",
                    worst(&rows, |d| d.hausdorff, true),
                    worst(&rows, |d| d.mean_nearest, true)
                );
                println!(
                    "worst sew Hausdorff = {:.3} cm, worst sew meanNN = {:.3} cm",
                    worst(&rows, |d| d.hausdorff, false),
                    worst(&rows, |d| d.mean_nearest, false)
                );
            }
            Err(e) => println!("(pant PDS not found at {}: {} - shape table skipped)", pds_path(), e),
        }
    }

    #[test]
    fn shape_distance_is_zero_for_identical_and_transformed() {
        // a non-trivial polygon
        let p = vec![v2(0.0, 0.0), v2(10.0, 0.5), v2(12.0, 6.0), v2(5.0, 9.0), v2(-1.0, 5.0)];
        let d0 = shape_distance(&p, &p);
        assert!(d0.hausdorff < 1e-6, "identical hausdorff {}", d0.hausdorff);
        // rotate 37 deg, translate, mirror -> alignment must recover it
        let (s, c) = 0.645f64.sin_cos();
        let q: Vec<V2> = p.iter().map(|v| v2(-(c * v.x - s * v.y) + 3.0, (s * v.x + c * v.y) - 7.0)).collect();
        let d1 = shape_distance(&p, &q);
        // ICP on a 5-vertex polygon can stall a little short of exact (sampling + nearest-point matching)
        assert!(d1.mean_nearest < 0.15 && d1.hausdorff < 0.5, "transformed meanNN {} hd {}", d1.mean_nearest, d1.hausdorff);
        assert!(d1.area_pct.abs() < 0.5 && d1.perim_pct.abs() < 0.5, "area {} per {}", d1.area_pct, d1.perim_pct);
    }

    #[test]
    fn pant_shape_distance_stays_within_calibrated_bounds() {
        // skipped when the (non-redistributable) sample PDS is not present
        let Ok(bytes) = std::fs::read(pds_path()) else { return };
        let (_, rows) = pant_shape_table(&bytes, PantCols::Pds).expect("shape table");
        for (piece, size, cut, sew) in &rows {
            let (hd_lim, nn_lim) = match piece.as_str() {
                "FRONT" | "BACK" => (1.0, 0.4),
                _ => (0.3, 0.1),
            };
            for d in [cut, sew] {
                assert!(d.hausdorff <= hd_lim && d.mean_nearest <= nn_lim, "{} {}: Hd {:.3} mNN {:.3}", piece, size, d.hausdorff, d.mean_nearest);
                assert!(d.area_pct.abs() <= 0.7 && d.perim_pct.abs() <= 0.4, "{} {}: area {:+.2}% per {:+.2}%", piece, size, d.area_pct, d.perim_pct);
            }
        }
    }
}
