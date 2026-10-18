//! Marker making (nesting): lay pattern pieces on a fabric of fixed width so as to use the least
//! fabric length (what Optitex "Marker" / "Nest" does).
//!
//! Coordinates: the marker is a strip `x` = along the fabric length (the grain direction),
//! `y` in `[0, fabric_width]` across the width, centimetres, y up. A placement transforms a
//! piece outline `p` to `R(angle) * M(flipped) * p + (x, y)` where `M` mirrors `x -> -x`.
//!
//! Algorithm (deterministic, zero dependencies, no clock, no threads, wasm32-safe):
//!  1. outlines are cleaned (NaN/duplicates removed, swallow-tail loops cut away, hull fallback);
//!  2. every allowed orientation (rotation x flip) is rasterised on a conservative occupancy grid
//!     (cells within `gap/2` of the polygon are marked) so that disjoint footprints guarantee a
//!     clearance of at least `gap`;
//!  3. pieces are placed one by one with a "minimum right edge, then lowest y" rule using a
//!     run-length sliding search (fills holes and concavities of earlier pieces);
//!  4. an improvement phase tries several sort orders and seeded random perturbations and keeps the
//!     shortest marker (work-bounded, not time-bounded, so results are reproducible);
//!  5. the winner is compacted with exact polygon geometry (slides left/down by decreasing steps),
//!     which removes the raster slack;
//!  6. `verify` re-checks everything independently with exact geometry.
use crate::export;
use crate::geom::*;
use crate::json::Json;
use crate::model::*;
use std::collections::BTreeMap;
use std::fmt::Write;

// ------------------------------------------------------------------------------------------------
// Public types
// ------------------------------------------------------------------------------------------------

/// One pattern piece to be nested.
#[derive(Clone, Debug)]
pub struct NestPiece {
    pub name: String,
    /// Closed polygon (no repeated end point), cm, the cut line incl. seam allowance.
    pub outline: Vec<V2>,
    /// Number of copies to place.
    pub qty: usize,
    /// Allowed rotations in degrees, relative to the grain-aligned orientation (0 = grain line
    /// parallel to the marker length). `[0,180]` is the usual "rotation 180" setting; `[0]` forbids
    /// turning; `[0,90,180,270]` allows cross-grain; free steps such as `[0,15,30..]` are filtered by
    /// `grain_tol_deg` (see [`allowed_rotations`]).
    pub rotations: Vec<f64>,
    /// A mirrored copy is allowed (left/right pairs).
    pub allow_flip: bool,
    /// Direction of the grain line in the piece's own coordinates (degrees, 0 = +x, 90 = +y).
    pub grain_deg: f64,
    /// Grain tolerance in degrees: a rotation is grain-legal when the piece's grain ends up within
    /// this angle of the fabric length axis (mod 180). Explicit multiples of 90 listed in
    /// `rotations` are always honoured (the piece "allows 90").
    pub grain_tol_deg: f64,
}

impl NestPiece {
    pub fn new(name: &str, outline: Vec<V2>) -> NestPiece {
        NestPiece { name: name.to_string(), outline, qty: 1, rotations: vec![0.0, 180.0], allow_flip: false, grain_deg: 0.0, grain_tol_deg: 0.0 }
    }
}

#[derive(Clone, Debug)]
pub struct NestOpts {
    /// Usable fabric width in cm (default 150).
    pub fabric_width: f64,
    /// Minimum piece-to-piece spacing in cm (default 0.5).
    pub gap: f64,
    /// Clear border kept free on all sides of the marker (cm, default 0).
    pub edge_margin: f64,
    /// Longest marker allowed in cm (default 10000). Pieces that do not fit are reported unplaced.
    pub max_length: f64,
    /// Upper bound of improvement iterations (the real number is also bounded by a work budget so
    /// big jobs stay fast). Default 200.
    pub time_budget_iters: usize,
    /// Seed of the deterministic random perturbations.
    pub seed: u64,
    /// One-way nap/pile: only rotations that keep every piece's grain pointing the same way.
    pub one_way_nap: bool,
    /// Pieces with `allow_flip` are cut in left/right pairs: odd copies are mirrored. When false a
    /// piece with `allow_flip` may be placed either way (the optimiser chooses).
    pub pair_mirroring: bool,
}

impl Default for NestOpts {
    fn default() -> Self {
        NestOpts { fabric_width: 150.0, gap: 0.5, edge_margin: 0.0, max_length: 10000.0, time_budget_iters: 200, seed: 1, one_way_nap: false, pair_mirroring: true }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Placement {
    /// Index into the `pieces` slice.
    pub piece: usize,
    /// Copy number `0..qty`.
    pub copy: usize,
    /// Translation applied after rotating: `R(angle) * M(flipped) * p + (x, y)`.
    pub x: f64,
    pub y: f64,
    /// Rotation in degrees, counter-clockwise, `[0,360)`.
    pub angle: f64,
    pub flipped: bool,
}

#[derive(Clone, Debug)]
pub struct NestResult {
    pub placements: Vec<Placement>,
    /// Marker length (cm), including `edge_margin` at the far end.
    pub length: f64,
    /// Fabric width (cm) = `opts.fabric_width`.
    pub width: f64,
    /// Placed piece area / (width * length), 0..1.
    pub efficiency: f64,
    /// `(piece, copy)` that could not be placed.
    pub unplaced: Vec<(usize, usize)>,
    pub warnings: Vec<String>,
}

// ------------------------------------------------------------------------------------------------
// Small helpers
// ------------------------------------------------------------------------------------------------

/// Tolerance (cm) used by `verify` on clearance / bounds.
const VERIFY_TOL: f64 = 1e-6;

fn norm360(a: f64) -> f64 {
    let r = a % 360.0;
    let r = if r < 0.0 { r + 360.0 } else { r };
    if r >= 360.0 { 0.0 } else { r }
}

fn circ_diff(a: f64, b: f64) -> f64 {
    let d = norm360(a - b);
    d.min(360.0 - d)
}

/// sin/cos in degrees, exact for multiples of 90 so axis-aligned pieces stay axis-aligned.
fn exact_sin_cos(deg: f64) -> (f64, f64) {
    let a = norm360(deg);
    let q = (a / 90.0).round();
    if (a - q * 90.0).abs() < 1e-9 {
        return match (q as i64) % 4 { 0 => (0.0, 1.0), 1 => (1.0, 0.0), 2 => (0.0, -1.0), _ => (-1.0, 0.0) };
    }
    a.to_radians().sin_cos()
}

/// Apply flip then rotation (no translation).
fn xform(p: V2, flipped: bool, angle_deg: f64) -> V2 {
    let q = if flipped { v2(-p.x, p.y) } else { p };
    let (s, c) = exact_sin_cos(angle_deg);
    v2(c * q.x - s * q.y, s * q.x + c * q.y)
}

fn flipped_grain(g: f64, flipped: bool) -> f64 {
    if flipped { 180.0 - g } else { g }
}

fn bbox(p: &[V2]) -> (V2, V2) {
    let mut lo = p[0];
    let mut hi = p[0];
    for q in p {
        lo = v2(lo.x.min(q.x), lo.y.min(q.y));
        hi = v2(hi.x.max(q.x), hi.y.max(q.y));
    }
    (lo, hi)
}

struct Rng(u64);
impl Rng {
    fn new(seed: u64) -> Rng { Rng(seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) ^ 0xD1B5_4A32_D192_ED03 | 1) }
    fn next(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    fn below(&mut self, n: usize) -> usize { if n == 0 { 0 } else { (self.next() % n as u64) as usize } }
    fn unit(&mut self) -> f64 { (self.next() >> 11) as f64 / (1u64 << 53) as f64 }
}

// ------------------------------------------------------------------------------------------------
// Exact polygon geometry
// ------------------------------------------------------------------------------------------------

fn pt_seg_dist(p: V2, a: V2, b: V2) -> f64 {
    let ab = b - a;
    let l2 = ab.dot(ab);
    if l2 < 1e-18 { return p.dist(a); }
    let t = ((p - a).dot(ab) / l2).clamp(0.0, 1.0);
    p.dist(a + ab * t)
}

/// Do the segments cross properly (transversally, by more than 1e-9 cm)?
fn crosses(a: V2, b: V2, c: V2, d: V2) -> bool {
    let (lab, lcd) = ((b - a).len().max(1e-300), (d - c).len().max(1e-300));
    let d1 = (b - a).cross(c - a) / lab;
    let d2 = (b - a).cross(d - a) / lab;
    let d3 = (d - c).cross(a - c) / lcd;
    let d4 = (d - c).cross(b - c) / lcd;
    const T: f64 = 1e-9;
    ((d1 > T && d2 < -T) || (d1 < -T && d2 > T)) && ((d3 > T && d4 < -T) || (d3 < -T && d4 > T))
}

/// Distance between two segments; `-1.0` when they properly cross.
fn seg_seg_dist(a: V2, b: V2, c: V2, d: V2) -> f64 {
    if crosses(a, b, c, d) { return -1.0; }
    pt_seg_dist(a, c, d).min(pt_seg_dist(b, c, d)).min(pt_seg_dist(c, a, b)).min(pt_seg_dist(d, a, b))
}

/// Strict point-in-polygon (ray casting).
fn pip(p: V2, poly: &[V2]) -> bool {
    let n = poly.len();
    let mut inside = false;
    let mut j = n - 1;
    for i in 0..n {
        let (a, b) = (poly[i], poly[j]);
        if (a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x {
            inside = !inside;
        }
        j = i;
    }
    inside
}

/// A point strictly inside a simple polygon (widest horizontal chord midpoint over several scanlines).
fn interior_point(p: &[V2]) -> V2 {
    let (lo, hi) = bbox(p);
    let n = p.len();
    let mut best = (-1.0, p[0]);
    for k in 0..9 {
        let f = 0.5 + ((k as f64) * 0.618_033_988_75).fract() * 0.6 - 0.3;
        let y = lo.y + (hi.y - lo.y) * if k == 0 { 0.5 } else { f };
        let mut xs: Vec<f64> = Vec::new();
        for i in 0..n {
            let (a, b) = (p[i], p[(i + 1) % n]);
            if (a.y <= y) != (b.y <= y) {
                xs.push(a.x + (y - a.y) / (b.y - a.y) * (b.x - a.x));
            }
        }
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        for w in xs.chunks(2) {
            if w.len() == 2 && w[1] - w[0] > best.0 {
                best = (w[1] - w[0], v2((w[0] + w[1]) * 0.5, y));
            }
        }
    }
    best.1
}

fn proper_crossing(a: V2, b: V2, c: V2, d: V2) -> Option<V2> {
    if !crosses(a, b, c, d) { return None; }
    let d3 = (d - c).cross(a - c);
    let d4 = (d - c).cross(b - c);
    let t = d3 / (d3 - d4);
    // intersection point along ab
    Some(a + (b - a) * t)
}

fn adjacent(i: usize, j: usize, n: usize) -> bool { j == i + 1 || (i == 0 && j == n - 1) }

/// First pair of crossing non-adjacent edges: (i, j, point).
fn find_crossing(p: &[V2]) -> Option<(usize, usize, V2)> {
    let n = p.len();
    for i in 0..n {
        for j in i + 2..n {
            if adjacent(i, j, n) { continue; }
            if let Some(x) = proper_crossing(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]) {
                return Some((i, j, x));
            }
        }
    }
    None
}

/// Non-adjacent edges touching without crossing (pinched polygon).
fn has_touching(p: &[V2]) -> bool {
    let n = p.len();
    for i in 0..n {
        for j in i + 2..n {
            if adjacent(i, j, n) { continue; }
            if seg_seg_dist(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]) < 1e-9 { return true; }
        }
    }
    false
}

fn convex_hull(pts: &[V2]) -> Vec<V2> {
    let mut v: Vec<V2> = pts.to_vec();
    v.sort_by(|a, b| a.x.partial_cmp(&b.x).unwrap().then(a.y.partial_cmp(&b.y).unwrap()));
    v.dedup_by(|a, b| a.dist(*b) < 1e-12);
    if v.len() < 3 { return v; }
    let mut h: Vec<V2> = Vec::new();
    for pass in 0..2 {
        let start = h.len();
        let it: Vec<V2> = if pass == 0 { v.clone() } else { v.iter().rev().cloned().collect() };
        for p in it {
            while h.len() >= start + 2 && (h[h.len() - 1] - h[h.len() - 2]).cross(p - h[h.len() - 2]) <= 0.0 { h.pop(); }
            h.push(p);
        }
        h.pop();
    }
    h
}

/// Clean an outline into a simple CCW polygon. Returns (polygon or empty, optional note).
pub fn clean_outline(o: &[V2]) -> (Vec<V2>, Option<String>) {
    let mut notes: Vec<&str> = Vec::new();
    let mut p: Vec<V2> = Vec::with_capacity(o.len());
    let mut dropped = false;
    for q in o {
        if !(q.x.is_finite() && q.y.is_finite() && q.x.abs() < 1e7 && q.y.abs() < 1e7) { dropped = true; continue; }
        if let Some(l) = p.last() { if l.dist(*q) < 1e-9 { continue; } }
        p.push(*q);
    }
    while p.len() > 1 && p[0].dist(p[p.len() - 1]) < 1e-9 { p.pop(); }
    if dropped { notes.push("non-finite points removed"); }
    if p.len() < 3 { return (vec![], Some("degenerate outline (fewer than 3 distinct points)".into())); }
    // swallow-tail repair
    let mut guard = 0;
    while let Some((i, j, x)) = find_crossing(&p) {
        guard += 1;
        if guard > 64 || p.len() < 3 { break; }
        // loop part: x, p[i+1..=j]; rest: p[0..=i], x, p[j+1..]
        let mut lp = vec![x];
        lp.extend_from_slice(&p[i + 1..=j]);
        let mut rest: Vec<V2> = p[..=i].to_vec();
        rest.push(x);
        rest.extend_from_slice(&p[j + 1..]);
        p = if signed_area(&lp).abs() > signed_area(&rest).abs() { lp } else { rest };
        p.dedup_by(|a, b| a.dist(*b) < 1e-9);
        notes.push("self-intersection repaired");
    }
    if p.len() < 3 { return (vec![], Some("degenerate outline after repair".into())); }
    if find_crossing(&p).is_some() || has_touching(&p) {
        p = convex_hull(&p);
        notes.push("self-intersecting outline replaced by its convex hull");
    }
    if p.len() < 3 || signed_area(&p).abs() < 1e-9 { return (vec![], Some("degenerate outline (zero area)".into())); }
    if signed_area(&p) < 0.0 { p.reverse(); }
    notes.dedup();
    (p, if notes.is_empty() { None } else { Some(notes.join("; ")) })
}

/// Strictly interior sample points of a simple polygon (chord quarter points over 16 scanlines).
/// Overlap without any proper edge crossing (identical or exactly aligned pieces, nesting) is
/// detected by testing these samples against the other polygon.
fn interior_samples(p: &[V2]) -> Vec<V2> {
    let (lo, hi) = bbox(p);
    let n = p.len();
    let mut out = Vec::new();
    for k in 0..16 {
        let y = lo.y + (hi.y - lo.y) * (k as f64 + 0.5) / 16.0 + 1e-7;
        let mut xs: Vec<f64> = Vec::new();
        for i in 0..n {
            let (a, b) = (p[i], p[(i + 1) % n]);
            if (a.y <= y) != (b.y <= y) { xs.push(a.x + (y - a.y) / (b.y - a.y) * (b.x - a.x)); }
        }
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        for w in xs.chunks(2) {
            if w.len() == 2 && w[1] - w[0] > 1e-6 {
                for f in [0.25, 0.5, 0.75] { out.push(v2(w[0] + (w[1] - w[0]) * f, y)); }
            }
        }
    }
    if out.is_empty() { out.push(interior_point(p)); }
    out
}

/// Placed polygon with cached bounds, for exact tests.
#[derive(Clone)]
struct Poly {
    pts: Vec<V2>,
    lo: V2,
    hi: V2,
    samples: Vec<V2>,
}

impl Poly {
    fn new(pts: Vec<V2>) -> Poly {
        let (lo, hi) = bbox(&pts);
        let samples = interior_samples(&pts);
        Poly { pts, lo, hi, samples }
    }
    fn shifted(&self, d: V2) -> Poly {
        Poly { pts: self.pts.iter().map(|p| *p + d).collect(), lo: self.lo + d, hi: self.hi + d, samples: self.samples.iter().map(|p| *p + d).collect() }
    }
    /// Some interior sample of `self` lies inside `o`.
    fn sample_in(&self, o: &Poly) -> bool { self.samples.iter().any(|s| pip(*s, &o.pts)) }
}

/// Degenerate-overlap test for polygons whose boundaries touch without crossing (aligned or
/// coincident edges, T-junctions): split each edge at the other polygon's vertices lying on it and
/// test whether a sub-segment midpoint is strictly inside the other polygon.
fn boundary_inside(edges: &[(V2, V2)], other: &[V2]) -> bool {
    let n = other.len();
    for &(p, q) in edges {
        let d = q - p;
        let l2 = d.dot(d);
        if l2 < 1e-18 { continue; }
        let mut ts = vec![0.0, 1.0];
        for r in other {
            if pt_seg_dist(*r, p, q) < 1e-7 {
                let t = (*r - p).dot(d) / l2;
                if t > 0.0 && t < 1.0 { ts.push(t); }
            }
        }
        ts.sort_by(|a, b| a.partial_cmp(b).unwrap());
        for w in ts.windows(2) {
            if w[1] - w[0] < 1e-9 { continue; }
            let m = p + d * ((w[0] + w[1]) * 0.5);
            let mut bd = f64::MAX;
            for k in 0..n { bd = bd.min(pt_seg_dist(m, other[k], other[(k + 1) % n])); }
            if bd > 1e-7 && pip(m, other) { return true; }
        }
    }
    false
}

fn edges_of(p: &Poly, bx: Option<(f64, f64, f64, f64)>) -> Vec<(V2, V2)> {
    let n = p.pts.len();
    let mut v = Vec::new();
    for i in 0..n {
        let (s, e) = (p.pts[i], p.pts[(i + 1) % n]);
        if let Some((x0, x1, y0, y1)) = bx {
            if !(s.x.max(e.x) >= x0 && s.x.min(e.x) <= x1 && s.y.max(e.y) >= y0 && s.y.min(e.y) <= y1) { continue; }
        }
        v.push((s, e));
    }
    v
}

/// True when polygons overlap or come closer than `gap - tol`. Brute force over all edge pairs
/// (after bounding-box rejection); used by `verify`.
fn violates_brute(a: &Poly, b: &Poly, gap: f64, tol: f64) -> bool {
    if a.lo.x > b.hi.x + gap || b.lo.x > a.hi.x + gap || a.lo.y > b.hi.y + gap || b.lo.y > a.hi.y + gap { return false; }
    let (ea, eb) = (edges_of(a, None), edges_of(b, None));
    let mut mind = f64::MAX;
    for (p, q) in &ea {
        for (r, s) in &eb {
            let d = seg_seg_dist(*p, *q, *r, *s);
            if d < gap - tol { return true; }
            mind = mind.min(d);
        }
    }
    (mind < 1e-7 && (boundary_inside(&ea, &b.pts) || boundary_inside(&eb, &a.pts))) || a.sample_in(b) || b.sample_in(a)
}

/// Same predicate with edge pre-filtering (fast path used during compaction).
fn violates_fast(a: &Poly, b: &Poly, gap: f64, tol: f64) -> bool {
    let m = gap + 1e-6;
    let (ox0, ox1) = (a.lo.x.max(b.lo.x) - m, a.hi.x.min(b.hi.x) + m);
    let (oy0, oy1) = (a.lo.y.max(b.lo.y) - m, a.hi.y.min(b.hi.y) + m);
    if ox0 > ox1 || oy0 > oy1 { return false; }
    let bx = Some((ox0, ox1, oy0, oy1));
    let (ea, eb) = (edges_of(a, bx), edges_of(b, bx));
    let mut mind = f64::MAX;
    for (p, q) in &ea {
        for (r, s) in &eb {
            if p.x.max(q.x) + m < r.x.min(s.x) || r.x.max(s.x) + m < p.x.min(q.x) || p.y.max(q.y) + m < r.y.min(s.y) || r.y.max(s.y) + m < p.y.min(q.y) { continue; }
            let d = seg_seg_dist(*p, *q, *r, *s);
            if d < gap - tol { return true; }
            mind = mind.min(d);
        }
    }
    (mind < 1e-7 && (boundary_inside(&ea, &b.pts) || boundary_inside(&eb, &a.pts))) || a.sample_in(b) || b.sample_in(a)
}

// ------------------------------------------------------------------------------------------------
// Orientations and rasterisation
// ------------------------------------------------------------------------------------------------

/// Rotations (relative to the grain-aligned orientation, normalised to `[0,360)`) a piece may use.
/// Honours the grain tolerance and `one_way_nap`. Never empty (falls back to `[0]`).
pub fn allowed_rotations(p: &NestPiece, opts: &NestOpts) -> Vec<f64> {
    let tol = if p.grain_tol_deg.is_finite() { p.grain_tol_deg.max(0.0) } else { 0.0 };
    let list: Vec<f64> = if p.rotations.is_empty() { vec![0.0] } else { p.rotations.clone() };
    let mut out: Vec<f64> = Vec::new();
    for r in list {
        if !r.is_finite() { continue; }
        let r = norm360(r);
        let r180 = r % 180.0;
        let d0 = r180.min(180.0 - r180);
        let mult90 = (r / 90.0 - (r / 90.0).round()).abs() * 90.0 < 1e-9;
        let grain_ok = d0 <= tol + 1e-9 || mult90;
        let nap_ok = !opts.one_way_nap || circ_diff(r, 0.0) <= tol + 1e-9;
        if grain_ok && nap_ok && !out.iter().any(|&x| circ_diff(x, r) < 1e-9) { out.push(r); }
    }
    if out.is_empty() { out.push(0.0); }
    if out.len() > 36 { out.truncate(36); }
    out
}

struct Orient {
    flipped: bool,
    angle: f64,
    /// bbox min of the transformed (unshifted) polygon
    qmin: V2,
    bw: f64,
    bh: f64,
    /// rows of occupied cell runs: (row index (may be negative), runs (inclusive))
    rows: Vec<(i32, Vec<(i32, i32)>)>,
}

fn seg_box_dist(p: V2, q: V2, x0: f64, y0: f64, x1: f64, y1: f64) -> f64 {
    let pbox = |a: V2| -> f64 {
        let dx = (x0 - a.x).max(0.0).max(a.x - x1);
        let dy = (y0 - a.y).max(0.0).max(a.y - y1);
        (dx * dx + dy * dy).sqrt()
    };
    // Liang-Barsky clip
    let (mut t0, mut t1) = (0.0f64, 1.0f64);
    let d = q - p;
    let mut hit = true;
    for (pp, qq) in [(-d.x, p.x - x0), (d.x, x1 - p.x), (-d.y, p.y - y0), (d.y, y1 - p.y)] {
        if pp.abs() < 1e-15 {
            if qq < 0.0 { hit = false; break; }
        } else {
            let r = qq / pp;
            if pp < 0.0 { if r > t1 { hit = false; break; } if r > t0 { t0 = r; } } else { if r < t0 { hit = false; break; } if r < t1 { t1 = r; } }
        }
    }
    if hit && t0 <= t1 { return 0.0; }
    let mut m = pbox(p).min(pbox(q));
    for c in [v2(x0, y0), v2(x1, y0), v2(x1, y1), v2(x0, y1)] { m = m.min(pt_seg_dist(c, p, q)); }
    m
}

/// Conservative raster of a polygon (local coords, bbox min at origin): all cells whose (slightly
/// shrunk) square is within `hg` of the polygon. Returns rows of inclusive runs.
fn rasterise(local: &[V2], bw: f64, bh: f64, c: f64, hg: f64) -> Vec<(i32, Vec<(i32, i32)>)> {
    let sh = 1e-7;
    let i0 = ((-hg - 1e-6) / c).floor() as i32;
    let i1 = ((bw + hg + 1e-6) / c).floor() as i32;
    let j0 = ((-hg - 1e-6) / c).floor() as i32;
    let j1 = ((bh + hg + 1e-6) / c).floor() as i32;
    let w = (i1 - i0 + 1) as usize;
    let h = (j1 - j0 + 1) as usize;
    let mut mask = vec![false; w * h];
    let n = local.len();
    // interior (cell centres inside)
    for j in j0..=j1 {
        let yc = (j as f64 + 0.5) * c;
        let mut xs: Vec<f64> = Vec::new();
        for k in 0..n {
            let (a, b) = (local[k], local[(k + 1) % n]);
            if (a.y <= yc) != (b.y <= yc) { xs.push(a.x + (yc - a.y) / (b.y - a.y) * (b.x - a.x)); }
        }
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        for pr in xs.chunks(2) {
            if pr.len() < 2 { break; }
            let ia = ((pr[0] / c - 0.5).ceil() as i32).max(i0);
            let ib = ((pr[1] / c - 0.5).floor() as i32).min(i1);
            for i in ia..=ib { mask[(j - j0) as usize * w + (i - i0) as usize] = true; }
        }
    }
    // boundary cells
    for k in 0..n {
        let (p, q) = (local[k], local[(k + 1) % n]);
        let ca = (((p.x.min(q.x) - hg) / c).floor() as i32).max(i0);
        let cb = (((p.x.max(q.x) + hg) / c).floor() as i32).min(i1);
        let d = q - p;
        for i in ca..=cb {
            let (xl, xr) = (i as f64 * c - hg, (i + 1) as f64 * c + hg);
            let (ylo, yhi) = if d.x.abs() < 1e-12 {
                (p.y.min(q.y), p.y.max(q.y))
            } else {
                let ta = ((xl - p.x) / d.x).clamp(0.0, 1.0);
                let tb = ((xr - p.x) / d.x).clamp(0.0, 1.0);
                let (ya, yb) = (p.y + d.y * ta, p.y + d.y * tb);
                (ya.min(yb), ya.max(yb))
            };
            let ra = (((ylo - hg) / c).floor() as i32).max(j0);
            let rb = (((yhi + hg) / c).floor() as i32).min(j1);
            for j in ra..=rb {
                let idx = (j - j0) as usize * w + (i - i0) as usize;
                if mask[idx] { continue; }
                let (x0, y0) = (i as f64 * c + sh, j as f64 * c + sh);
                if seg_box_dist(p, q, x0, y0, x0 + c - 2.0 * sh, y0 + c - 2.0 * sh) <= hg + 1e-12 { mask[idx] = true; }
            }
        }
    }
    let mut rows = Vec::new();
    for j in j0..=j1 {
        let mut runs: Vec<(i32, i32)> = Vec::new();
        let mut i = i0;
        while i <= i1 {
            if mask[(j - j0) as usize * w + (i - i0) as usize] {
                let s = i;
                while i + 1 <= i1 && mask[(j - j0) as usize * w + (i + 1 - i0) as usize] { i += 1; }
                runs.push((s, i));
            }
            i += 1;
        }
        if !runs.is_empty() { rows.push((j, runs)); }
    }
    rows
}

/// Orientation of `poly`; `None` when its bounding box exceeds `max_w` x `max_h` (not rasterised).
fn build_orient(poly: &[V2], flipped: bool, rel: f64, grain: f64, c: f64, hg: f64, max_w: f64, max_h: f64) -> Option<Orient> {
    let angle = norm360(rel - flipped_grain(grain, flipped));
    let mut q: Vec<V2> = poly.iter().map(|p| xform(*p, flipped, angle)).collect();
    if flipped { q.reverse(); }
    let (lo, hi) = bbox(&q);
    let (bw, bh) = (hi.x - lo.x, hi.y - lo.y);
    if bw > max_w || bh > max_h { return None; }
    let local: Vec<V2> = q.iter().map(|p| *p - lo).collect();
    let rows = rasterise(&local, bw, bh, c, hg);
    Some(Orient { flipped, angle, qmin: lo, bw, bh, rows })
}

// ------------------------------------------------------------------------------------------------
// Packing on the occupancy grid
// ------------------------------------------------------------------------------------------------

struct Grid {
    rows: Vec<Vec<(i32, i32)>>,
    pad: i32,
}

impl Grid {
    fn clear(&mut self) { for r in self.rows.iter_mut() { r.clear(); } }
    fn insert(&mut self, gi: usize, a: i32, b: i32) {
        let r = &mut self.rows[gi];
        // first run whose end >= a-1 (touching or overlapping)
        let k = r.partition_point(|&(_, d)| d < a - 1);
        let (mut na, mut nb) = (a, b);
        let mut e = k;
        while e < r.len() && r[e].0 <= nb + 1 {
            na = na.min(r[e].0);
            nb = nb.max(r[e].1);
            e += 1;
        }
        r.splice(k..e, std::iter::once((na, nb)));
    }
}

struct Item {
    piece: usize,
    copy: usize,
    /// candidate orientation indices (into the global orient table)
    cands: Vec<usize>,
}

struct PackOut {
    /// per item: (orient, ix, iy)
    pos: Vec<Option<(usize, i32, i32)>>,
    len: f64,
    nfail: usize,
    sum_right: f64,
}

struct Ctx<'a> {
    orients: &'a [Orient],
    cell: f64,
    avail: f64,
    max_cols: f64,
}

/// Search the position (ix, iy) minimising the right edge (strictly below `*best_key`).
fn find_pos(o: &Orient, grid: &Grid, cell: f64, avail: f64, best_key: &mut f64, work: &mut u64) -> Option<(i32, i32)> {
    let iy_max = ((avail - o.bh) / cell + 1e-9).floor() as i32;
    let bwc = o.bw / cell;
    let mut best = None;
    for iy in 0..=iy_max {
        let limit = (*best_key - bwc - 1e-9).ceil() as i64 - 1;
        if limit < 0 { break; }
        let mut ix: i64 = 0;
        let mut ok = true;
        loop {
            let mut changed = false;
            for (j, runs) in &o.rows {
                let gi = (iy + j + grid.pad) as usize;
                let gr = &grid.rows[gi];
                if gr.is_empty() { continue; }
                *work += 1;
                for &(a, b) in runs {
                    let lo = ix + a as i64;
                    let k = gr.partition_point(|&(_, d)| (d as i64) < lo);
                    if k < gr.len() && (gr[k].0 as i64) <= ix + b as i64 {
                        ix = gr[k].1 as i64 - a as i64 + 1;
                        changed = true;
                        if ix > limit { ok = false; break; }
                    }
                }
                if !ok { break; }
            }
            if !ok || !changed { break; }
        }
        if ok && ix <= limit {
            *best_key = ix as f64 + bwc;
            best = Some((ix as i32, iy));
        }
    }
    best
}

fn pack(ctx: &Ctx, items: &[Item], order: &[usize], grid: &mut Grid, work: &mut u64) -> PackOut {
    grid.clear();
    let mut pos = vec![None; items.len()];
    let mut len: f64 = 0.0;
    let mut nfail = 0;
    let mut sum_right = 0.0;
    for &it in order {
        let item = &items[it];
        let mut best_key = ctx.max_cols + 1e-9;
        let mut chosen: Option<(usize, i32, i32)> = None;
        for &oi in &item.cands {
            let o = &ctx.orients[oi];
            if let Some((ix, iy)) = find_pos(o, grid, ctx.cell, ctx.avail, &mut best_key, work) {
                chosen = Some((oi, ix, iy));
            }
        }
        match chosen {
            Some((oi, ix, iy)) => {
                let o = &ctx.orients[oi];
                for (j, runs) in &o.rows {
                    let gi = (iy + j + grid.pad) as usize;
                    for &(a, b) in runs { grid.insert(gi, ix + a, ix + b); }
                }
                len = len.max(best_key);
                sum_right += best_key;
                pos[it] = Some((oi, ix, iy));
            }
            None => nfail += 1,
        }
    }
    PackOut { pos, len, nfail, sum_right }
}

fn better(a: &PackOut, b: &PackOut) -> bool {
    if a.nfail != b.nfail { return a.nfail < b.nfail; }
    if (a.len - b.len).abs() > 1e-9 { return a.len < b.len; }
    a.sum_right < b.sum_right - 1e-9
}

// ------------------------------------------------------------------------------------------------
// Nesting driver
// ------------------------------------------------------------------------------------------------

/// Work units (grid row look-ups) allowed for the whole improvement phase. Deterministic stand-in for
/// a time budget (no clock is available on wasm32); about 1.5 s in release on a 2020 laptop.
const WORK_BUDGET: u64 = 100_000_000;

struct PlacedP {
    piece: usize,
    copy: usize,
    flipped: bool,
    angle: f64,
    t: V2,
    poly: Poly,
}

fn validate_opts(o: &NestOpts) -> Result<(), String> {
    if !(o.fabric_width.is_finite() && o.fabric_width > 0.0) { return Err("fabric_width must be a positive number".into()); }
    if !(o.gap.is_finite() && o.gap >= 0.0) { return Err("gap must be >= 0".into()); }
    if !(o.edge_margin.is_finite() && o.edge_margin >= 0.0) { return Err("edge_margin must be >= 0".into()); }
    if !(o.max_length.is_finite() && o.max_length > 0.0) { return Err("max_length must be a positive number".into()); }
    if o.fabric_width - 2.0 * o.edge_margin <= 0.0 { return Err("edge_margin leaves no usable fabric width".into()); }
    if o.fabric_width > 10_000.0 { return Err("fabric_width above 10000 cm is not supported".into()); }
    if o.max_length > 1_000_000.0 { return Err("max_length above 1000000 cm is not supported".into()); }
    if o.gap > o.fabric_width { return Err("gap larger than the fabric width".into()); }
    Ok(())
}

/// Nest the pieces. Never panics on bad geometry: unusable or oversize pieces are reported in
/// `unplaced` and `warnings`. Errors only for invalid options or absurd quantities.
pub fn nest(pieces: &[NestPiece], opts: &NestOpts) -> Result<NestResult, String> {
    validate_opts(opts)?;
    let total: usize = pieces.iter().map(|p| p.qty).fold(0usize, |a, b| a.saturating_add(b));
    if total > 20_000 { return Err(format!("too many piece copies ({}); the limit is 20000", total)); }
    let m = opts.edge_margin;
    let avail = opts.fabric_width - 2.0 * m;
    let mut warnings: Vec<String> = Vec::new();
    let mut unplaced: Vec<(usize, usize)> = Vec::new();
    let cell = if total > 400 { 1.0 } else { 0.5 };
    let hg = opts.gap * 0.5;
    let pad = (hg / cell).ceil() as i32 + 2;
    let max_cols = (opts.max_length - 2.0 * m) / cell;

    let mut orients: Vec<Orient> = Vec::new();
    let mut polys: Vec<Vec<V2>> = Vec::with_capacity(pieces.len());
    let mut cands: Vec<[Vec<usize>; 2]> = Vec::with_capacity(pieces.len());
    let mut areas: Vec<f64> = Vec::new();
    for (pi, pc) in pieces.iter().enumerate() {
        let (poly, note) = clean_outline(&pc.outline);
        if let Some(n) = note { warnings.push(format!("piece '{}': {}", pc.name, n)); }
        let mut cs: [Vec<usize>; 2] = [vec![], vec![]];
        if poly.is_empty() {
            for c in 0..pc.qty { unplaced.push((pi, c)); }
            polys.push(poly);
            cands.push(cs);
            areas.push(0.0);
            continue;
        }
        let rots = allowed_rotations(pc, opts);
        let grain = if pc.grain_deg.is_finite() { pc.grain_deg } else { 0.0 };
        let flips: &[bool] = if pc.allow_flip { &[false, true] } else { &[false] };
        for &fl in flips {
            for &r in &rots {
                let o = match build_orient(&poly, fl, r, grain, cell, hg, (opts.max_length - 2.0 * m + 1e-9).min(100_000.0), avail + 1e-9) { Some(o) => o, None => continue };
                let dup = cs[fl as usize].iter().any(|&k| {
                    let q: &Orient = &orients[k];
                    (q.bw - o.bw).abs() < 1e-9 && (q.bh - o.bh).abs() < 1e-9 && q.rows == o.rows
                });
                if dup { continue; }
                cs[fl as usize].push(orients.len());
                orients.push(o);
            }
        }
        if cs[0].is_empty() && cs[1].is_empty() {
            warnings.push(format!("piece '{}' does not fit the fabric (width {:.1} cm usable, {:.1} cm needed at best)", pc.name, avail, {
                let mut best = f64::MAX;
                for &r in &rots {
                    let (lo, hi) = bbox(&transform_poly(&poly, false, norm360(r - grain), v2(0.0, 0.0)));
                    let _ = lo;
                    best = best.min(hi.y - lo.y);
                }
                best
            }));
            for c in 0..pc.qty { unplaced.push((pi, c)); }
        }
        areas.push(signed_area(&poly).abs());
        polys.push(poly);
        cands.push(cs);
    }

    let mut items: Vec<Item> = Vec::new();
    for (pi, pc) in pieces.iter().enumerate() {
        if cands[pi][0].is_empty() && cands[pi][1].is_empty() { continue; }
        for c in 0..pc.qty {
            let cs: Vec<usize> = if pc.allow_flip {
                if opts.pair_mirroring {
                    cands[pi][(c % 2) as usize].clone()
                } else {
                    let mut v = cands[pi][0].clone();
                    v.extend_from_slice(&cands[pi][1]);
                    v
                }
            } else {
                cands[pi][0].clone()
            };
            if cs.is_empty() { unplaced.push((pi, c)); continue; }
            items.push(Item { piece: pi, copy: c, cands: cs });
        }
    }

    let mut placed: Vec<PlacedP> = Vec::new();
    if !items.is_empty() {
        let nrows = (avail / cell).ceil() as usize + 2 * pad as usize + 6;
        let mut grid = Grid { rows: vec![Vec::new(); nrows], pad };
        let ctx = Ctx { orients: &orients, cell, avail, max_cols };
        let n = items.len();
        let extent = |i: usize| -> f64 { let o = &orients[items[i].cands[0]]; o.bw.max(o.bh) };
        let area = |i: usize| -> f64 { areas[items[i].piece] };
        let sorted_by = |key: &dyn Fn(usize) -> f64| -> Vec<usize> {
            let mut v: Vec<usize> = (0..n).collect();
            v.sort_by(|&a, &b| key(b).partial_cmp(&key(a)).unwrap_or(std::cmp::Ordering::Equal).then(a.cmp(&b)));
            v
        };
        let mut work: u64 = 0;
        let base: Vec<Vec<usize>> = vec![
            sorted_by(&|i| area(i)),
            sorted_by(&|i| extent(i)),
            sorted_by(&|i| orients[items[i].cands[0]].bw),
            sorted_by(&|i| area(i) / (1.0 + 0.002 * extent(i))),
        ];
        let w0 = work;
        let mut best_order = base[0].clone();
        let mut best = pack(&ctx, &items, &best_order, &mut grid, &mut work);
        let per_pack = (work - w0).max(1);
        let allowed = ((WORK_BUDGET / per_pack) as usize).clamp(1, 4 + opts.time_budget_iters);
        let mut done = 1usize;
        for o in base.iter().skip(1) {
            if done >= allowed { break; }
            let r = pack(&ctx, &items, o, &mut grid, &mut work);
            done += 1;
            if better(&r, &best) { best = r; best_order = o.clone(); }
        }
        let mut rng = Rng::new(opts.seed);
        while done < allowed {
            let k = done;
            let order: Vec<usize> = if k % 5 == 4 {
                let noise: Vec<f64> = (0..n).map(|_| 0.6 + 0.8 * rng.unit()).collect();
                sorted_by(&|i| area(i) * noise[i])
            } else {
                let mut o = best_order.clone();
                for _ in 0..1 + rng.below(3) {
                    let i = rng.below(n);
                    let span = 1 + n.min(12);
                    let j = (i + rng.below(span * 2 + 1)).saturating_sub(span).min(n - 1);
                    if rng.below(2) == 0 { o.swap(i, j); } else { let x = o.remove(i); o.insert(j, x); }
                }
                o
            };
            let r = pack(&ctx, &items, &order, &mut grid, &mut work);
            done += 1;
            if !better(&best, &r) { best = r; best_order = order; }
        }
        for (it, p) in best.pos.iter().enumerate() {
            let item = &items[it];
            match p {
                None => unplaced.push((item.piece, item.copy)),
                Some((oi, ix, iy)) => {
                    let o = &orients[*oi];
                    let pos = v2(m + *ix as f64 * cell, m + *iy as f64 * cell);
                    let t = pos - o.qmin;
                    let pts = transform_poly(&polys[item.piece], o.flipped, o.angle, t);
                    placed.push(PlacedP { piece: item.piece, copy: item.copy, flipped: o.flipped, angle: o.angle, t, poly: Poly::new(pts) });
                }
            }
        }
        if placed.len() <= 800 {
            compact(&mut placed, opts);
        } else {
            warnings.push("exact compaction skipped (more than 800 placed copies)".into());
        }
    }

    placed.sort_by(|a, b| (a.piece, a.copy).cmp(&(b.piece, b.copy)));
    unplaced.sort();
    unplaced.dedup();
    let mut length: f64 = 0.0;
    let mut area_sum = 0.0;
    for p in &placed {
        length = length.max(p.poly.hi.x + m);
        area_sum += signed_area(&p.poly.pts).abs();
    }
    for &(pi, c) in &unplaced {
        warnings.push(format!("unplaced: piece '{}' copy {}", pieces[pi].name, c));
    }
    let efficiency = if length > 0.0 { (area_sum / (opts.fabric_width * length)).min(1.0) } else { 0.0 };
    let placements = placed.iter().map(|p| Placement { piece: p.piece, copy: p.copy, x: p.t.x, y: p.t.y, angle: p.angle, flipped: p.flipped }).collect();
    Ok(NestResult { placements, length, width: opts.fabric_width, efficiency, unplaced, warnings })
}

fn transform_poly(poly: &[V2], flipped: bool, angle: f64, t: V2) -> Vec<V2> {
    let mut q: Vec<V2> = poly.iter().map(|p| xform(*p, flipped, angle) + t).collect();
    if flipped { q.reverse(); }
    q
}

/// Exact-geometry compaction: slide pieces left and down by decreasing steps while no overlap and
/// clearance >= gap is kept.
fn compact(placed: &mut Vec<PlacedP>, opts: &NestOpts) {
    let n = placed.len();
    if n == 0 { return; }
    let (m, w, gap) = (opts.edge_margin, opts.fabric_width, opts.gap);
    let steps = [4.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05, 0.02];
    let valid = |placed: &Vec<PlacedP>, i: usize, d: V2| -> bool {
        let p = &placed[i].poly;
        if p.lo.x + d.x < m - 1e-12 || p.lo.y + d.y < m - 1e-12 || p.hi.y + d.y > w - m + 1e-12 || p.hi.x + d.x > opts.max_length - m + 1e-9 { return false; }
        let cand = p.shifted(d);
        for j in 0..placed.len() {
            if j != i && violates_fast(&cand, &placed[j].poly, gap, 1e-9) { return false; }
        }
        true
    };
    let apply = |placed: &mut Vec<PlacedP>, i: usize, d: V2| {
        let np = placed[i].poly.shifted(d);
        placed[i].poly = np;
        placed[i].t = placed[i].t + d;
    };
    let slide = |placed: &mut Vec<PlacedP>, i: usize, dir: V2| {
        // snap to the boundary first when it is free
        let snap = if dir.x < 0.0 { placed[i].poly.lo.x - m } else { placed[i].poly.lo.y - m };
        if snap > 1e-12 {
            let d = dir * snap;
            if valid(placed, i, d) { apply(placed, i, d); return; }
        }
        for &s in &steps {
            let mut cnt = 0;
            while cnt < 600 && valid(placed, i, dir * s) {
                apply(placed, i, dir * s);
                cnt += 1;
            }
        }
    };
    for _round in 0..2 {
        let mut order: Vec<usize> = (0..n).collect();
        order.sort_by(|&a, &b| placed[a].poly.lo.x.partial_cmp(&placed[b].poly.lo.x).unwrap().then(a.cmp(&b)));
        for &i in &order {
            slide(placed, i, v2(-1.0, 0.0));
            slide(placed, i, v2(0.0, -1.0));
            slide(placed, i, v2(-1.0, 0.0));
        }
    }
}

// ------------------------------------------------------------------------------------------------
// Public helpers: polygons, verification
// ------------------------------------------------------------------------------------------------

/// Placed outlines in marker coordinates (cleaned, CCW) as `(piece index, polygon)`, in the order of
/// `res.placements`.
pub fn placed_polygons(pieces: &[NestPiece], res: &NestResult) -> Vec<(usize, Vec<V2>)> {
    res.placements.iter().filter_map(|pl| {
        let pc = pieces.get(pl.piece)?;
        let (poly, _) = clean_outline(&pc.outline);
        if poly.is_empty() { return None; }
        Some((pl.piece, transform_poly(&poly, pl.flipped, pl.angle, v2(pl.x, pl.y))))
    }).collect()
}

/// Independent exact check of a nesting result: every copy accounted for exactly once, rotation /
/// flip / grain rules, fabric bounds, no overlap and clearance >= gap (1e-6 cm tolerance),
/// length and efficiency consistent.
pub fn verify(pieces: &[NestPiece], res: &NestResult, opts: &NestOpts) -> Result<(), String> {
    validate_opts(opts)?;
    let m = opts.edge_margin;
    let tol = VERIFY_TOL;
    if (res.width - opts.fabric_width).abs() > tol { return Err(format!("result width {} != fabric width {}", res.width, opts.fabric_width)); }
    let mut seen: BTreeMap<(usize, usize), bool> = BTreeMap::new();
    for pl in &res.placements {
        let pc = pieces.get(pl.piece).ok_or_else(|| format!("placement refers to missing piece {}", pl.piece))?;
        if pl.copy >= pc.qty { return Err(format!("piece '{}' copy {} >= qty {}", pc.name, pl.copy, pc.qty)); }
        if seen.insert((pl.piece, pl.copy), true).is_some() { return Err(format!("piece '{}' copy {} placed twice", pc.name, pl.copy)); }
        if !(pl.x.is_finite() && pl.y.is_finite() && pl.angle.is_finite()) { return Err(format!("non-finite placement for '{}'", pc.name)); }
        if pl.flipped && !pc.allow_flip { return Err(format!("piece '{}' copy {} is mirrored but flipping is not allowed", pc.name, pl.copy)); }
        if pc.allow_flip && opts.pair_mirroring && pl.flipped != (pl.copy % 2 == 1) {
            return Err(format!("piece '{}' copy {}: pair mirroring requires flipped = {}", pc.name, pl.copy, pl.copy % 2 == 1));
        }
        let grain = if pc.grain_deg.is_finite() { pc.grain_deg } else { 0.0 };
        let rel = norm360(pl.angle + flipped_grain(grain, pl.flipped));
        if !allowed_rotations(pc, opts).iter().any(|&r| circ_diff(r, rel) < 1e-6) {
            return Err(format!("piece '{}' copy {}: rotation {:.3} deg (grain-relative {:.3}) violates the grain / rotation rules", pc.name, pl.copy, pl.angle, rel));
        }
    }
    for &(pi, c) in &res.unplaced {
        let pc = pieces.get(pi).ok_or_else(|| format!("unplaced refers to missing piece {}", pi))?;
        if c >= pc.qty { return Err(format!("unplaced copy {} >= qty of '{}'", c, pc.name)); }
        if seen.insert((pi, c), false).is_some() { return Err(format!("piece '{}' copy {} both placed and unplaced", pc.name, c)); }
    }
    for (pi, pc) in pieces.iter().enumerate() {
        for c in 0..pc.qty {
            if !seen.contains_key(&(pi, c)) { return Err(format!("piece '{}' copy {} is neither placed nor reported unplaced", pc.name, c)); }
        }
    }
    let mut ps: Vec<(usize, Poly)> = Vec::new();
    let mut area = 0.0;
    let mut maxx: f64 = 0.0;
    for (pi, pts) in placed_polygons(pieces, res) {
        let poly = Poly::new(pts);
        if poly.lo.x < m - tol { return Err(format!("piece '{}' starts at x={:.4} before the margin", pieces[pi].name, poly.lo.x)); }
        if poly.lo.y < m - tol { return Err(format!("piece '{}' leaves the fabric at y={:.4} (< {})", pieces[pi].name, poly.lo.y, m)); }
        if poly.hi.y > opts.fabric_width - m + tol { return Err(format!("piece '{}' exceeds the fabric width: y={:.4} > {}", pieces[pi].name, poly.hi.y, opts.fabric_width - m)); }
        area += signed_area(&poly.pts).abs();
        maxx = maxx.max(poly.hi.x);
        ps.push((pi, poly));
    }
    if ps.len() != res.placements.len() { return Err("a placed piece has a degenerate outline".into()); }
    for i in 0..ps.len() {
        for j in i + 1..ps.len() {
            if violates_brute(&ps[i].1, &ps[j].1, opts.gap, tol) {
                return Err(format!("'{}' (copy {}) and '{}' (copy {}) overlap or are closer than the gap {}",
                    pieces[ps[i].0].name, res.placements[i].copy, pieces[ps[j].0].name, res.placements[j].copy, opts.gap));
            }
        }
    }
    if !res.placements.is_empty() {
        if res.length + tol < maxx + m { return Err(format!("reported length {:.4} shorter than the layout {:.4}", res.length, maxx + m)); }
        if res.length > opts.max_length + tol { return Err(format!("length {:.2} exceeds max_length {:.2}", res.length, opts.max_length)); }
        let eff = area / (res.width * res.length);
        if (eff - res.efficiency).abs() > 1e-6 { return Err(format!("reported efficiency {:.6} != recomputed {:.6}", res.efficiency, eff)); }
    }
    Ok(())
}

// ------------------------------------------------------------------------------------------------
// From a Pattern
// ------------------------------------------------------------------------------------------------

fn fold_edge(p: &Piece) -> Option<usize> {
    p.nodes.iter().position(|n| n.edge == "cf" || n.edge == "cb" || n.edge == "crotch_fold")
}

/// Cut outline of a piece; pieces drafted as a half on a fold are unfolded into the full piece.
/// Returns (outline, unfolded?).
fn full_cut_outline(p: &Piece) -> (Vec<V2>, bool) {
    let (_, cut) = export::cut_outline(p);
    let n = p.nodes.len();
    if let Some(fi) = fold_edge(p) {
        let (a, b) = (p.nodes[fi].p, p.nodes[(fi + 1) % n].p);
        let dir = (b - a).norm();
        if dir.len() > 0.5 && cut.len() >= 4 {
            let dist = |q: V2| (q - a).cross(dir).abs();
            let on: Vec<bool> = cut.iter().map(|q| dist(*q) < 1e-6).collect();
            let k = cut.len();
            let cnt = on.iter().filter(|&&x| x).count();
            // exactly one contiguous run of on-line points
            let starts: Vec<usize> = (0..k).filter(|&i| on[i] && !on[(i + k - 1) % k]).collect();
            if cnt >= 2 && cnt < k && starts.len() == 1 {
                let s = starts[0];
                let mut e = s;
                while on[(e + 1) % k] { e = (e + 1) % k; }
                let refl = |q: V2| -> V2 {
                    let rel = q - a;
                    let along = dir * rel.dot(dir);
                    a + along * 2.0 - rel
                };
                let mut chain: Vec<V2> = Vec::new();
                let mut i = (e + 1) % k;
                while i != s {
                    chain.push(cut[i]);
                    i = (i + 1) % k;
                }
                let mut full = chain.clone();
                full.push(cut[s]);
                for q in chain.iter().rev() { full.push(refl(*q)); }
                if cut[e].dist(cut[s]) > 1e-9 { full.push(cut[e]); }
                return (full, true);
            }
        }
    }
    (cut, false)
}

/// Build nesting pieces from a pattern. `qty` maps piece names to the number of copies in the
/// marker (pieces absent from the map use their pattern quantity: fold pieces are unfolded and cut
/// `qty` times; `mirror` pieces without a fold are cut `2*qty` times as left/right pairs; a map
/// value of 0 leaves the piece out). Rotations default to `[0,180]` (Optitex "rotation 180").
pub fn pieces_from_pattern(p: &Pattern, qty: &BTreeMap<String, usize>) -> Vec<NestPiece> {
    let mut out = Vec::new();
    for pc in &p.pieces {
        let (outline, unfolded) = full_cut_outline(pc);
        let default_q = if unfolded { pc.qty as usize } else { pc.qty as usize * if pc.mirror { 2 } else { 1 } };
        let q = qty.get(&pc.name).copied().unwrap_or(default_q);
        if q == 0 { continue; }
        let g = pc.grain.1 - pc.grain.0;
        let grain_deg = if g.len() < 1e-9 { 90.0 } else { g.y.atan2(g.x).to_degrees() };
        out.push(NestPiece {
            name: pc.name.clone(),
            outline,
            qty: q,
            rotations: vec![0.0, 180.0],
            allow_flip: pc.mirror && !unfolded,
            grain_deg,
            grain_tol_deg: 0.0,
        });
    }
    out
}

/// Nest all pieces of a pattern (see [`pieces_from_pattern`]).
pub fn nest_pattern(p: &Pattern, qty: &BTreeMap<String, usize>, opts: &NestOpts) -> Result<(Vec<NestPiece>, NestResult), String> {
    let pieces = pieces_from_pattern(p, qty);
    let res = nest(&pieces, opts)?;
    Ok((pieces, res))
}

// ------------------------------------------------------------------------------------------------
// Output: SVG, DXF, JSON
// ------------------------------------------------------------------------------------------------

fn esc(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

fn centroid_inside(p: &[V2]) -> V2 {
    let (lo, hi) = bbox(p);
    let c = v2((lo.x + hi.x) * 0.5, (lo.y + hi.y) * 0.5);
    if pip(c, p) { c } else { interior_point(p) }
}

/// SVG of the marker: fabric rectangle (cm), coloured pieces, names, grain arrows and a caption.
/// y is flipped so the picture matches the maths orientation (y up).
pub fn marker_svg(pieces: &[NestPiece], res: &NestResult, opts: &NestOpts) -> String {
    let len = res.length.max(1.0);
    let w = res.width.max(1.0);
    let pad = 2.0;
    let cap = (w * 0.07).max(5.0);
    let fs = (w * 0.03).max(2.0);
    let mut s = String::new();
    let _ = write!(s, "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"{:.2} {:.2} {:.2} {:.2}\" width=\"{:.0}mm\" height=\"{:.0}mm\" font-family=\"sans-serif\">",
        -pad, -pad, len + 2.0 * pad, w + cap + 2.0 * pad, (len + 2.0 * pad) * 10.0, (w + cap + 2.0 * pad) * 10.0);
    let _ = write!(s, "<rect x=\"0\" y=\"0\" width=\"{:.2}\" height=\"{:.2}\" fill=\"#fbfaf6\" stroke=\"#666\" stroke-width=\"0.3\"/>", len, w);
    if opts.edge_margin > 0.0 {
        let m = opts.edge_margin;
        let _ = write!(s, "<rect x=\"{:.2}\" y=\"{:.2}\" width=\"{:.2}\" height=\"{:.2}\" fill=\"none\" stroke=\"#bbb\" stroke-width=\"0.15\" stroke-dasharray=\"1,1\"/>", m, m, (len - 2.0 * m).max(0.0), (w - 2.0 * m).max(0.0));
    }
    let polys = placed_polygons(pieces, res);
    for (k, (pi, pts)) in polys.iter().enumerate() {
        let pl = &res.placements[k];
        let pc = &pieces[*pi];
        let hue = (*pi * 47) % 360;
        let _ = write!(s, "<g data-piece=\"{}\" data-copy=\"{}\"><path d=\"M", esc(&pc.name), pl.copy);
        for (i, q) in pts.iter().enumerate() {
            let _ = write!(s, "{}{:.2},{:.2}", if i == 0 { "" } else { " L" }, q.x, w - q.y);
        }
        let _ = write!(s, "Z\" fill=\"hsl({},55%,76%)\" stroke=\"#333\" stroke-width=\"0.25\"/>", hue);
        let c = centroid_inside(pts);
        let (lo, hi) = bbox(pts);
        // grain arrow along the placed grain direction
        let g = xform(v2(pc.grain_deg.to_radians().cos(), pc.grain_deg.to_radians().sin()), pl.flipped, pl.angle);
        let half = ((hi.x - lo.x).min(hi.y - lo.y).max(2.0) * 0.3).min(((hi.x - lo.x).max(hi.y - lo.y)) * 0.3);
        let (a, b) = (c - g * half, c + g * half);
        let perp = g.perp();
        let head = (half * 0.25).clamp(0.6, 2.0);
        let (h1, h2) = (b - g * head + perp * (head * 0.45), b - g * head - perp * (head * 0.45));
        let _ = write!(s, "<path d=\"M{:.2},{:.2} L{:.2},{:.2} M{:.2},{:.2} L{:.2},{:.2} L{:.2},{:.2}\" fill=\"none\" stroke=\"#444\" stroke-width=\"0.2\"/>",
            a.x, w - a.y, b.x, w - b.y, h1.x, w - h1.y, b.x, w - b.y, h2.x, w - h2.y);
        let size = fs.min((hi.x - lo.x) / (pc.name.chars().count().max(1) as f64 * 0.62)).max(0.8);
        let _ = write!(s, "<text x=\"{:.2}\" y=\"{:.2}\" font-size=\"{:.2}\" text-anchor=\"middle\" fill=\"#222\">{}{}</text></g>",
            c.x, w - c.y - fs * 0.3, size, esc(&pc.name), if pl.flipped { " (R)" } else { "" });
    }
    let _ = write!(s, "<text x=\"0\" y=\"{:.2}\" font-size=\"{:.2}\" fill=\"#222\">Length {:.1} cm   Width {:.1} cm   Efficiency {:.1}%   Pieces {}{}</text>",
        w + cap * 0.7, cap * 0.55, res.length, res.width, res.efficiency * 100.0, res.placements.len(),
        if res.unplaced.is_empty() { String::new() } else { format!("   UNPLACED {}", res.unplaced.len()) });
    s.push_str("</svg>");
    s
}

/// AAMA-style marker DXF (metric, mm): one closed POLYLINE per placed piece on layer 1, a TEXT with
/// piece name / copy, the grain LINE on layer 7 and the fabric boundary on layer 0.
pub fn marker_dxf(pieces: &[NestPiece], res: &NestResult, style: &str) -> String {
    let mm = 10.0;
    let mut s = String::new();
    let mut g = |code: i32, v: &dyn std::fmt::Display| { let _ = write!(s, "{:>3}\r\n{}\r\n", code, v); };
    g(999, &"PatternForge marker DXF (metric, mm). One closed polyline per placed piece on layer 1.");
    g(999, &format!("Style: {}  Length {:.2} cm  Width {:.2} cm  Efficiency {:.2}%", style, res.length, res.width, res.efficiency * 100.0));
    g(0, &"SECTION");
    g(2, &"HEADER");
    g(0, &"ENDSEC");
    g(0, &"SECTION");
    g(2, &"ENTITIES");
    let poly = |g: &mut dyn FnMut(i32, &dyn std::fmt::Display), layer: &str, pts: &[V2]| {
        g(0, &"POLYLINE");
        g(8, &layer);
        g(66, &1);
        g(70, &1);
        for q in pts.iter().chain(std::iter::once(&pts[0])) {
            g(0, &"VERTEX");
            g(8, &layer);
            g(10, &format!("{:.3}", q.x * mm));
            g(20, &format!("{:.3}", q.y * mm));
            g(30, &"0.000");
        }
        g(0, &"SEQEND");
        g(8, &layer);
    };
    let fab = [v2(0.0, 0.0), v2(res.length, 0.0), v2(res.length, res.width), v2(0.0, res.width)];
    poly(&mut g, "0", &fab);
    let polys = placed_polygons(pieces, res);
    for (k, (pi, pts)) in polys.iter().enumerate() {
        let pl = &res.placements[k];
        let pc = &pieces[*pi];
        poly(&mut g, "1", pts);
        let c = centroid_inside(pts);
        g(0, &"TEXT");
        g(8, &"1");
        g(10, &format!("{:.3}", c.x * mm));
        g(20, &format!("{:.3}", c.y * mm));
        g(30, &"0.000");
        g(40, &"6.000");
        g(1, &format!("{} #{}{}", pc.name, pl.copy + 1, if pl.flipped { " (mirrored)" } else { "" }));
        let d = xform(v2(pc.grain_deg.to_radians().cos(), pc.grain_deg.to_radians().sin()), pl.flipped, pl.angle);
        let (lo, hi) = bbox(pts);
        let half = ((hi.x - lo.x).max(hi.y - lo.y)) * 0.25;
        let (a, b) = (c - d * half, c + d * half);
        g(0, &"LINE");
        g(8, &"7");
        g(10, &format!("{:.3}", a.x * mm));
        g(20, &format!("{:.3}", a.y * mm));
        g(30, &"0.000");
        g(11, &format!("{:.3}", b.x * mm));
        g(21, &format!("{:.3}", b.y * mm));
        g(31, &"0.000");
    }
    g(0, &"ENDSEC");
    g(0, &"EOF");
    s
}

fn pt_json(p: V2) -> Json { Json::nums(&[p.x, p.y]) }

/// JSON description of a result for the API.
pub fn nest_json(pieces: &[NestPiece], res: &NestResult, opts: &NestOpts) -> Json {
    let polys = placed_polygons(pieces, res);
    let placements: Vec<Json> = res.placements.iter().enumerate().map(|(k, pl)| {
        let name = pieces.get(pl.piece).map(|p| p.name.as_str()).unwrap_or("");
        let mut o = Json::obj()
            .set("piece", Json::num(pl.piece as f64))
            .set("name", Json::str(name))
            .set("copy", Json::num(pl.copy as f64))
            .set("x", Json::num(pl.x))
            .set("y", Json::num(pl.y))
            .set("angle", Json::num(pl.angle))
            .set("flipped", Json::Bool(pl.flipped));
        if let Some((_, pts)) = polys.get(k) { o = o.set("polygon", Json::Arr(pts.iter().map(|q| pt_json(*q)).collect())); }
        o
    }).collect();
    let unplaced: Vec<Json> = res.unplaced.iter().map(|&(pi, c)| {
        Json::obj().set("piece", Json::num(pi as f64)).set("name", Json::str(pieces.get(pi).map(|p| p.name.as_str()).unwrap_or(""))).set("copy", Json::num(c as f64))
    }).collect();
    Json::obj()
        .set("length", Json::num(res.length))
        .set("width", Json::num(res.width))
        .set("efficiency", Json::num(res.efficiency))
        .set("fabric_area", Json::num(res.length * res.width))
        .set("placed", Json::num(res.placements.len() as f64))
        .set("placements", Json::Arr(placements))
        .set("unplaced", Json::Arr(unplaced))
        .set("warnings", Json::Arr(res.warnings.iter().map(|w| Json::str(w)).collect()))
        .set("verified", Json::Bool(verify(pieces, res, opts).is_ok()))
        .set("svg", Json::Str(marker_svg(pieces, res, opts)))
}

fn jnum(j: &Json, k: &str, d: f64) -> f64 { j.get(k).and_then(|v| v.as_f64()).filter(|v| v.is_finite()).unwrap_or(d) }

/// Parse `{"opts": {...}}` (fields of [`NestOpts`], plus `iters` as alias of `time_budget_iters`).
pub fn opts_from_json(j: &Json) -> NestOpts {
    let mut o = NestOpts::default();
    if let Some(x) = j.get("opts") {
        o.fabric_width = jnum(x, "fabric_width", o.fabric_width);
        o.gap = jnum(x, "gap", o.gap);
        o.edge_margin = jnum(x, "edge_margin", o.edge_margin);
        o.max_length = jnum(x, "max_length", o.max_length);
        o.time_budget_iters = jnum(x, "time_budget_iters", jnum(x, "iters", o.time_budget_iters as f64)).clamp(0.0, 1000.0) as usize;
        o.seed = jnum(x, "seed", o.seed as f64).max(0.0) as u64;
        o.one_way_nap = x.get("one_way_nap").and_then(|v| v.as_bool()).unwrap_or(o.one_way_nap);
        o.pair_mirroring = x.get("pair_mirroring").and_then(|v| v.as_bool()).unwrap_or(o.pair_mirroring);
    }
    o
}

fn piece_from_json(j: &Json) -> Result<NestPiece, String> {
    let name = j.get("name").and_then(|v| v.as_str()).unwrap_or("piece");
    let pts = j.get("outline").and_then(|v| v.as_arr()).ok_or("piece missing outline")?;
    let mut outline = Vec::new();
    for p in pts {
        let a = p.as_arr().filter(|a| a.len() == 2).ok_or("outline point must be [x,y]")?;
        outline.push(v2(a[0].as_f64().ok_or("bad x")?, a[1].as_f64().ok_or("bad y")?));
    }
    let mut np = NestPiece::new(name, outline);
    np.qty = jnum(j, "qty", 1.0).clamp(0.0, 1000.0) as usize;
    if let Some(r) = j.get("rotations").and_then(|v| v.as_arr()) { np.rotations = r.iter().filter_map(|x| x.as_f64()).collect(); }
    np.allow_flip = j.get("allow_flip").and_then(|v| v.as_bool()).unwrap_or(false);
    np.grain_deg = jnum(j, "grain_deg", 0.0);
    np.grain_tol_deg = jnum(j, "grain_tol_deg", 0.0);
    Ok(np)
}

/// API entry: request is `{"pattern": {...}, "qty": {"name": n}, "opts": {...}}` or
/// `{"pieces": [{name, outline, qty, rotations, allow_flip, grain_deg, grain_tol_deg}], "opts": {...}}`.
/// Response is [`nest_json`] plus `"dxf"` (marker DXF).
pub fn nest_request(j: &Json) -> Result<Json, String> {
    let opts = opts_from_json(j);
    let (pieces, res) = if let Some(pj) = j.get("pattern") {
        let pat = Pattern::from_json(pj)?;
        let mut qty = BTreeMap::new();
        if let Some(Json::Obj(o)) = j.get("qty") {
            for (k, v) in o { if let Some(n) = v.as_f64() { qty.insert(k.clone(), n.clamp(0.0, 1000.0) as usize); } }
        }
        nest_pattern(&pat, &qty, &opts)?
    } else {
        let arr = j.get("pieces").and_then(|v| v.as_arr()).ok_or("request needs 'pattern' or 'pieces'")?;
        let pieces: Result<Vec<NestPiece>, String> = arr.iter().map(piece_from_json).collect();
        let pieces = pieces?;
        let res = nest(&pieces, &opts)?;
        (pieces, res)
    };
    let style = j.get("style").and_then(|v| v.as_str()).unwrap_or("MARKER");
    Ok(nest_json(&pieces, &res, &opts).set("dxf", Json::Str(marker_dxf(&pieces, &res, style))))
}

// ------------------------------------------------------------------------------------------------
// Tests
// ------------------------------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Instant;

    // Cut-line polygons (0.01 cm units) of the <MARKER> svgs in samples/52abc29d.xml (shirt) and
    // samples/61dcbea7.xml (pant), as laid out by Optitex.
    pub const SHIRT_VIEW: (f64, f64) = (15404.0, 11314.0);
    pub const SHIRT_POLYS: &[&str] = &[
        "140 3808 133 3322 132 2672 144 2072 171 1473 218 774 266 161 2816 142 4416 121 5359 101 5381 250 5417 395 5456 487 5511 571 5580 644 5661 703 5795 770 5939 813 6087 839 6287 852 6537 849 6786 828 7082 783 7322 738 8020 2515 7831 2580 7693 2639 7562 2714 7485 2777 7421 2854 7376 2943 7348 3039 7333 3163 7333 3319 7454 3319 7554 3319 7554 3809",
        "102 8066 104 7466 117 6916 145 6317 196 5569 243 4978 2793 4960 4393 4938 5291 4919 5331 5064 5384 5204 5435 5291 5501 5366 5580 5427 5668 5474 5810 5523 5957 5552 6156 5572 6506 5581 6789 5581 6849 6429 6881 7028 6897 7578 6901 8066",
        "102 8066 104 8666 117 9216 145 9815 196 10564 243 11154 2793 11172 4393 11194 5291 11213 5331 11068 5384 10928 5435 10841 5501 10766 5580 10705 5668 10658 5810 10609 5957 10580 6156 10560 6506 10552 6789 10551 6849 9703 6881 9104 6897 8554 6901 8066",
        "7204 8066 7203 5594 7602 5562 7949 5520 8153 5490 8635 5368 9152 7208 9009 7256 8871 7314 8783 7362 8709 7429 8660 7516 8634 7612 8614 7862 8608 8066",
        "7204 8066 7203 10538 7602 10570 7949 10612 8153 10642 8635 10764 9152 8924 9009 8876 8871 8819 8783 8770 8709 8703 8660 8617 8634 8520 8614 8271 8608 8066",
        "12620 6690 13170 6694 13670 6710 14169 6740 14767 6792 15050 6821 14857 7675 14367 7576 14022 7517 13724 7478 13425 7451 13026 7434 12955 7432 12620 7429",
        "12620 6690 12070 6694 11571 6710 11072 6740 10474 6792 10191 6821 10384 7675 10874 7576 11219 7517 11517 7478 11815 7451 12215 7434 12286 7432 12620 7429",
        "12711 9210 13261 9216 13660 9232 13959 9256 14207 9288 14453 9334 14696 9395 14934 9470 15303 9607 15271 9754 15240 9849 15192 9937 15120 10008 15029 10046 14928 10045 14821 10025 14479 9951 14134 9891 13787 9846 13438 9817 13089 9803 12711 9801",
        "12711 9210 12161 9216 11761 9232 11462 9256 11214 9288 10968 9334 10726 9395 10487 9470 10118 9607 10150 9754 10181 9849 10229 9937 10301 10008 10392 10046 10493 10045 10600 10025 10942 9951 11287 9891 11634 9846 11983 9817 12332 9803 12711 9801",
        "12680 8019 13230 8025 13630 8041 13929 8065 14177 8097 14423 8143 14665 8204 14904 8279 15273 8416 15241 8563 15209 8657 15161 8745 15090 8817 14999 8855 14897 8854 14791 8834 14449 8759 14104 8700 13757 8655 13408 8626 13058 8612 12680 8610",
        "12680 8019 12130 8025 11731 8041 11432 8065 11184 8097 10938 8143 10695 8204 10457 8279 10087 8416 10120 8563 10151 8657 10199 8745 10270 8817 10362 8855 10463 8854 10570 8834 10912 8759 11256 8700 11604 8655 11952 8626 12302 8612 12680 8610",
        "11520 4615 11370 4565 11370 418 11520 369 11720 435 12103 319 12386 220 12670 104 12729 243 12797 376 12882 500 12985 610 13139 737 13387 906 13637 1072 13797 1191 13947 1324 14049 1435 14137 1556 14211 1686 14271 1824 14316 1967 14348 2114 14369 2313 14366 2513 14340 2711 14305 2857 14256 2999 14195 3136 14120 3266 14032 3388 13896 3535 13747 3668 13548 3819 13222 4052 13067 4178 12959 4283 12865 4400 12786 4527 12698 4706 12630 4865 12352 4752 12068 4653 11721 4548",
    ];
    pub const PANT_VIEW: (f64, f64) = (19009.0, 11837.0);
    pub const PANT_POLYS: &[&str] = &[
        "6310 9394 11590 9394 11590 10044 11590 10694 6310 10694",
        "6310 9394 1030 9394 1030 10044 1030 10694 6310 10694",
        "601 5153 1036 5156 3086 5167 4436 5164 5586 5149 6985 5116 8918 5058 8931 5107 8967 5200 9034 5274 9120 5324 9216 5352 9465 5380 9829 5407 11418 5499 11434 6449 11458 7149 11483 7703 9846 8246 6447 8177 5097 8159 3647 8154 1097 8156 603 8154 602 6655",
        "596 502 1033 518 4992 494 5542 488 5942 473 6391 442 6939 390 7435 329 7880 261 8571 147 8892 101 8927 349 8968 545 9015 687 9082 821 9139 904 9206 978 9283 1042 9413 1117 9552 1172 9745 1225 9934 1267 10106 1292 11889 1518 11490 4201 8893 4094 7843 4062 6643 4038 5193 4025 2793 4020 595 4016",
        "15469 5753 15400 6198 15364 6496 15347 6745 15347 6995 15392 7994 15425 8489 14726 8518 14226 8527 13576 8521 13037 8510 13023 8409 13001 8312 12965 8220 12831 8007 12763 7874 12729 7780 12700 7633 12686 7433 12680 6983 12688 6683 12716 6284 12739 6035 12764 5887 12808 5744 12877 5610 13052 5366 13098 5278 13140 5134 13153 5064 13869 5101",
        "16273 6907 18845 6353 18879 7002 18909 7452 18209 7479 17709 7488 17059 7484 16520 7473 16507 7372 16485 7275 16449 7182 16273 6907",
        "101 11737 101 11337 16601 11337 16601 11737",
        "15966 3009 15993 3527 14356 4071 13634 4057 13595 3796",
    ];

    fn rect(w: f64, h: f64) -> Vec<V2> { vec![v2(0., 0.), v2(w, 0.), v2(w, h), v2(0., h)] }

    fn piece(name: &str, o: Vec<V2>, qty: usize) -> NestPiece {
        let mut p = NestPiece::new(name, o);
        p.qty = qty;
        p
    }

    fn parse_polys(src: &[&str], scale: f64) -> Vec<Vec<V2>> {
        src.iter().map(|s| {
            let n: Vec<f64> = s.split_whitespace().map(|t| t.parse().unwrap()).collect();
            n.chunks(2).map(|c| v2(c[0] * scale, c[1] * scale)).collect()
        }).collect()
    }

    /// Scale derived from the sample XML (GEOM_INFO perimeter of FRT size L = 223.5822 cm versus the
    /// marker polygon with the longest perimeter) when the file is around; 0.01 cm/unit otherwise.
    fn sample_scale() -> f64 {
        let s = 0.01;
        if let Ok(x) = std::fs::read_to_string("/home/claude/samples/52abc29d.xml") {
            let polys = parse_polys(SHIRT_POLYS, 1.0);
            let per = |p: &Vec<V2>| -> f64 { (0..p.len()).map(|i| p[i].dist(p[(i + 1) % p.len()])).sum() };
            // the FRT polygon is the one with the largest area (AREA 0.2588 sq.m for size L)
            let big = polys.iter().max_by(|a, b| signed_area(a).abs().partial_cmp(&signed_area(b).abs()).unwrap()).unwrap();
            let big = per(big);
            // first PERIMETER of the size named L in the FRT piece
            let i = x.find("<PIECE>").unwrap() + x[x.find("<PIECE>").unwrap()..].find("<NAME>L</NAME>").unwrap();
            let j = x[i..].find("PERIMETER=\"").unwrap() + i + 11;
            let v: f64 = x[j..].split('"').next().unwrap().parse().unwrap();
            let d = v / big;
            assert!((d - s).abs() / s < 0.02, "derived scale {} not near 0.01", d);
            return d;
        }
        s
    }

    fn sample_pieces(src: &[&str], scale: f64, sets: usize) -> Vec<NestPiece> {
        parse_polys(src, scale).into_iter().enumerate().map(|(i, p)| piece(&format!("P{}", i), p, sets)).collect()
    }

    #[test]
    fn four_rectangles_known_length() {
        let pcs = vec![piece("R", rect(50., 30.), 4)];
        let mut o = NestOpts::default();
        o.fabric_width = 60.0;
        o.gap = 0.0;
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        assert!(r.unplaced.is_empty());
        assert!((r.length - 100.0).abs() < 0.01, "length {}", r.length);
        assert!((r.efficiency - 1.0).abs() < 1e-6);
        // with a gap the optimum is 51 + 50
        o.fabric_width = 61.0;
        o.gap = 1.0;
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        assert!((r.length - 101.0).abs() < 0.01, "length {}", r.length);
        // 3 across at 150 wide
        let pcs = vec![piece("R", rect(40., 50.), 6)];
        o.fabric_width = 150.0;
        o.gap = 0.0;
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        assert!((r.length - 80.0).abs() < 0.01, "length {}", r.length);
    }

    #[test]
    fn rotation_helps_when_allowed() {
        let mut p = piece("R", rect(100., 20.), 3);
        p.rotations = vec![0.0, 90.0];
        let mut o = NestOpts::default();
        o.fabric_width = 100.0;
        o.gap = 0.0;
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p.clone()], &r, &o).unwrap();
        assert!((r.length - 60.0).abs() < 0.01 || r.length <= 60.01, "length {}", r.length);
        p.rotations = vec![0.0, 180.0];
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p], &r, &o).unwrap();
        assert!((r.length - 100.0).abs() < 1e-6 || r.length > 99.9, "length {}", r.length); // 3 x 20 stacked across 100 wide -> but needs 100 length
    }

    #[test]
    fn grain_is_honoured_and_pieces_are_rotated_to_it() {
        // tall piece with the grain drawn vertically: must be laid down so it runs along x
        let mut p = piece("tall", rect(10., 80.), 2);
        p.grain_deg = 90.0;
        let o = NestOpts { fabric_width: 100.0, ..Default::default() };
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p.clone()], &r, &o).unwrap();
        for (_, poly) in placed_polygons(&[p.clone()], &r) {
            let (lo, hi) = bbox(&poly);
            assert!((hi.x - lo.x - 80.0).abs() < 1e-6 && (hi.y - lo.y - 10.0).abs() < 1e-6);
        }
        // cross-grain explicitly forbidden: a piece wider than the fabric on the grain stays unplaced
        let mut q = piece("wide", rect(10., 80.), 1);
        q.grain_deg = 0.0; // grain along its width 10: rotating 90 is not allowed -> 80 tall > 60 wide
        q.rotations = vec![0.0, 180.0, 45.0, 90.0 + 1e-3];
        let o2 = NestOpts { fabric_width: 60.0, ..Default::default() };
        let r = nest(&[q.clone()], &o2).unwrap();
        assert_eq!(r.unplaced.len(), 1);
        verify(&[q], &r, &o2).unwrap();
    }

    #[test]
    fn free_rotation_respects_grain_tolerance() {
        let mut p = piece("tri", vec![v2(0., 0.), v2(40., 0.), v2(10., 25.)], 5);
        p.rotations = (0..24).map(|i| i as f64 * 15.0).collect();
        p.grain_tol_deg = 16.0;
        let o = NestOpts { fabric_width: 60.0, ..Default::default() };
        let allowed = allowed_rotations(&p, &o);
        assert!(allowed.iter().all(|&r| { let d = r % 180.0; d.min(180.0 - d) <= 16.0 + 1e-9 || (r % 90.0).abs() < 1e-9 }));
        assert!(allowed.contains(&15.0) && allowed.contains(&165.0) && allowed.contains(&90.0));
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p], &r, &o).unwrap();
    }

    #[test]
    fn one_way_nap_never_turns_pieces() {
        let p = piece("R", vec![v2(0., 0.), v2(30., 0.), v2(30., 10.), v2(10., 25.), v2(0., 25.)], 6);
        let o = NestOpts { fabric_width: 80.0, one_way_nap: true, ..Default::default() };
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p.clone()], &r, &o).unwrap();
        assert!(r.placements.iter().all(|pl| pl.angle.abs() < 1e-9));
        let o2 = NestOpts { one_way_nap: false, ..o.clone() };
        let r2 = nest(&[p.clone()], &o2).unwrap();
        verify(&[p.clone()], &r2, &o2).unwrap();
        assert!(r2.length <= r.length + 1e-6, "turning allowed must not be worse: {} vs {}", r2.length, r.length);
        // verify enforces nap: rotate one placement by 180 in a nap marker
        let mut bad = r.clone();
        bad.placements[0].angle = 180.0;
        assert!(verify(&[p], &bad, &o).is_err());
    }

    #[test]
    fn pair_mirroring_flips_odd_copies() {
        let mut p = piece("sleeve", vec![v2(0., 0.), v2(40., 0.), v2(30., 20.), v2(0., 25.)], 4);
        p.allow_flip = true;
        let o = NestOpts { fabric_width: 70.0, ..Default::default() };
        let r = nest(&[p.clone()], &o).unwrap();
        verify(&[p.clone()], &r, &o).unwrap();
        for pl in &r.placements { assert_eq!(pl.flipped, pl.copy % 2 == 1); }
        // free flipping may only be better or equal
        let o2 = NestOpts { pair_mirroring: false, ..o.clone() };
        let r2 = nest(&[p.clone()], &o2).unwrap();
        verify(&[p], &r2, &o2).unwrap();
        assert!(r2.length <= r.length + 0.6);
    }

    #[test]
    fn too_wide_pieces_are_reported_not_panicking() {
        let pcs = vec![piece("huge", rect(300., 200.), 2), piece("ok", rect(20., 20.), 3)];
        let o = NestOpts::default();
        let r = nest(&pcs, &o).unwrap();
        assert_eq!(r.unplaced, vec![(0, 0), (0, 1)]);
        assert_eq!(r.placements.len(), 3);
        assert!(r.warnings.iter().any(|w| w.contains("huge")));
        verify(&pcs, &r, &o).unwrap();
        // max_length
        let o2 = NestOpts { max_length: 30.0, fabric_width: 25.0, ..Default::default() };
        let pcs2 = vec![piece("a", rect(20., 20.), 4)];
        let r = nest(&pcs2, &o2).unwrap();
        verify(&pcs2, &r, &o2).unwrap();
        assert!(r.length <= 30.0 + 1e-9 && !r.unplaced.is_empty());
    }

    #[test]
    fn degenerate_outlines_are_robust() {
        let nan = f64::NAN;
        let bow = vec![v2(0., 0.), v2(20., 20.), v2(20., 0.), v2(0., 20.)]; // bow-tie
        let swallow = vec![v2(0., 0.), v2(30., 0.), v2(30., 20.), v2(20., 20.), v2(25., 10.), v2(15., 25.), v2(10., 20.), v2(0., 20.)];
        let pcs = vec![
            piece("empty", vec![], 2),
            piece("one", vec![v2(1., 1.)], 1),
            piece("line", vec![v2(0., 0.), v2(10., 0.), v2(20., 0.)], 1),
            piece("nan", vec![v2(0., 0.), v2(nan, 3.), v2(10., 0.), v2(10., 10.), v2(0., 10.)], 1),
            piece("inf", vec![v2(f64::INFINITY, 0.), v2(1., 1.), v2(5., 1.)], 1),
            piece("bow", bow, 2),
            piece("swallow", swallow, 2),
            piece("dups", vec![v2(0., 0.), v2(0., 0.), v2(10., 0.), v2(10., 10.), v2(10., 10.), v2(0., 10.), v2(0., 0.)], 2),
            piece("zero qty", rect(5., 5.), 0),
            piece("cw", vec![v2(0., 0.), v2(0., 10.), v2(10., 10.), v2(10., 0.)], 1),
        ];
        let o = NestOpts::default();
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        assert!(r.efficiency.is_finite() && r.length.is_finite());
        assert!(r.unplaced.iter().any(|&(p, _)| p == 0));
        let svg = marker_svg(&pcs, &r, &o);
        assert!(svg.contains("</svg>") && !svg.contains("NaN"));
        assert!(!marker_dxf(&pcs, &r, "x").contains("NaN"));
        // nothing at all
        let r = nest(&[], &o).unwrap();
        assert_eq!(r.length, 0.0);
        verify(&[], &r, &o).unwrap();
        // invalid options
        assert!(nest(&pcs, &NestOpts { fabric_width: 0.0, ..Default::default() }).is_err());
        assert!(nest(&pcs, &NestOpts { gap: -1.0, ..Default::default() }).is_err());
        assert!(nest(&pcs, &NestOpts { fabric_width: f64::NAN, ..Default::default() }).is_err());
        assert!(nest(&pcs, &NestOpts { edge_margin: 80.0, ..Default::default() }).is_err());
    }

    #[test]
    fn determinism_with_equal_seed() {
        let pcs = garment(2);
        let o = NestOpts { seed: 7, time_budget_iters: 12, ..Default::default() };
        let a = nest(&pcs, &o).unwrap();
        let b = nest(&pcs, &o).unwrap();
        assert_eq!(a.placements, b.placements);
        assert_eq!(a.length.to_bits(), b.length.to_bits());
        let c = nest(&pcs, &NestOpts { seed: 8, ..o.clone() }).unwrap();
        verify(&pcs, &c, &o).unwrap();
    }

    #[test]
    fn verify_catches_violations() {
        let pcs = vec![piece("A", rect(30., 30.), 2), piece("B", rect(20., 40.), 1)];
        let o = NestOpts { fabric_width: 80.0, ..Default::default() };
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        // deliberate overlap
        let mut bad = r.clone();
        bad.placements[1].x = bad.placements[0].x + 5.0;
        bad.placements[1].y = bad.placements[0].y + 5.0;
        let e = verify(&pcs, &bad, &o).unwrap_err();
        assert!(e.contains("overlap"), "{}", e);
        // gap violation (0.2 cm apart)
        let mut bad = r.clone();
        let polys = placed_polygons(&pcs, &r);
        let (lo0, hi0) = bbox(&polys[0].1);
        let (lo1, _) = bbox(&polys[1].1);
        bad.placements[1].x += hi0.x + 0.2 - lo1.x;
        bad.placements[1].y += lo0.y - lo1.y;
        assert!(verify(&pcs, &bad, &o).is_err());
        // outside the fabric
        let mut bad = r.clone();
        bad.placements[2].y += 100.0;
        assert!(verify(&pcs, &bad, &o).unwrap_err().contains("width"));
        // rotation not allowed
        let mut bad = r.clone();
        bad.placements[0].angle = 90.0;
        assert!(verify(&pcs, &bad, &o).is_err());
        // missing copy
        let mut bad = r.clone();
        bad.placements.pop();
        assert!(verify(&pcs, &bad, &o).is_err());
        // duplicated copy
        let mut bad = r.clone();
        let dup = bad.placements[0].clone();
        bad.placements.push(dup);
        assert!(verify(&pcs, &bad, &o).is_err());
        // identical polygons exactly on top of each other with zero gap
        let o0 = NestOpts { gap: 0.0, ..o.clone() };
        let mut bad = nest(&pcs, &o0).unwrap();
        bad.placements[1].x = bad.placements[0].x;
        bad.placements[1].y = bad.placements[0].y;
        assert!(verify(&pcs, &bad, &o0).is_err());
        // one inside another
        let nested = vec![piece("big", rect(60., 60.), 1), piece("small", rect(10., 10.), 1)];
        let on = NestOpts { fabric_width: 100.0, gap: 0.0, ..Default::default() };
        let mut r = nest(&nested, &on).unwrap();
        verify(&nested, &r, &on).unwrap();
        let big = r.placements[0].clone();
        r.placements[1].x = big.x + 20.0;
        r.placements[1].y = big.y + 20.0;
        assert!(verify(&nested, &r, &on).is_err());
    }

    #[test]
    fn concave_pieces_nest_into_each_other() {
        // two L shapes interlock (rotated 180) into a rectangle
        let l = vec![v2(0., 0.), v2(60., 0.), v2(60., 20.), v2(20., 20.), v2(20., 40.), v2(0., 40.)];
        let pcs = vec![piece("L", l, 2)];
        let o = NestOpts { fabric_width: 40.0, gap: 0.0, ..Default::default() };
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        assert!(r.length < 90.0, "interlocked length {}", r.length); // side by side would be 120
    }

    #[test]
    fn edge_margin_is_kept() {
        let pcs = vec![piece("R", rect(30., 20.), 5)];
        let o = NestOpts { fabric_width: 100.0, edge_margin: 2.0, gap: 1.0, ..Default::default() };
        let r = nest(&pcs, &o).unwrap();
        verify(&pcs, &r, &o).unwrap();
        for (_, p) in placed_polygons(&pcs, &r) {
            let (lo, hi) = bbox(&p);
            assert!(lo.x >= 2.0 - 1e-6 && lo.y >= 2.0 - 1e-6 && hi.y <= 98.0 + 1e-6 && hi.x <= r.length - 2.0 + 1e-6);
        }
    }

    /// Synthetic garment: ~7 curved pieces x sizes.
    fn blob(rx: f64, ry: f64, n: usize, k: f64) -> Vec<V2> {
        (0..n).map(|i| {
            let a = i as f64 / n as f64 * std::f64::consts::TAU;
            let r = 1.0 + 0.12 * (3.0 * a + k).sin() + 0.06 * (5.0 * a).cos();
            v2(rx * r * a.cos(), ry * r * a.sin())
        }).collect()
    }

    fn garment(sizes: usize) -> Vec<NestPiece> {
        let mut v = Vec::new();
        for s in 0..sizes {
            let g = 1.0 + 0.04 * s as f64;
            let defs: [(&str, f64, f64, usize, bool); 7] = [
                ("front", 38.0, 36.0, 2, true), ("back", 40.0, 36.0, 1, false), ("sleeve", 30.0, 22.0, 2, true),
                ("collar", 22.0, 6.0, 2, false), ("cuff", 14.0, 6.0, 4, false), ("pocket", 9.0, 8.0, 2, false), ("yoke", 36.0, 8.0, 1, false)];
            for (i, (n, rx, ry, q, fl)) in defs.iter().enumerate() {
                let mut p = piece(&format!("{}_{}", n, s), blob(rx * g, ry * g, 60, i as f64), *q);
                p.allow_flip = *fl;
                v.push(p);
            }
        }
        v
    }

    #[test]
    fn typical_garment_is_fast_and_valid() {
        let pcs = garment(6);
        let copies: usize = pcs.iter().map(|p| p.qty).sum();
        assert!(copies >= 80);
        let o = NestOpts::default();
        let t = Instant::now();
        let r = nest(&pcs, &o).unwrap();
        let dt = t.elapsed().as_secs_f64();
        verify(&pcs, &r, &o).unwrap();
        eprintln!("synthetic garment: {} copies, length {:.1} cm, efficiency {:.3}, {:.2}s", copies, r.length, r.efficiency, dt);
        assert!(r.unplaced.is_empty());
        assert!(dt < 3.0, "took {:.2}s", dt);
        assert!(r.efficiency > 0.65);
    }

    fn run_sample(name: &str, src: &[&str], view: (f64, f64), sets: usize, width: Option<f64>, gap: f64) -> f64 {
        let sc = sample_scale();
        let pcs = sample_pieces(src, sc, sets);
        let (a, b) = (view.0 * sc, view.1 * sc);
        let fw = width.unwrap_or(a.min(b));
        let o = NestOpts { fabric_width: fw, gap, ..Default::default() };
        let t = Instant::now();
        let r = nest(&pcs, &o).unwrap();
        let dt = t.elapsed().as_secs_f64();
        verify(&pcs, &r, &o).unwrap();
        assert!(r.unplaced.is_empty(), "{:?}", r.warnings);
        eprintln!("{} x{} width {:.2} gap {}: length {:.1} cm, efficiency {:.3} ({:.2}s)", name, sets, fw, gap, r.length, r.efficiency, dt);
        r.efficiency
    }

    #[test]
    fn real_sample_markers_beat_70_percent() {
        let sc = sample_scale();
        // Optitex' own layouts for reference: area of the polygons / marker rectangle
        for (name, src, view) in [("shirt", SHIRT_POLYS, SHIRT_VIEW), ("pant", PANT_POLYS, PANT_VIEW)] {
            let area: f64 = parse_polys(src, sc).iter().map(|p| signed_area(p).abs()).sum();
            eprintln!("{} Optitex sample marker: utilisation {:.3}", name, area / (view.0 * sc * view.1 * sc));
        }
        // same pieces, same fabric width as the sample's marker
        let e1 = run_sample("shirt", SHIRT_POLYS, SHIRT_VIEW, 1, None, 0.5);
        let e2 = run_sample("pant", PANT_POLYS, PANT_VIEW, 1, None, 0.5);
        assert!(e1 >= 0.70, "shirt {}", e1);
        // the pant marker holds a 165 cm long strip that can only lie along the grain, so one set on
        // 118 cm fabric cannot exceed 0.52 whatever the algorithm; Optitex' own layout reaches 0.45
        assert!(e2 >= 0.50, "pant {}", e2);
        // production-like: three garments, 150 cm fabric
        let e3 = run_sample("shirt", SHIRT_POLYS, SHIRT_VIEW, 3, Some(150.0), 0.5);
        let e4 = run_sample("pant", PANT_POLYS, PANT_VIEW, 3, Some(150.0), 0.5);
        assert!(e3 >= 0.70, "shirt x3 {}", e3);
        assert!(e4 >= 0.70, "pant x3 {}", e4);
        run_sample("shirt", SHIRT_POLYS, SHIRT_VIEW, 1, None, 0.0);
        run_sample("pant", PANT_POLYS, PANT_VIEW, 1, None, 0.0);
    }

    #[test]
    fn outputs_are_well_formed() {
        let sc = 0.01;
        let pcs = sample_pieces(SHIRT_POLYS, sc, 1);
        let o = NestOpts { fabric_width: 113.14, ..Default::default() };
        let r = nest(&pcs, &o).unwrap();
        let svg = marker_svg(&pcs, &r, &o);
        assert!(svg.starts_with("<svg") && svg.ends_with("</svg>"));
        assert_eq!(svg.matches("<g data-piece").count(), r.placements.len());
        assert!(svg.contains("Efficiency") && svg.contains("Length"));
        let dxf = marker_dxf(&pcs, &r, "T");
        assert_eq!(dxf.matches("POLYLINE").count() - dxf.matches("SEQEND").count(), 0);
        assert_eq!(dxf.matches("\r\n  0\r\nPOLYLINE").count(), r.placements.len() + 1);
        assert!(dxf.trim_end().ends_with("EOF"));
        let j = nest_json(&pcs, &r, &o);
        assert_eq!(j.get("verified").and_then(|v| v.as_bool()), Some(true));
        assert_eq!(j.get("placements").and_then(|v| v.as_arr()).unwrap().len(), r.placements.len());
        Json::parse(&j.to_string()).unwrap();
    }

    #[test]
    fn nest_pattern_from_drafts_and_api_request() {
        use crate::draft::{draft, DraftOpts};
        use crate::model::Measurements;
        for g in ["bodice", "skirt", "trousers"] {
            let pat = draft(g, &Measurements::default(), &DraftOpts::default()).unwrap();
            let o = NestOpts::default();
            let t = Instant::now();
            let (pcs, r) = nest_pattern(&pat, &BTreeMap::new(), &o).unwrap();
            verify(&pcs, &r, &o).unwrap();
            assert!(r.unplaced.is_empty(), "{} {:?}", g, r.warnings);
            eprintln!("{}: {} pieces, length {:.1} cm, efficiency {:.3} ({:.2}s)", g, r.placements.len(), r.length, r.efficiency, t.elapsed().as_secs_f64());
            assert!(r.efficiency > 0.4);
            // quantity override
            let mut q = BTreeMap::new();
            q.insert(pat.pieces[0].name.clone(), 3usize);
            let (pcs2, r2) = nest_pattern(&pat, &q, &o).unwrap();
            verify(&pcs2, &r2, &o).unwrap();
            assert_eq!(pcs2[0].qty, 3);
            // request round trip
            let req = Json::obj().set("pattern", pat.to_json()).set("opts", Json::obj().set("fabric_width", Json::num(140.0)).set("iters", Json::num(5.0)));
            let resp = nest_request(&req).unwrap();
            assert_eq!(resp.get("verified").and_then(|v| v.as_bool()), Some(true));
            assert!(resp.get("dxf").is_some() && resp.get("svg").is_some());
        }
        let req = Json::parse(r#"{"pieces":[{"name":"r","outline":[[0,0],[10,0],[10,5],[0,5]],"qty":3}],"opts":{"fabric_width":12}}"#).unwrap();
        let resp = nest_request(&req).unwrap();
        assert_eq!(resp.get("placed").and_then(|v| v.as_f64()), Some(3.0));
        assert!(nest_request(&Json::obj()).is_err());
    }

    #[test]
    fn fold_pieces_are_unfolded() {
        use crate::draft::{draft, DraftOpts};
        use crate::model::Measurements;
        let pat = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        let fold = pat.pieces.iter().find(|p| p.nodes.iter().any(|n| n.edge == "cf" || n.edge == "cb")).expect("fold piece");
        let (_, cut) = export::cut_outline(fold);
        let (full, unfolded) = full_cut_outline(fold);
        assert!(unfolded);
        let (ha, fa) = (signed_area(&cut).abs(), signed_area(&full).abs());
        assert!((fa / ha - 2.0).abs() < 0.05, "half {} full {}", ha, fa);
        let (c, note) = clean_outline(&full);
        assert!(note.is_none(), "{:?}", note);
        assert!(c.len() >= 6);
    }

    #[test]
    fn fuzz_random_pieces_always_verify() {
        let mut rng = Rng::new(99);
        for case in 0..40 {
            let np = 2 + rng.below(8);
            let mut pcs = Vec::new();
            for i in 0..np {
                let n = 3 + rng.below(40);
                let (rx, ry) = (3.0 + rng.unit() * 40.0, 3.0 + rng.unit() * 40.0);
                // random star-shaped (sometimes self-intersecting after jitter) polygon
                let mut pts: Vec<V2> = (0..n).map(|k| {
                    let a = k as f64 / n as f64 * std::f64::consts::TAU + if case % 5 == 0 { rng.unit() * 1.5 } else { 0.0 };
                    let r = 0.4 + 0.6 * rng.unit();
                    v2(rx * r * a.cos(), ry * r * a.sin())
                }).collect();
                if case % 7 == 0 { pts.push(pts[0]); pts.push(v2(f64::NAN, 1.0)); }
                let mut p = piece(&format!("p{}", i), pts, 1 + rng.below(4));
                p.allow_flip = rng.below(2) == 0;
                p.grain_deg = [0.0, 90.0, 30.0][rng.below(3)];
                p.rotations = match rng.below(3) { 0 => vec![0.0, 180.0], 1 => vec![0.0, 90.0, 180.0, 270.0], _ => vec![0.0] };
                pcs.push(p);
            }
            let o = NestOpts {
                fabric_width: 40.0 + rng.unit() * 110.0,
                gap: [0.0, 0.5, 2.0][rng.below(3)],
                edge_margin: [0.0, 1.0][rng.below(2)],
                time_budget_iters: 6,
                seed: case as u64,
                one_way_nap: rng.below(4) == 0,
                pair_mirroring: rng.below(2) == 0,
                ..Default::default()
            };
            let r = nest(&pcs, &o).unwrap();
            verify(&pcs, &r, &o).unwrap_or_else(|e| panic!("case {}: {}", case, e));
            assert!(r.efficiency.is_finite());
        }
    }

    #[test]
    fn large_job_stays_responsive() {
        let pcs: Vec<NestPiece> = (0..60).map(|i| piece(&format!("b{}", i), blob(6.0 + (i % 7) as f64, 5.0 + (i % 5) as f64, 40, i as f64), 10)).collect();
        let o = NestOpts::default();
        let t = Instant::now();
        let r = nest(&pcs, &o).unwrap();
        let dt = t.elapsed().as_secs_f64();
        verify(&pcs, &r, &o).unwrap();
        eprintln!("large job: {} copies, eff {:.3}, {:.2}s", r.placements.len(), r.efficiency, dt);
        assert!(dt < 10.0);
    }
}
