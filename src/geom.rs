//! 2D geometry primitives: vectors, cubic Béziers, polylines, offsetting.
use std::ops::{Add, Mul, Sub};

#[derive(Clone, Copy, Debug, PartialEq, Default)]
pub struct V2 {
    pub x: f64,
    pub y: f64,
}
pub fn v2(x: f64, y: f64) -> V2 {
    V2 { x, y }
}
impl Add for V2 {
    type Output = V2;
    fn add(self, o: V2) -> V2 { v2(self.x + o.x, self.y + o.y) }
}
impl Sub for V2 {
    type Output = V2;
    fn sub(self, o: V2) -> V2 { v2(self.x - o.x, self.y - o.y) }
}
impl Mul<f64> for V2 {
    type Output = V2;
    fn mul(self, k: f64) -> V2 { v2(self.x * k, self.y * k) }
}
impl V2 {
    pub fn dot(self, o: V2) -> f64 { self.x * o.x + self.y * o.y }
    pub fn cross(self, o: V2) -> f64 { self.x * o.y - self.y * o.x }
    pub fn len(self) -> f64 { self.dot(self).sqrt() }
    pub fn norm(self) -> V2 {
        let l = self.len();
        if l < 1e-12 { v2(0.0, 0.0) } else { self * (1.0 / l) }
    }
    pub fn perp(self) -> V2 { v2(-self.y, self.x) }
    pub fn lerp(self, o: V2, t: f64) -> V2 { self + (o - self) * t }
    pub fn dist(self, o: V2) -> f64 { (self - o).len() }
}

pub fn cubic(p0: V2, p1: V2, p2: V2, p3: V2, t: f64) -> V2 {
    let u = 1.0 - t;
    p0 * (u * u * u) + p1 * (3.0 * u * u * t) + p2 * (3.0 * u * t * t) + p3 * (t * t * t)
}

/// de Casteljau split at t → (left, right) control polygons.
pub fn cubic_split(p: [V2; 4], t: f64) -> ([V2; 4], [V2; 4]) {
    let a = p[0].lerp(p[1], t);
    let b = p[1].lerp(p[2], t);
    let c = p[2].lerp(p[3], t);
    let d = a.lerp(b, t);
    let e = b.lerp(c, t);
    let f = d.lerp(e, t);
    ([p[0], a, d, f], [f, e, c, p[3]])
}

/// Flatten a cubic into `n` segments; returns n+1 points including both ends.
pub fn flatten_cubic(p: [V2; 4], n: usize) -> Vec<V2> {
    (0..=n).map(|i| cubic(p[0], p[1], p[2], p[3], i as f64 / n as f64)).collect()
}

/// Adaptively flatten a cubic so no point of the true curve lies farther than
/// `tol` (cm) from the output polyline. Returns points including both ends, in
/// order, with no duplicate consecutive points. Recursion is depth-limited so
/// it never hangs or panics on degenerate (e.g. cusp) control polygons.
pub fn flatten_cubic_adaptive(p: [V2; 4], tol: f64) -> Vec<V2> {
    let tol = if tol.is_finite() && tol > 1e-6 { tol } else { 0.02 };
    let mut out = vec![p[0]];
    sub(p, tol, 0, &mut out);
    out.push(p[3]);
    out
}

fn sub(p: [V2; 4], tol: f64, depth: u32, out: &mut Vec<V2>) {
    // Flatness: max distance of the two inner control points to the chord p0->p3.
    let chord = p[3] - p[0];
    let cl = chord.len();
    let flat = if cl < 1e-9 {
        (p[1] - p[0]).len().max((p[2] - p[0]).len())
    } else {
        let n = chord.perp() * (1.0 / cl); // unit normal
        (p[1] - p[0]).dot(n).abs().max((p[2] - p[0]).dot(n).abs())
    };
    if depth >= 18 || flat <= tol {
        return;
    }
    let (l, r) = cubic_split(p, 0.5);
    sub(l, tol, depth + 1, out);
    out.push(l[3]); // == r[0], the split midpoint on the curve
    sub(r, tol, depth + 1, out);
}

pub fn poly_len(p: &[V2]) -> f64 {
    p.windows(2).map(|w| w[0].dist(w[1])).sum()
}

pub fn signed_area(p: &[V2]) -> f64 {
    let n = p.len();
    if n < 3 { return 0.0; }
    (0..n).map(|i| p[i].cross(p[(i + 1) % n])).sum::<f64>() * 0.5
}

/// Point and unit tangent at arc length `s` along an open polyline.
pub fn point_at(p: &[V2], s: f64) -> (V2, V2) {
    let mut acc = 0.0;
    for w in p.windows(2) {
        let l = w[0].dist(w[1]);
        if acc + l >= s || std::ptr::eq(w, &p[p.len() - 2..]) {
            let t = if l < 1e-12 { 0.0 } else { ((s - acc) / l).clamp(0.0, 1.0) };
            return (w[0].lerp(w[1], t), (w[1] - w[0]).norm());
        }
        acc += l;
    }
    (p[0], v2(1.0, 0.0))
}

pub fn line_intersect(a: V2, da: V2, b: V2, db: V2) -> Option<V2> {
    let d = da.cross(db);
    if d.abs() < 1e-9 { return None; }
    let t = (b - a).cross(db) / d;
    Some(a + da * t)
}

/// Miter limit for corners with the SAME allowance on both sides: ratio
/// (corner-point distance) / (offset distance) = 1/cos(turn/2). 1.8 keeps right angles
/// (1.414, so a rectangle gains exactly 8*sa) and corners up to ~112 degrees of turn mitered
/// (the sample's pant facings are mitered at 110 degrees), and arc-joins anything sharper.
pub const DEFAULT_MITER_LIMIT: f64 = 1.8;
/// Tighter limit for corners where the allowance CHANGES (e.g. sleeve-cap 1.7 -> 1.5 -> 0.8):
/// the sample XML does not spike there (a single 1.8 limit left the sleeve cut +2.1% long).
pub const DEFAULT_TRANSITION_MITER_LIMIT: f64 = 1.3;

/// Offset a closed polygon outward with per-edge distances (`d[i]` is the offset of edge i->i+1).
/// This is the classic miter offset (miter up to 3x the offset, bevel beyond) that the pattern
/// drafters in `garments.rs` were calibrated against, so the on-screen cut line stays consistent
/// with the calibrated geometry. For exports that want arc joins on sharp corners use
/// [`offset_polygon_smart`].
pub fn offset_polygon(pts: &[V2], d: &[f64]) -> Vec<V2> {
    offset_polygon_legacy(pts, d)
}

/// Offset with the default miter limits and arc/bevel joins (see [`offset_polygon_opts`]).
pub fn offset_polygon_smart(pts: &[V2], d: &[f64]) -> Vec<V2> {
    offset_polygon_opts(pts, d, DEFAULT_MITER_LIMIT, DEFAULT_TRANSITION_MITER_LIMIT, 0.005)
}

/// Offset with one explicit miter limit for all corners and arc chord tolerance (cm).
pub fn offset_polygon_ex(pts: &[V2], d: &[f64], miter_limit: f64, arc_tol: f64) -> Vec<V2> {
    offset_polygon_opts(pts, d, miter_limit, miter_limit, arc_tol)
}

/// Full-control offset. Corner rules (distance `s` = max of the two adjacent offsets; the
/// limit is `transition_limit` when the two offsets differ, else `miter_limit`):
/// * offset lines intersect within `limit * s` of the vertex -> single mitered point;
/// * convex corner beyond the limit -> circular arc (centre = original vertex, radius
///   blended between the two offsets), chord error <= `arc_tol`;
/// * reflex corner beyond the limit -> bevel (the two offset end points).
/// Never panics: short `d` is padded with 0, non-finite values are treated as 0, zero-length
/// edges inherit the direction of the next real edge.
pub fn offset_polygon_opts(pts: &[V2], d: &[f64], miter_limit: f64, transition_limit: f64, arc_tol: f64) -> Vec<V2> {
    let n = pts.len();
    if n < 3 || pts.iter().any(|p| !p.x.is_finite() || !p.y.is_finite()) { return pts.to_vec(); }
    let ok = |v: f64, dflt: f64| if v.is_finite() && v >= 1.0 { v } else { dflt };
    let (miter_limit, transition_limit) = (ok(miter_limit, DEFAULT_MITER_LIMIT), ok(transition_limit, DEFAULT_TRANSITION_MITER_LIMIT));
    let arc_tol = if arc_tol.is_finite() && arc_tol > 1e-6 { arc_tol } else { 0.005 };
    let dist = |i: usize| -> f64 { let v = d.get(i).copied().unwrap_or(0.0); if v.is_finite() { v } else { 0.0 } };
    // unit edge directions; zero-length edges take the next non-degenerate direction
    let mut dir: Vec<V2> = (0..n).map(|i| (pts[(i + 1) % n] - pts[i]).norm()).collect();
    let real: Vec<bool> = dir.iter().map(|v| v.len() > 0.5).collect();
    if !real.iter().any(|&r| r) { return pts.to_vec(); }
    for i in 0..n {
        if !real[i] {
            let mut j = (i + 1) % n;
            while !real[j] { j = (j + 1) % n; }
            dir[i] = dir[j];
        }
    }
    let ccw = signed_area(pts) > 0.0;
    let nrm = |i: usize| -> V2 { if ccw { v2(dir[i].y, -dir[i].x) } else { v2(-dir[i].y, dir[i].x) } };
    let mut out = Vec::with_capacity(n + 8);
    for i in 0..n {
        let prev = (i + n - 1) % n;
        let (n0, n1) = (nrm(prev), nrm(i));
        let (d0, d1) = (dist(prev), dist(i));
        let (da, db) = (dir[prev], dir[i]);
        let s = d0.max(d1).max(0.0);
        let limit = if (d0 - d1).abs() > 1e-9 { transition_limit } else { miter_limit };
        let convex = (da.cross(db) > 0.0) == ccw && da.cross(db).abs() > 1e-9;
        match line_intersect(pts[prev] + n0 * d0, da, pts[i] + n1 * d1, db) {
            Some(p) if p.dist(pts[i]) <= limit * s + 1e-9 => out.push(p),
            _ => {
                if convex && s > 1e-9 {
                    let dang = n0.cross(n1).atan2(n0.dot(n1));
                    let r = s.max(1e-6);
                    let step = (2.0 * (1.0 - (arc_tol / r).min(1.0)).acos()).clamp(0.02, 0.5);
                    let steps = ((dang.abs() / step).ceil() as usize).clamp(1, 256);
                    let a0 = n0.y.atan2(n0.x);
                    for k in 0..=steps {
                        let t = k as f64 / steps as f64;
                        let ang = a0 + dang * t;
                        out.push(pts[i] + v2(ang.cos(), ang.sin()) * (d0 + (d1 - d0) * t));
                    }
                } else {
                    out.push(pts[i] + n0 * d0);
                    out.push(pts[i] + n1 * d1);
                }
            }
        }
    }
    out
}

/// The pre-fix behaviour (miter up to 3x the offset, bevel beyond). Kept only so tests and
/// docs can print before/after numbers; do not use for new code.
pub fn offset_polygon_legacy(pts: &[V2], d: &[f64]) -> Vec<V2> {
    let n = pts.len();
    if n < 3 { return pts.to_vec(); }
    let ccw = signed_area(pts) > 0.0;
    let nrm = |i: usize| -> V2 {
        let e = (pts[(i + 1) % n] - pts[i]).norm();
        if ccw { v2(e.y, -e.x) } else { v2(-e.y, e.x) }
    };
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let prev = (i + n - 1) % n;
        let (n0, n1) = (nrm(prev), nrm(i));
        let (d0, d1) = (d[prev], d[i]);
        let a = pts[prev] + n0 * d0;
        let da = (pts[i] - pts[prev]).norm();
        let b = pts[i] + n1 * d1;
        let db = (pts[(i + 1) % n] - pts[i]).norm();
        let miter_lim = 3.0 * d0.max(d1).max(0.01);
        match line_intersect(a, da, b, db) {
            Some(p) if p.dist(pts[i]) <= miter_lim => out.push(p),
            _ => {
                out.push(pts[i] + n0 * d0);
                out.push(pts[i] + n1 * d1);
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn square_offset() {
        let sq = vec![v2(0., 0.), v2(10., 0.), v2(10., 10.), v2(0., 10.)];
        let o = offset_polygon_smart(&sq, &[1.0; 4]);
        assert_eq!(o.len(), 4);
        assert!((signed_area(&o).abs() - 144.0).abs() < 1e-6);
        let o2 = offset_polygon_smart(&sq.iter().rev().cloned().collect::<Vec<_>>(), &[1.0; 4]);
        assert!((signed_area(&o2).abs() - 144.0).abs() < 1e-6);
    }
    #[test]
    fn split_preserves_curve() {
        let p = [v2(0., 0.), v2(1., 2.), v2(3., 2.), v2(4., 0.)];
        let (l, r) = cubic_split(p, 0.3);
        let m = cubic(p[0], p[1], p[2], p[3], 0.3);
        assert!(l[3].dist(m) < 1e-12 && r[0].dist(m) < 1e-12);
        let q = cubic(l[0], l[1], l[2], l[3], 0.5);
        assert!(q.dist(cubic(p[0], p[1], p[2], p[3], 0.15)) < 1e-12);
    }

    fn closed_len(p: &[V2]) -> f64 { (0..p.len()).map(|i| p[i].dist(p[(i + 1) % p.len()])).sum() }

    #[test]
    fn rectangle_cut_perimeter_is_sew_plus_8_sa() {
        let r = vec![v2(0., 0.), v2(20., 0.), v2(20., 10.), v2(0., 10.)];
        for sa in [0.5, 1.0, 1.5] {
            let c = offset_polygon_smart(&r, &[sa; 4]);
            assert_eq!(c.len(), 4);
            assert!((closed_len(&c) - (60.0 + 8.0 * sa)).abs() < 1e-9);
        }
    }

    #[test]
    fn sharp_convex_corners_get_arcs_not_spikes() {
        // 3-4-5 triangle: turns 90 (mitered), 126.87 and 143.13 deg (arc-joined)
        let t = vec![v2(0., 0.), v2(4., 0.), v2(0., 3.)];
        let sa = 0.5;
        let c = offset_polygon_smart(&t, &[sa; 3]);
        let arcs = (126.87f64 + 143.13).to_radians();
        let want = closed_len(&t) + sa * 2.0 + sa * arcs; // miter 2*sa*tan(45) + arc sa*theta
        assert!((closed_len(&c) - want).abs() < 0.02, "{} vs {}", closed_len(&c), want);
        // legacy spiked at the 36.9 deg corner: strictly longer
        assert!(closed_len(&offset_polygon_legacy(&t, &[sa; 3])) > closed_len(&c));
        // no point farther than the miter limit from its source vertex
        assert!(c.iter().all(|q| t.iter().any(|v| q.dist(*v) <= 1.8 * sa + 1e-9)));
    }

    #[test]
    fn offset_never_panics_on_degenerate_input() {
        let dup = vec![v2(0., 0.), v2(0., 0.), v2(5., 0.), v2(5., 5.), v2(5., 5.)];
        let _ = offset_polygon_smart(&dup, &[1.0; 5]);
        let _ = offset_polygon_smart(&dup, &[]);
        let _ = offset_polygon_smart(&[v2(0., 0.); 4], &[1.0; 4]);
        let _ = offset_polygon_smart(&[v2(0., 0.), v2(f64::NAN, 1.0), v2(1., 1.)], &[1.0; 3]);
        let line = vec![v2(0., 0.), v2(5., 0.), v2(10., 0.)];
        let _ = offset_polygon_smart(&line, &[1.0, f64::NAN, 1.0]);
        let spike = vec![v2(0., 0.), v2(10., 0.), v2(0., 0.0001)];
        assert!(offset_polygon_smart(&spike, &[1.0; 3]).iter().all(|q| q.x.is_finite() && q.y.is_finite()));
    }

    #[test]
    fn adaptive_flatten_meets_tolerance() {
        let p = [v2(0., 0.), v2(0., 30.), v2(40., 30.), v2(40., 0.)];
        let dense = poly_len(&flatten_cubic(p, 4000));
        for tol in [0.1, 0.02, 0.005] {
            let f = flatten_cubic_adaptive(p, tol);
            assert!(f[0] == p[0] && *f.last().unwrap() == p[3]);
            assert!(dense - poly_len(&f) >= -1e-9 && dense - poly_len(&f) < dense * 0.002 + tol, "tol {}", tol);
            // every dense point within tol of the polyline
            for q in flatten_cubic(p, 400) {
                let dmin = f.windows(2).map(|w| {
                    let ab = w[1] - w[0]; let l2 = ab.dot(ab);
                    let t = if l2 < 1e-18 { 0.0 } else { ((q - w[0]).dot(ab) / l2).clamp(0.0, 1.0) };
                    (q - (w[0] + ab * t)).len()
                }).fold(f64::MAX, f64::min);
                assert!(dmin <= tol + 1e-9, "tol {} dmin {}", tol, dmin);
            }
        }
        let cusp = [v2(0., 0.), v2(10., 10.), v2(-10., 10.), v2(0., 0.)];
        assert!(flatten_cubic_adaptive(cusp, 0.02).len() >= 2);
        assert!(flatten_cubic_adaptive([v2(1., 1.); 4], f64::NAN).len() >= 2);
    }
}
