//! Pattern editing operations (stateless: pattern in, pattern out).
use crate::geom::*;
use crate::model::*;

fn piece_mut<'a>(p: &'a mut Pattern, name: &str) -> Result<&'a mut Piece, String> {
    p.pieces.iter_mut().find(|x| x.name == name).ok_or_else(|| format!("no piece '{}'", name))
}
fn check_idx(pc: &Piece, i: usize) -> Result<(), String> {
    if i >= pc.nodes.len() { Err(format!("node index {} out of range", i)) } else { Ok(()) }
}
fn finite(v: f64) -> Result<f64, String> {
    if v.is_finite() { Ok(v) } else { Err("non-finite coordinate".into()) }
}

pub fn move_node(p: &mut Pattern, piece: &str, i: usize, x: f64, y: f64) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    pc.nodes[i].p = v2(finite(x)?, finite(y)?);
    Ok(())
}

/// Move a Bézier handle to an absolute position. `out` selects the outgoing handle.
pub fn move_handle(p: &mut Pattern, piece: &str, i: usize, out: bool, x: f64, y: f64) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    let rel = v2(finite(x)?, finite(y)?) - pc.nodes[i].p;
    if out { pc.nodes[i].hout = rel } else { pc.nodes[i].hin = rel }
    Ok(())
}

pub fn set_corner(p: &mut Pattern, piece: &str, i: usize) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    pc.nodes[i].hin = V2::default();
    pc.nodes[i].hout = V2::default();
    Ok(())
}

/// Turn a node into a smooth point (collinear handles) if it has none.
pub fn set_smooth(p: &mut Pattern, piece: &str, i: usize) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    let n = pc.nodes.len();
    let prev = pc.nodes[(i + n - 1) % n].p;
    let next = pc.nodes[(i + 1) % n].p;
    let cur = pc.nodes[i].p;
    let dir = (next - prev).norm();
    pc.nodes[i].hout = dir * (cur.dist(next) / 3.0);
    pc.nodes[i].hin = dir * (-(cur.dist(prev) / 3.0));
    Ok(())
}

/// Split edge `i` at parameter t (0..1); the new node inherits the edge tag.
pub fn split_edge(p: &mut Pattern, piece: &str, i: usize, t: f64) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    let t = t.clamp(0.02, 0.98);
    let n = pc.nodes.len();
    let (a, b) = (pc.nodes[i].clone(), pc.nodes[(i + 1) % n].clone());
    let straight = a.hout == V2::default() && b.hin == V2::default();
    let mut new = Node { edge: a.edge.clone(), sa: a.sa, ..Default::default() };
    if straight {
        new.p = a.p.lerp(b.p, t);
    } else {
        let (l, r) = cubic_split([a.p, a.p + a.hout, b.p + b.hin, b.p], t);
        new.p = l[3];
        new.hin = l[2] - l[3];
        new.hout = r[1] - r[0];
        pc.nodes[i].hout = l[1] - l[0];
        let j = (i + 1) % n;
        pc.nodes[j].hin = r[2] - r[3];
    }
    pc.nodes.insert(i + 1, new);
    // re-index notches
    for nt in pc.notches.iter_mut() {
        if nt.node == i {
            if nt.t <= t { nt.t /= t; } else { nt.node = i + 1; nt.t = (nt.t - t) / (1.0 - t); }
        } else if nt.node > i {
            nt.node += 1;
        }
    }
    Ok(())
}

pub fn delete_node(p: &mut Pattern, piece: &str, i: usize) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, i)?;
    if pc.nodes.len() <= 3 {
        return Err("a piece needs at least 3 nodes".into());
    }
    let n = pc.nodes.len();
    let prev = (i + n - 1) % n;
    // the previous node's edge now spans to the next node; keep its tag
    pc.nodes[prev].hout = V2::default();
    let nxt = (i + 1) % n;
    pc.nodes[nxt].hin = V2::default();
    pc.nodes.remove(i);
    pc.notches.retain(|nt| nt.node != i && nt.node != prev);
    for nt in pc.notches.iter_mut() {
        if nt.node > i { nt.node -= 1; }
    }
    Ok(())
}

pub fn set_seam_allowance(p: &mut Pattern, piece: &str, edge: Option<usize>, sa: f64) -> Result<(), String> {
    let sa = finite(sa)?;
    if !(0.0..=10.0).contains(&sa) { return Err("seam allowance must be 0–10 cm".into()); }
    let pc = piece_mut(p, piece)?;
    match edge {
        Some(e) => { check_idx(pc, e)?; pc.nodes[e].sa = Some(sa); }
        None => { pc.sa = sa; for n in pc.nodes.iter_mut() { n.sa = None; } }
    }
    Ok(())
}

/// Change a dart's intake (cm), keeping its centre and apex.
pub fn set_dart_width(p: &mut Pattern, piece: &str, di: usize, width: f64) -> Result<(), String> {
    let width = finite(width)?;
    if !(0.0..=15.0).contains(&width) { return Err("dart width must be 0–15 cm".into()); }
    let pc = piece_mut(p, piece)?;
    let d = pc.darts.get_mut(di).ok_or("no such dart")?;
    let c = d.a.lerp(d.b, 0.5);
    let dir = (d.b - d.a).norm();
    d.a = c + dir * (-width / 2.0);
    d.b = c + dir * (width / 2.0);
    let (a, apex, b) = (d.a, d.apex, d.b);
    // update the matching internal polyline (identified by the apex)
    for l in pc.internal.iter_mut() {
        if l.len() == 3 && l[1].dist(apex) < 1e-9 { l[0] = a; l[2] = b; }
    }
    Ok(())
}

pub fn add_notch(p: &mut Pattern, piece: &str, edge: usize, t: f64, kind: &str) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    check_idx(pc, edge)?;
    pc.notches.push(Notch { node: edge, t: t.clamp(0.0, 1.0), kind: kind.into() });
    Ok(())
}

pub fn remove_notch(p: &mut Pattern, piece: &str, index: usize) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    if index >= pc.notches.len() { return Err("no such notch".into()); }
    pc.notches.remove(index);
    Ok(())
}

pub fn translate_piece(p: &mut Pattern, piece: &str, dx: f64, dy: f64) -> Result<(), String> {
    let pc = piece_mut(p, piece)?;
    let d = v2(finite(dx)?, finite(dy)?);
    for n in pc.nodes.iter_mut() { n.p = n.p + d; }
    pc.grain = (pc.grain.0 + d, pc.grain.1 + d);
    for dt in pc.darts.iter_mut() { dt.apex = dt.apex + d; dt.a = dt.a + d; dt.b = dt.b + d; }
    for l in pc.internal.iter_mut() { for q in l.iter_mut() { *q = *q + d; } }
    for q in pc.drills.iter_mut() { *q = *q + d; }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::draft::{draft, DraftOpts};

    fn pat() -> Pattern { draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap() }

    #[test]
    fn split_keeps_shape_and_tag() {
        let mut p = pat();
        let before = p.piece("Back Bodice").unwrap().area();
        let len_before = p.piece("Back Bodice").unwrap().tag_len("armhole");
        split_edge(&mut p, "Back Bodice", 2, 0.4).unwrap();
        let pc = p.piece("Back Bodice").unwrap();
        assert_eq!(pc.nodes.len(), 7);
        assert_eq!(pc.nodes[3].edge, "armhole");
        assert!((pc.area() - before).abs() / before < 0.002);
        assert!((pc.tag_len("armhole") - len_before).abs() < 0.05);
    }

    #[test]
    fn split_reindexes_notches() {
        let mut p = pat();
        let n0 = p.piece("Back Bodice").unwrap().notches.len();
        split_edge(&mut p, "Back Bodice", 0, 0.5).unwrap();
        let pc = p.piece("Back Bodice").unwrap();
        assert_eq!(pc.notches.len(), n0);
        assert!(pc.notches.iter().all(|n| n.node < pc.nodes.len()));
    }

    #[test]
    fn delete_guards_minimum() {
        let mut p = pat();
        for _ in 0..3 { delete_node(&mut p, "Back Bodice", 0).unwrap(); }
        assert!(delete_node(&mut p, "Back Bodice", 0).is_err());
    }

    #[test]
    fn dart_width_changes_intake() {
        let mut p = pat();
        set_dart_width(&mut p, "Back Bodice", 0, 4.0).unwrap();
        let d = &p.piece("Back Bodice").unwrap().darts[0];
        assert!((d.a.dist(d.b) - 4.0).abs() < 1e-9);
        assert!(set_dart_width(&mut p, "Back Bodice", 9, 4.0).is_err());
        assert!(set_dart_width(&mut p, "Back Bodice", 0, f64::NAN).is_err());
    }

    #[test]
    fn bad_inputs_error_not_panic() {
        let mut p = pat();
        assert!(move_node(&mut p, "Nope", 0, 1.0, 1.0).is_err());
        assert!(move_node(&mut p, "Back Bodice", 99, 1.0, 1.0).is_err());
        assert!(set_seam_allowance(&mut p, "Back Bodice", None, 99.0).is_err());
    }
}
