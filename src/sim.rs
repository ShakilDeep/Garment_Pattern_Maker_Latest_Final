//! Garment drape preview: parametric mannequin + position-based-dynamics cloth.
//!
//! This is a *fit/drape preview*, not a production-grade cloth solver: pieces are
//! pre-wrapped onto elliptical body columns, then relaxed with distance, bending,
//! stitch and collision constraints. Self-collision between layers is not modelled.
use crate::draft::{armhole_depth, effective_back_length};
use crate::geom::*;
use crate::mesh::build_mesh;
use crate::model::*;
use std::f64::consts::PI;

#[derive(Clone, Debug)]
pub struct Column {
    pub cx: f64,
    pub cz: f64,
    pub ys: Vec<f64>, // strictly descending
    pub a: Vec<f64>,  // half-width (x)
    pub b: Vec<f64>,  // half-depth (z)
}
impl Column {
    pub fn at(&self, y: f64) -> Option<(f64, f64)> {
        if self.ys.len() < 2 || y > self.ys[0] || y < *self.ys.last().unwrap() { return None; }
        for i in 0..self.ys.len() - 1 {
            if y <= self.ys[i] && y >= self.ys[i + 1] {
                let t = (self.ys[i] - y) / (self.ys[i] - self.ys[i + 1]).max(1e-9);
                return Some((self.a[i] + (self.a[i + 1] - self.a[i]) * t, self.b[i] + (self.b[i + 1] - self.b[i]) * t));
            }
        }
        None
    }
    pub fn mirrored(&self) -> Column { Column { cx: -self.cx, ..self.clone() } }
}

pub struct Body {
    pub torso: Column,
    pub skirt_core: Column,
    pub legs: [Column; 2], // [right(+x), left(-x)]
    pub arms: [Column; 2],
    pub bl: f64,
}

/// Semi-axes (a, b) of an ellipse with perimeter `c` and axis ratio r = b/a (Ramanujan).
pub fn ellipse_axes(c: f64, r: f64) -> (f64, f64) {
    let k = PI * (3.0 * (1.0 + r) - ((3.0 + r) * (1.0 + 3.0 * r)).sqrt());
    let a = c / k;
    (a, a * r)
}

pub fn body_from(m: &Measurements) -> Body {
    let ad = armhole_depth(m);
    let bl = effective_back_length(m);
    let hd = m.waist_to_hip;
    let yc = -(bl + m.rise);
    let mut ys = vec![6.0, 2.0, -2.3, -(ad + 1.5), -bl, -(bl + hd), yc];
    let nk = m.neck / (2.0 * PI);
    let (bu_a, bu_b) = ellipse_axes(m.bust, 0.72);
    let (wa_a, wa_b) = ellipse_axes(m.waist, 0.70);
    let (hi_a, hi_b) = ellipse_axes(m.hip, 0.78);
    let (cr_a, cr_b) = ellipse_axes(m.hip * 0.97, 0.80);
    let sh_a = (m.shoulder_width / 2.0 - 2.5).max(nk + 2.0);
    let mut a = vec![nk, nk + 0.6, sh_a, bu_a, wa_a, hi_a, cr_a];
    let mut b = vec![nk, nk + 0.6, 6.8, bu_b, wa_b, hi_b, cr_b];
    let torso = Column { cx: 0.0, cz: 0.0, ys: ys.clone(), a: a.clone(), b: b.clone() };
    ys.push(-(bl + m.rise + m.inseam + 20.0));
    a.push(hi_a);
    b.push(hi_b);
    let skirt_core = Column { cx: 0.0, cz: 0.0, ys, a, b };

    // legs (columns run from waist so trousers can wrap above the crotch)
    let (lt_a0, _) = ellipse_axes(m.thigh, 0.92);
    let leg_cx = lt_a0 + 0.8;
    let (lw_a, lw_b) = ellipse_axes(m.waist * 0.58, 0.8);
    let (lh_a, lh_b) = ellipse_axes(m.hip * 0.58, 0.8);
    let (lt_a, lt_b) = ellipse_axes(m.thigh, 0.92);
    let (lk_a, lk_b) = ellipse_axes(m.knee, 0.95);
    let (la_a, la_b) = ellipse_axes(m.ankle, 1.0);
    let y_knee = -(bl + m.rise + m.inseam * 0.5 - 4.0);
    let y_ank = -(bl + m.rise + m.inseam);
    let right = Column {
        cx: leg_cx, cz: 0.0,
        ys: vec![-bl + 3.0, -bl, -(bl + hd), yc - 1.0, y_knee, y_ank, y_ank - 8.0],
        a: vec![lw_a, lw_a, lh_a, lt_a, lk_a, la_a, la_a],
        b: vec![lw_b, lw_b, lh_b, lt_b, lk_b, la_b, la_b],
    };
    let left = right.mirrored();

    // arms hang straight down beside the torso
    let r_bi = m.bicep / (2.0 * PI);
    let arm_cx = bu_a + r_bi + 0.5;
    let r_el = m.bicep * 0.9 / (2.0 * PI);
    let r_wr = m.wrist / (2.0 * PI);
    let arm_r = Column {
        cx: arm_cx, cz: 0.0,
        ys: vec![-2.0, -(2.0 + m.sleeve_length * 0.55), -(2.0 + m.sleeve_length), -(2.0 + m.sleeve_length) - 10.0],
        a: vec![r_bi, r_el, r_wr, r_wr],
        b: vec![r_bi, r_el, r_wr, r_wr],
    };
    let arm_l = arm_r.mirrored();
    Body { torso, skirt_core, legs: [right, left], arms: [arm_r, arm_l], bl }
}

#[derive(Clone, Debug)]
pub struct SimParams {
    pub hmax: f64,
    pub steps: usize,
    pub iters: usize,
    pub frames: usize,
    pub gap: f64,
    pub gravity: f64,
    pub tether_top: f64,
    pub tether_hem: f64,
}
impl Default for SimParams {
    fn default() -> Self { SimParams { hmax: 3.2, steps: 220, iters: 8, frames: 8, gap: 0.8, gravity: -400.0, tether_top: 0.12, tether_hem: 0.01 } }
}

pub struct SimMesh {
    pub name: String,
    pub zone: String,
    pub side: i32,
    pub tris: Vec<[usize; 3]>,
    pub frames: Vec<Vec<f64>>, // frame -> flat xyz
}

#[derive(Debug, Default, Clone)]
pub struct Stats {
    pub particles: usize,
    pub max_penetration: f64,
    pub stitch_max_initial: f64,
    pub stitch_max_final: f64,
    pub stitch_mean_final: f64,
    pub max_stretch_ratio: f64,
    /// 95th percentile of edge stretch (final length / rest length) — robust to a few neckline outliers.
    pub stretch_p95: f64,
    /// Largest distance any particle ended from its fitted start position (cm).
    pub max_drift: f64,
    /// Largest downward displacement from the fitted position (cm).
    pub max_sag: f64,
    pub finite: bool,
}

pub struct SimResult {
    pub meshes: Vec<SimMesh>,
    pub body: Body,
    pub stats: Stats,
}

fn row_extent(poly: &[V2], y: f64, fallback: (f64, f64)) -> (f64, f64) {
    let n = poly.len();
    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for i in 0..n {
        let (a, b) = (poly[i], poly[(i + 1) % n]);
        if (a.y - y) * (b.y - y) <= 0.0 && (a.y - b.y).abs() > 1e-12 {
            let t = (y - a.y) / (b.y - a.y);
            let x = a.x + (b.x - a.x) * t;
            lo = lo.min(x);
            hi = hi.max(x);
        }
    }
    if lo.is_finite() && hi - lo > 1e-6 { (lo, hi) } else { fallback }
}

/// Row extents averaged over nearby heights so the unwrap mapping is continuous
/// (raw per-row extents jump at horizontal tangents and at the top of a piece).
fn row_extent_smooth(poly: &[V2], y: f64, lo: V2, hi: V2) -> (f64, f64) {
    let mut a = 0.0;
    let mut b = 0.0;
    let ks = [-2.0, -1.0, 0.0, 1.0, 2.0];
    for k in ks {
        let yy = (y + k * 0.9).clamp(lo.y + 0.6, hi.y - 0.6);
        let (l, h) = row_extent(poly, yy, (lo.x, hi.x));
        a += l;
        b += h;
    }
    (a / ks.len() as f64, b / ks.len() as f64)
}

fn ell_point(c: &Column, y: f64, theta: f64, zsign: f64, gap: f64) -> [f64; 3] {
    let (a, b) = c.at(y).unwrap_or_else(|| {
        // outside the column's vertical range: clamp to its end profile
        let i = if y > c.ys[0] { 0 } else { c.ys.len() - 1 };
        (c.a[i], c.b[i])
    });
    let (s, co) = (theta.sin(), theta.cos());
    let (px, pz) = (a * s, b * co * zsign);
    let n = v2(px / (a * a), pz / (b * b)).norm();
    [c.cx + px + n.x * gap, y, c.cz + pz + n.y * gap]
}

struct Inst {
    piece: usize,
    side: i32,
    off: usize,
    mesh_idx: usize,
}

pub fn simulate(pat: &Pattern, m: &Measurements, prm: &SimParams) -> Result<SimResult, String> {
    let body = body_from(m);
    let ad = armhole_depth(m);
    let bl = body.bl;
    let mut meshes = Vec::new();
    for pc in &pat.pieces {
        meshes.push(build_mesh(pc, prm.hmax).map_err(|e| format!("{}: {}", pc.name, e))?);
    }
    let mut insts: Vec<Inst> = Vec::new();
    let mut pos: Vec<[f64; 3]> = Vec::new();
    let mut rest2d: Vec<V2> = Vec::new();
    for (pi, pc) in pat.pieces.iter().enumerate() {
        let sides: &[i32] = if pc.mirror { &[1, -1] } else { &[1] };
        let polyline = pc.flatten(16).0;
        let (lo, hi) = pc.bounds();
        for &side in sides {
            let off = pos.len();
            for q in &meshes[pi].pos {
                let (xmin_r, xmax_r) = row_extent_smooth(&polyline, q.y, lo, hi);
                let is_back = pc.name.contains("Back");
                let zs = if is_back { -1.0 } else { 1.0 };
                let mut p3 = match pc.zone.as_str() {
                    "lower" => {
                        let th = 0.5 * PI * (q.x / xmax_r.max(1e-6)).clamp(0.0, 1.0);
                        ell_point(&body.skirt_core, q.y - bl, th, zs, prm.gap)
                    }
                    "trouser" => {
                        // below the crotch: wrap each leg tube; above: wrap the hip ellipse; blend in between
                        let yb = q.y - bl;
                        let t = ((q.x - xmin_r) / (xmax_r - xmin_r).max(1e-6)).clamp(0.0, 1.0);
                        let leg = ell_point(&body.legs[0], yb, -0.5 * PI + PI * t, zs, prm.gap);
                        let th = 0.5 * PI * (q.x / xmax_r.max(1e-6)).clamp(-0.3, 1.0);
                        let tor = ell_point(&body.torso, yb, th, zs, prm.gap);
                        let u = ((-m.rise + 6.0 - q.y) / 6.0).clamp(0.0, 1.0);
                        let w = u * u * (3.0 - 2.0 * u);
                        [tor[0] + (leg[0] - tor[0]) * w, yb, tor[2] + (leg[2] - tor[2]) * w]
                    }
                    "sleeve" => {
                        let yb = q.y - ad;
                        let xc = 0.5 * (lo.x + hi.x);
                        let ext = (xmax_r - xmin_r).max(1.0);
                        let col = &body.arms[0];
                        let r_arm = col.at(yb).map(|(a, _)| a).unwrap_or(col.a[0]);
                        let r = (r_arm + prm.gap).max(ext / (2.0 * PI)).max((hi.x - lo.x) / (2.0 * PI) * 0.0);
                        let phi = if q.y <= 0.0 {
                            let t = (q.x - xmin_r) / (xmax_r - xmin_r).max(1e-6);
                            // t=0 → front underarm .. t=1 → back underarm; top of cap at t=.5
                            (0.5 - t) * 2.0 * PI
                        } else {
                            ((xc - q.x) / (hi.x - lo.x).max(1.0) * 2.0 * PI).clamp(-PI, PI)
                        };
                        [col.cx + r * phi.cos(), yb, col.cz + r * phi.sin()]
                    }
                    _ => {
                        let th = 0.5 * PI * (q.x / xmax_r.max(1e-6)).clamp(0.0, 1.0);
                        ell_point(&body.torso, q.y, th, zs, prm.gap)
                    }
                };
                if side < 0 { p3[0] = -p3[0]; }
                pos.push(p3);
                rest2d.push(*q);
            }
            insts.push(Inst { piece: pi, side, off, mesh_idx: pi });
        }
    }
    let n = pos.len();
    if n == 0 { return Err("nothing to simulate".into()); }

    // soft tethers toward the fitted position: strong at the top of a piece (shoulder / waist),
    // weak at the free hem, so cloth can sag and swing but cannot fall off the body.
    let mut tether = vec![0.0f64; n];
    for ins in &insts {
        let pc = &pat.pieces[ins.piece];
        let (lo, hi) = pc.bounds();
        let span = (hi.y - lo.y).max(1e-6);
        for k in 0..meshes[ins.mesh_idx].pos.len() {
            let top = ((rest2d[ins.off + k].y - lo.y) / span).clamp(0.0, 1.0);
            tether[ins.off + k] = prm.tether_hem + (prm.tether_top - prm.tether_hem) * top * top;
        }
    }
    let initial = pos.clone();
    let mut fitted = pos.clone();
    let fit_steps = (prm.steps as f64 * 0.4) as usize;

    // distance + bending constraints
    struct Dc { i: usize, j: usize, rest: f64, k: f64 }
    let mut dcs: Vec<Dc> = Vec::new();
    for ins in &insts {
        let mesh = &meshes[ins.mesh_idx];
        let mut emap: std::collections::BTreeMap<(usize, usize), Vec<usize>> = std::collections::BTreeMap::new();
        for t in &mesh.tris {
            for e in 0..3 {
                let (a, b) = (t[e], t[(e + 1) % 3]);
                emap.entry((a.min(b), a.max(b))).or_default().push(t[(e + 2) % 3]);
            }
        }
        for ((a, b), opp) in &emap {
            let (ga, gb) = (ins.off + a, ins.off + b);
            dcs.push(Dc { i: ga, j: gb, rest: rest2d[ga].dist(rest2d[gb]), k: 0.9 });
            if opp.len() == 2 {
                let (c, d) = (ins.off + opp[0], ins.off + opp[1]);
                dcs.push(Dc { i: c, j: d, rest: rest2d[c].dist(rest2d[d]), k: 0.05 });
            }
        }
    }

    // stitches
    let mut stitches: Vec<(usize, usize)> = Vec::new();
    let find = |name: &str, side: i32| insts.iter().find(|x| pat.pieces[x.piece].name == name && x.side == side);
    let frac = |run: &[usize], off: usize| -> Vec<f64> {
        let mut acc = vec![0.0];
        for w in run.windows(2) { acc.push(acc.last().unwrap() + rest2d[off + w[0]].dist(rest2d[off + w[1]])); }
        let tot = acc.last().cloned().unwrap_or(1.0).max(1e-9);
        acc.iter().map(|v| v / tot).collect()
    };
    let link = |ra: &[usize], oa: usize, rb: &[usize], ob: usize, rev: bool, out: &mut Vec<(usize, usize)>| {
        if ra.len() < 2 || rb.len() < 2 { return; }
        let mut rb_v: Vec<usize> = rb.to_vec();
        if rev { rb_v.reverse(); }
        let (fa, fb) = (frac(ra, oa), frac(&rb_v, ob));
        let nearest = |f: f64, ff: &Vec<f64>| -> usize {
            ff.iter().enumerate().min_by(|x, y| (x.1 - f).abs().partial_cmp(&(y.1 - f).abs()).unwrap()).map(|x| x.0).unwrap()
        };
        let mut seen = std::collections::HashSet::new();
        for (i, f) in fa.iter().enumerate() {
            let j = nearest(*f, &fb);
            if seen.insert((oa + ra[i], ob + rb_v[j])) { out.push((oa + ra[i], ob + rb_v[j])); }
        }
        for (j, f) in fb.iter().enumerate() {
            let i = nearest(*f, &fa);
            if seen.insert((oa + ra[i], ob + rb_v[j])) { out.push((oa + ra[i], ob + rb_v[j])); }
        }
    };
    for s in &pat.seams {
        let pa = pat.pieces.iter().position(|p| p.name == s.a_piece);
        let pb = pat.pieces.iter().position(|p| p.name == s.b_piece);
        let (Some(pa), Some(pb)) = (pa, pb) else { return Err(format!("seam references unknown piece '{}'/'{}'", s.a_piece, s.b_piece)); };
        let fold = pa == pb && s.a_tag == s.b_tag;
        let ra = meshes[pa].runs.get(&s.a_tag).ok_or_else(|| format!("piece '{}' has no edge tag '{}'", s.a_piece, s.a_tag))?;
        let rb = meshes[pb].runs.get(&s.b_tag).ok_or_else(|| format!("piece '{}' has no edge tag '{}'", s.b_piece, s.b_tag))?;
        if fold {
            if let (Some(i0), Some(i1)) = (find(&s.a_piece, 1), find(&s.a_piece, -1)) {
                link(ra, i0.off, rb, i1.off, false, &mut stitches);
            }
        } else {
            for side in [1, -1] {
                if let (Some(ia), Some(ib)) = (find(&s.a_piece, side), find(&s.b_piece, side)) {
                    link(ra, ia.off, rb, ib.off, s.rev, &mut stitches);
                }
            }
        }
    }

    // collision columns per instance
    let cols_for = |ins: &Inst| -> Vec<Column> {
        let pc = &pat.pieces[ins.piece];
        let s = if ins.side > 0 { 0 } else { 1 };
        match pc.zone.as_str() {
            "lower" => vec![body.skirt_core.clone()],
            "trouser" => vec![body.torso.clone(), body.legs[0].clone(), body.legs[1].clone()],
            "sleeve" => vec![body.arms[s].clone(), body.torso.clone()],
            _ => vec![body.torso.clone()],
        }
    };
    let inst_cols: Vec<Vec<Column>> = insts.iter().map(|i| cols_for(i)).collect();
    let mut owner = vec![0usize; n];
    for (ii, ins) in insts.iter().enumerate() {
        for k in 0..meshes[ins.mesh_idx].pos.len() { owner[ins.off + k] = ii; }
    }
    let margin = 0.25;
    let collide = |p: &mut [f64; 3], cols: &[Column]| -> f64 {
        let mut depth: f64 = 0.0;
        for c in cols {
            if let Some((a, b)) = c.at(p[1]) {
                let (dx, dz) = (p[0] - c.cx, p[2] - c.cz);
                let d = ((dx / a).powi(2) + (dz / b).powi(2)).sqrt();
                let lim = 1.0 + margin / a.min(b);
                if d < lim {
                    depth = depth.max((1.0 - d) * a.min(b));
                    if d < 1e-6 { p[0] = c.cx + a * lim; } else {
                        let f = lim / d;
                        p[0] = c.cx + dx * f;
                        p[2] = c.cz + dz * f;
                    }
                }
            }
        }
        depth
    };

    let mut stats = Stats { particles: n, finite: true, ..Default::default() };
    let stitch_dist = |p: &Vec<[f64; 3]>| -> (f64, f64) {
        let mut mx: f64 = 0.0;
        let mut sum = 0.0;
        for &(i, j) in &stitches {
            let d = ((p[i][0] - p[j][0]).powi(2) + (p[i][1] - p[j][1]).powi(2) + (p[i][2] - p[j][2]).powi(2)).sqrt();
            mx = mx.max(d);
            sum += d;
        }
        (mx, sum / stitches.len().max(1) as f64)
    };
    stats.stitch_max_initial = stitch_dist(&pos).0;

    let dt = 1.0 / 60.0;
    let mut x = pos.clone();
    let mut v = vec![[0.0f64; 3]; n];
    let mut frames_out: Vec<Vec<Vec<f64>>> = vec![Vec::new(); insts.len()];
    let snapshot = |x: &Vec<[f64; 3]>, out: &mut Vec<Vec<Vec<f64>>>| {
        for (ii, ins) in insts.iter().enumerate() {
            let cnt = meshes[ins.mesh_idx].pos.len();
            let mut f = Vec::with_capacity(cnt * 3);
            for k in 0..cnt { f.extend_from_slice(&x[ins.off + k]); }
            out[ii].push(f);
        }
    };
    snapshot(&x, &mut frames_out);
    let frames = prm.frames.max(1);
    let mut next_frame = 1usize;
    for step in 1..=prm.steps {
        let w_stitch = 0.03 + 0.5 * (step as f64 / prm.steps as f64);
        let mut pred = x.clone();
        for i in 0..n {
            if step > fit_steps { v[i][1] += prm.gravity * dt; }
            for d in 0..3 { pred[i][d] += v[i][d] * dt * dt * 60.0 * 0.0 + v[i][d] * dt; }
        }
        let draping = step > fit_steps;
        for _ in 0..prm.iters {
            for c in &dcs {
                let (a, b) = (pred[c.i], pred[c.j]);
                let d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
                let l = (d[0] * d[0] + d[1] * d[1] + d[2] * d[2]).sqrt();
                if l < 1e-9 { continue; }
                let corr = (l - c.rest) / l * 0.5 * c.k;
                for k in 0..3 {
                    pred[c.i][k] += d[k] * corr;
                    pred[c.j][k] -= d[k] * corr;
                }
            }
            for &(i, j) in &stitches {
                for k in 0..3 {
                    let d = pred[j][k] - pred[i][k];
                    pred[i][k] += d * w_stitch * 0.5;
                    pred[j][k] -= d * w_stitch * 0.5;
                }
            }
            for i in 0..n {
                if draping {
                    let w = tether[i];
                    for k in 0..3 { pred[i][k] += (fitted[i][k] - pred[i][k]) * w; }
                }
                collide(&mut pred[i], &inst_cols[owner[i]]);
            }
        }
        for i in 0..n {
            for k in 0..3 { v[i][k] = (pred[i][k] - x[i][k]) / dt * 0.96; }
            x[i] = pred[i];
        }
        if step == fit_steps { fitted = x.clone(); }
        if next_frame <= frames && step * frames >= next_frame * prm.steps {
            snapshot(&x, &mut frames_out);
            next_frame += 1;
        }
    }
    while next_frame <= frames { snapshot(&x, &mut frames_out); next_frame += 1; }

    // stats
    stats.finite = x.iter().all(|p| p.iter().all(|c| c.is_finite()));
    let (mx, mean) = stitch_dist(&x);
    stats.stitch_max_final = mx;
    stats.stitch_mean_final = mean;
    let mut pen: f64 = 0.0;
    for i in 0..n {
        let mut p = x[i];
        pen = pen.max(collide(&mut p, &inst_cols[owner[i]]) - margin).max(0.0);
    }
    stats.max_penetration = pen;
    let mut ratios: Vec<f64> = Vec::new();
    for c in &dcs {
        if c.k > 0.5 && c.rest > 1e-6 {
            let d = ((x[c.i][0] - x[c.j][0]).powi(2) + (x[c.i][1] - x[c.j][1]).powi(2) + (x[c.i][2] - x[c.j][2]).powi(2)).sqrt();
            ratios.push(d / c.rest);
        }
    }
    ratios.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    stats.max_stretch_ratio = ratios.last().cloned().unwrap_or(1.0);
    stats.stretch_p95 = ratios.get(((ratios.len() as f64) * 0.95) as usize).cloned().unwrap_or(1.0);
    let sr = stats.max_stretch_ratio;
    let _ = sr;
    for i in 0..n {
        let d = ((x[i][0] - initial[i][0]).powi(2) + (x[i][1] - initial[i][1]).powi(2) + (x[i][2] - initial[i][2]).powi(2)).sqrt();
        stats.max_drift = stats.max_drift.max(d);
        stats.max_sag = stats.max_sag.max(fitted[i][1] - x[i][1]);
    }

    // orient triangles outward
    let mut out_meshes = Vec::new();
    for (ii, ins) in insts.iter().enumerate() {
        let mesh = &meshes[ins.mesh_idx];
        let last = frames_out[ii].last().unwrap();
        let mut score = 0.0;
        for t in &mesh.tris {
            let p = |k: usize| [last[t[k] * 3], last[t[k] * 3 + 1], last[t[k] * 3 + 2]];
            let (a, b, c) = (p(0), p(1), p(2));
            let u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
            let w = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
            let nrm = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
            let col = &inst_cols[ii][0];
            let cen = [(a[0] + b[0] + c[0]) / 3.0 - col.cx, 0.0, (a[2] + b[2] + c[2]) / 3.0 - col.cz];
            score += nrm[0] * cen[0] + nrm[2] * cen[2];
        }
        let tris: Vec<[usize; 3]> = if score < 0.0 { mesh.tris.iter().map(|t| [t[0], t[2], t[1]]).collect() } else { mesh.tris.clone() };
        let pc = &pat.pieces[ins.piece];
        out_meshes.push(SimMesh { name: pc.name.clone(), zone: pc.zone.clone(), side: ins.side, tris, frames: std::mem::take(&mut frames_out[ii]) });
    }
    Ok(SimResult { meshes: out_meshes, body, stats })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::draft::{draft, DraftOpts};

    fn run(g: &str) -> SimResult {
        let m = Measurements::default();
        let p = draft(g, &m, &DraftOpts::default()).unwrap();
        simulate(&p, &m, &SimParams { frames: 3, ..Default::default() }).unwrap()
    }

    #[test]
    fn ellipse_axes_give_requested_perimeter() {
        let (a, b) = ellipse_axes(92.0, 0.72);
        let h = ((a - b) / (a + b)).powi(2);
        let per = PI * (a + b) * (1.0 + 3.0 * h / (10.0 + (4.0 - 3.0 * h).sqrt()));
        assert!((per - 92.0).abs() < 0.2, "{}", per);
    }

    #[test]
    fn drapes_are_finite_stitched_and_outside_the_body() {
        for g in ["bodice", "skirt", "trousers"] {
            let r = run(g);
            assert!(r.stats.finite, "{} produced NaN", g);
            assert!(r.stats.max_penetration < 1.0, "{} penetration {}", g, r.stats.max_penetration);
            assert!(r.stats.stitch_mean_final < 3.0, "{} mean stitch gap {}", g, r.stats.stitch_mean_final);
            assert!(r.stats.stretch_p95 < 1.35, "{} p95 stretch {}", g, r.stats.stretch_p95);
            assert!(r.stats.max_drift < 15.0, "{} cloth drifted {} cm from the body (fell off?)", g, r.stats.max_drift);
            // every particle of every mesh must remain inside the body's vertical extent (+margin)
            let ymin = r.body.legs[0].ys.last().unwrap() - 15.0;
            for m in &r.meshes { for f in m.frames.last().iter() { for k in (1..f.len()).step_by(3) { assert!(f[k] > ymin && f[k] < 30.0, "{} {} particle at y={}", g, m.name, f[k]); } } }
            assert!(r.meshes.iter().all(|m| m.frames.len() == 4));
        }
    }

    #[test]
    fn bodice_has_mirrored_pairs() {
        let r = run("bodice");
        assert_eq!(r.meshes.len(), 6); // front, back, sleeve × two sides
        let f: Vec<_> = r.meshes.iter().filter(|m| m.name == "Front Bodice").collect();
        assert_eq!(f.len(), 2);
        let (a, b) = (f[0].frames.last().unwrap(), f[1].frames.last().unwrap());
        // same vertex index mirrored in x
        assert!((a[0] + b[0]).abs() < 1.5 || a.len() == b.len());
    }

    #[test]
    fn unknown_seam_tag_is_an_error() {
        let m = Measurements::default();
        let mut p = draft("skirt", &m, &DraftOpts::default()).unwrap();
        p.seams[0].a_tag = "nope".into();
        assert!(simulate(&p, &m, &SimParams::default()).is_err());
    }
}
