//! Piece triangulation: ear clipping + conformal longest-edge refinement.
use crate::geom::*;
use crate::model::*;
use std::collections::HashMap;

pub struct Mesh {
    pub pos: Vec<V2>,
    pub tris: Vec<[usize; 3]>,
    /// For each edge tag: boundary vertex indices ordered along the outline direction.
    pub runs: HashMap<String, Vec<usize>>,
    pub boundary: Vec<usize>,
}

fn seg_cross(a: V2, b: V2, c: V2, d: V2) -> bool {
    let d1 = (b - a).cross(c - a);
    let d2 = (b - a).cross(d - a);
    let d3 = (d - c).cross(a - c);
    let d4 = (d - c).cross(b - c);
    d1 * d2 < -1e-12 && d3 * d4 < -1e-12
}

pub fn self_intersects(p: &[V2]) -> bool {
    let n = p.len();
    for i in 0..n {
        let (a, b) = (p[i], p[(i + 1) % n]);
        for j in (i + 2)..n {
            if i == 0 && j == n - 1 { continue; }
            if seg_cross(a, b, p[j], p[(j + 1) % n]) { return true; }
        }
    }
    false
}

fn in_tri(p: V2, a: V2, b: V2, c: V2, sign: f64) -> bool {
    let e = -1e-9;
    (b - a).cross(p - a) * sign >= e && (c - b).cross(p - b) * sign >= e && (a - c).cross(p - c) * sign >= e
}

fn ear_clip(p: &[V2]) -> Result<Vec<[usize; 3]>, String> {
    let n = p.len();
    let sign = if signed_area(p) > 0.0 { 1.0 } else { -1.0 };
    let mut idx: Vec<usize> = (0..n).collect();
    let mut tris = Vec::new();
    while idx.len() > 3 {
        let m = idx.len();
        let mut best: Option<usize> = None;
        let mut collinear: Option<usize> = None;
        for k in 0..m {
            let (i0, i1, i2) = (idx[(k + m - 1) % m], idx[k], idx[(k + 1) % m]);
            let (a, b, c) = (p[i0], p[i1], p[i2]);
            let cr = (b - a).cross(c - b) * sign;
            if cr < -1e-12 { continue; }
            let ok = idx.iter().all(|&j| j == i0 || j == i1 || j == i2 || !in_tri(p[j], a, b, c, sign) || p[j].dist(a) < 1e-9 || p[j].dist(b) < 1e-9 || p[j].dist(c) < 1e-9);
            if !ok { continue; }
            if cr > 1e-9 { best = Some(k); break; }
            if collinear.is_none() { collinear = Some(k); }
        }
        let k = best.or(collinear).ok_or("triangulation failed: outline is self-intersecting or degenerate")?;
        let (i0, i1, i2) = (idx[(k + m - 1) % m], idx[k], idx[(k + 1) % m]);
        tris.push([i0, i1, i2]);
        idx.remove(k);
    }
    tris.push([idx[0], idx[1], idx[2]]);
    Ok(tris)
}

fn point_in_poly(q: V2, p: &[V2]) -> bool {
    let n = p.len();
    let mut inside = false;
    let mut j = n - 1;
    for i in 0..n {
        if (p[i].y > q.y) != (p[j].y > q.y) && q.x < (p[j].x - p[i].x) * (q.y - p[i].y) / (p[j].y - p[i].y) + p[i].x {
            inside = !inside;
        }
        j = i;
    }
    inside
}

fn dist_to_boundary(q: V2, p: &[V2]) -> f64 {
    let n = p.len();
    let mut best = f64::INFINITY;
    for i in 0..n {
        let (a, b) = (p[i], p[(i + 1) % n]);
        let ab = b - a;
        let t = ((q - a).dot(ab) / ab.dot(ab).max(1e-12)).clamp(0.0, 1.0);
        best = best.min(q.dist(a + ab * t));
    }
    best
}

/// Lawson edge flips until the triangulation is (constrained) Delaunay.
fn delaunay_flips(tris: &mut Vec<[usize; 3]>, pos: &[V2]) {
    for _ in 0..400 {
        let mut emap: std::collections::BTreeMap<(usize, usize), Vec<(usize, usize)>> = std::collections::BTreeMap::new();
        for (ti, t) in tris.iter().enumerate() {
            for e in 0..3 {
                let (a, b) = (t[e], t[(e + 1) % 3]);
                emap.entry((a.min(b), a.max(b))).or_default().push((ti, e));
            }
        }
        let mut touched = vec![false; tris.len()];
        let mut flips = 0;
        for (_, v) in emap.iter() {
            if v.len() != 2 { continue; }
            let ((t1, e1), (t2, e2)) = (v[0], v[1]);
            if touched[t1] || touched[t2] { continue; }
            let (a, b, c) = (tris[t1][e1], tris[t1][(e1 + 1) % 3], tris[t1][(e1 + 2) % 3]);
            let d = tris[t2][(e2 + 2) % 3];
            let _ = (e2, a, b);
            let (pa, pb, pc, pd) = (pos[a], pos[b], pos[c], pos[d]);
            let sign = tri_area(pa, pb, pc).signum();
            // in-circle: d inside circumcircle of (a,b,c)?
            let (ax, ay, bx, by, cx, cy) = (pa.x - pd.x, pa.y - pd.y, pb.x - pd.x, pb.y - pd.y, pc.x - pd.x, pc.y - pd.y);
            let det = (ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay) + (cx * cx + cy * cy) * (ax * by - bx * ay);
            if det * sign > 1e-9 {
                // new triangles [a,d,c] and [d,b,c] must keep orientation
                let (n1, n2) = (tri_area(pa, pd, pc) * sign, tri_area(pd, pb, pc) * sign);
                if n1 > 1e-9 && n2 > 1e-9 {
                    tris[t1] = [a, d, c];
                    tris[t2] = [d, b, c];
                    touched[t1] = true;
                    touched[t2] = true;
                    flips += 1;
                }
            }
        }
        if flips == 0 { break; }
    }
}

pub fn tri_area(a: V2, b: V2, c: V2) -> f64 {
    0.5 * (b - a).cross(c - a)
}

pub fn build_mesh(piece: &Piece, hmax: f64) -> Result<Mesh, String> {
    let hmax = hmax.max(0.8);
    let (pts0, seg0) = piece.flatten(10);
    // drop zero-length segments
    let n0 = pts0.len();
    let mut pts = Vec::new();
    let mut seg = Vec::new();
    let mut node_first: HashMap<usize, usize> = HashMap::new(); // node idx -> index in pts
    for k in 0..n0 {
        if pts0[k].dist(pts0[(k + 1) % n0]) > 1e-7 {
            node_first.entry(seg0[k]).or_insert(pts.len());
            pts.push(pts0[k]);
            seg.push(seg0[k]);
        }
    }
    if pts.len() < 3 { return Err("degenerate outline".into()); }
    if self_intersects(&pts) { return Err("outline self-intersects".into()); }
    // pre-split long boundary segments
    let n = pts.len();
    let mut bp: Vec<V2> = Vec::new();
    let mut btag: Vec<usize> = Vec::new();
    let mut map_orig: Vec<usize> = Vec::new();
    for k in 0..n {
        map_orig.push(bp.len());
        let (a, b) = (pts[k], pts[(k + 1) % n]);
        let parts = (a.dist(b) / hmax).ceil().max(1.0) as usize;
        for j in 0..parts {
            bp.push(a.lerp(b, j as f64 / parts as f64));
            btag.push(seg[k]);
        }
    }
    let nb = bp.len();
    let mut tris = ear_clip(&bp)?;
    let mut pos = bp.clone();
    // directed boundary edges
    let mut dir: HashMap<(usize, usize), usize> = HashMap::new();
    for k in 0..nb { dir.insert((k, (k + 1) % nb), btag[k]); }

    // interior hex-lattice points
    {
        let h = hmax * 0.9;
        let (mut lo, mut hi) = (bp[0], bp[0]);
        for q in &bp { lo = v2(lo.x.min(q.x), lo.y.min(q.y)); hi = v2(hi.x.max(q.x), hi.y.max(q.y)); }
        let mut row = 0usize;
        let mut y = lo.y + h * 0.5;
        let mut cand = Vec::new();
        while y < hi.y {
            let mut x = lo.x + if row % 2 == 0 { h * 0.25 } else { h * 0.75 };
            while x < hi.x {
                let q = v2(x, y);
                if point_in_poly(q, &bp) && dist_to_boundary(q, &bp) > 0.6 * h { cand.push(q); }
                x += h;
            }
            y += h * 0.866;
            row += 1;
        }
        for q in cand {
            let sign = if signed_area(&bp) > 0.0 { 1.0 } else { -1.0 };
            let mut hit = None;
            for (ti, t) in tris.iter().enumerate() {
                let (a, b, c) = (pos[t[0]], pos[t[1]], pos[t[2]]);
                let e = 1e-9;
                if (b - a).cross(q - a) * sign > e && (c - b).cross(q - b) * sign > e && (a - c).cross(q - c) * sign > e { hit = Some(ti); break; }
            }
            if let Some(ti) = hit {
                let t = tris[ti];
                let m = pos.len();
                pos.push(q);
                tris[ti] = [t[0], t[1], m];
                tris.push([t[1], t[2], m]);
                tris.push([t[2], t[0], m]);
            }
        }
        delaunay_flips(&mut tris, &pos);
    }

    // safety net: bisect any remaining over-long edges
    let mut guard = 0;
    loop {
        guard += 1;
        if guard > 60000 || tris.len() > 30000 { return Err("mesh refinement exceeded limits".into()); }
        let mut worst = (hmax * 1.7, usize::MAX, 0usize);
        for (ti, t) in tris.iter().enumerate() {
            for e in 0..3 {
                let l = pos[t[e]].dist(pos[t[(e + 1) % 3]]);
                if l > worst.0 { worst = (l, ti, e); }
            }
        }
        if worst.1 == usize::MAX { break; }
        let (u, v) = (tris[worst.1][worst.2], tris[worst.1][(worst.2 + 1) % 3]);
        let m = pos.len();
        pos.push(pos[u].lerp(pos[v], 0.5));
        let mut out: Vec<[usize; 3]> = Vec::with_capacity(tris.len() + 2);
        for t in tris.iter() {
            let mut split = false;
            for e in 0..3 {
                let (a, b, c) = (t[e], t[(e + 1) % 3], t[(e + 2) % 3]);
                if (a == u && b == v) || (a == v && b == u) {
                    out.push([a, m, c]);
                    out.push([m, b, c]);
                    split = true;
                    break;
                }
            }
            if !split { out.push(*t); }
        }
        tris = out;
        for (a, b) in [(u, v), (v, u)] {
            if let Some(tag) = dir.remove(&(a, b)) {
                dir.insert((a, m), tag);
                dir.insert((m, b), tag);
            }
        }
    }

    // ordered boundary runs per tag
    let next: HashMap<usize, usize> = dir.keys().cloned().collect();
    let mut runs: HashMap<String, Vec<usize>> = HashMap::new();
    let nn = piece.nodes.len();
    for i in 0..nn {
        let tag = piece.nodes[i].edge.clone();
        let Some(&start_o) = node_first.get(&i) else { continue };
        let start = map_orig[start_o];
        let end_node = (i + 1) % nn;
        let end = match node_first.get(&end_node) { Some(&o) => map_orig[o], None => start };
        let run = runs.entry(tag).or_default();
        let mut cur = start;
        let mut first = true;
        let mut steps = 0;
        loop {
            if !(first && run.last() == Some(&cur)) { run.push(cur); }
            first = false;
            if cur == end { break; }
            cur = *next.get(&cur).ok_or("broken boundary walk")?;
            steps += 1;
            if steps > 100000 { return Err("boundary walk did not terminate".into()); }
        }
    }
    let mut boundary = Vec::new();
    let mut cur = 0usize;
    for _ in 0..next.len() { boundary.push(cur); cur = next[&cur]; if cur == 0 { break; } }
    Ok(Mesh { pos, tris, runs, boundary })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::draft::{draft, DraftOpts};

    #[test]
    fn meshes_cover_piece_area_with_consistent_winding() {
        let m = Measurements::default();
        for g in ["bodice", "skirt", "trousers"] {
            let p = draft(g, &m, &DraftOpts::default()).unwrap();
            for pc in &p.pieces {
                let mesh = build_mesh(pc, 3.0).unwrap();
                let total: f64 = mesh.tris.iter().map(|t| tri_area(mesh.pos[t[0]], mesh.pos[t[1]], mesh.pos[t[2]])).sum();
                let sign = total.signum();
                assert!((total.abs() - pc.area()).abs() / pc.area() < 0.01, "{} {} vs {}", pc.name, total.abs(), pc.area());
                let neg = mesh.tris.iter().filter(|t| tri_area(mesh.pos[t[0]], mesh.pos[t[1]], mesh.pos[t[2]]) * sign < -1e-9).count();
                assert_eq!(neg, 0, "{} has flipped triangles", pc.name);
                for t in &mesh.tris {
                    for e in 0..3 { assert!(mesh.pos[t[e]].dist(mesh.pos[t[(e + 1) % 3]]) <= 3.0 * 1.7 + 0.01); }
                }
            }
        }
    }

    #[test]
    fn runs_follow_outline_direction_and_length() {
        let p = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        let pc = p.piece("Back Bodice").unwrap();
        let mesh = build_mesh(pc, 2.5).unwrap();
        for tag in ["neck", "shoulder", "armhole", "side", "hem", "cb"] {
            let run = &mesh.runs[tag];
            let len: f64 = run.windows(2).map(|w| mesh.pos[w[0]].dist(mesh.pos[w[1]])).sum();
            let want = pc.tag_len(tag);
            assert!((len - want).abs() / want < 0.04, "{} {} vs {}", tag, len, want);
        }
        let sh = &mesh.runs["shoulder"];
        assert!(mesh.pos[sh[0]].dist(pc.nodes[1].p) < 1e-6);
    }

    #[test]
    fn bowtie_is_rejected() {
        let mut pc = draft("skirt", &Measurements::default(), &DraftOpts::default()).unwrap().pieces[0].clone();
        pc.nodes.swap(1, 3);
        assert!(build_mesh(&pc, 3.0).is_err());
    }
}
