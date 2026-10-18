//! Parametric block drafting from body measurements.
//!
//! The constructions follow standard block-drafting practice (quarter-scale
//! bust/waist/hip, armhole depth from bust, neck-width from neck girth, sleeve
//! cap solved so cap length = armhole length + ease). The constants are
//! simplified approximations, NOT a verbatim reproduction of any published
//! system; calibrate them with a toile before production use.
use crate::geom::*;
use crate::model::*;

#[derive(Clone, Debug)]
pub struct DraftOpts {
    pub bust_ease: f64,
    pub waist_ease: f64,
    pub hip_ease: f64,
    pub cap_ease: f64,
    pub sleeve_ease: f64,
    pub sa: f64,
    pub hem_sa: f64,
}
impl Default for DraftOpts {
    fn default() -> Self {
        DraftOpts { bust_ease: 8.0, waist_ease: 6.0, hip_ease: 5.0, cap_ease: 3.5, sleeve_ease: 6.0, sa: 1.0, hem_sa: 3.0 }
    }
}

fn sm(ps: &[Piece], a: &str, ai: usize, b: &str, bi: usize, rev: bool) -> Seam {
    let tag = |n: &str, i: usize| ps.iter().find(|p| p.name == n).map(|p| p.nodes[i].edge.clone()).unwrap_or_default();
    Seam { a_piece: a.into(), a_tag: tag(a, ai), b_piece: b.into(), b_tag: tag(b, bi), rev }
}

fn node(x: f64, y: f64, edge: &str) -> Node { Node::corner(x, y, edge) }
fn with_out(mut n: Node, dx: f64, dy: f64) -> Node { n.hout = v2(dx, dy); n }
fn with_in(mut n: Node, dx: f64, dy: f64) -> Node { n.hin = v2(dx, dy); n }

fn base_piece(name: &str, zone: &str, nodes: Vec<Node>, o: &DraftOpts) -> Piece {
    let mut p = Piece {
        name: name.into(), zone: zone.into(), nodes, grain: (v2(0., 0.), v2(0., -10.)),
        notches: vec![], darts: vec![], internal: vec![], drills: vec![], sa: o.sa, mirror: true, qty: 1,
        material: "SELF".into(),
    };
    // hem edges get a deeper allowance
    for n in p.nodes.iter_mut() {
        if n.edge == "hem" { n.sa = Some(o.hem_sa); }
        if n.edge == "cf" || n.edge == "cb" || n.edge == "crotch_fold" { n.sa = Some(0.0); }
    }
    set_default_grain(&mut p);
    p
}

pub fn set_default_grain(p: &mut Piece) {
    let (lo, hi) = p.bounds();
    let x = lo.x + (hi.x - lo.x) * 0.5;
    let h = hi.y - lo.y;
    p.grain = (v2(x, hi.y - h * 0.15), v2(x, lo.y + h * 0.15));
}

fn dart(x: f64, apex_y: f64, width: f64, base_y: f64) -> Dart {
    Dart { apex: v2(x, apex_y), a: v2(x - width / 2.0, base_y), b: v2(x + width / 2.0, base_y) }
}

fn finish_darts(p: &mut Piece) {
    for d in p.darts.clone() {
        p.internal.push(vec![d.a, d.apex, d.b]);
        p.drills.push(d.apex + v2(0.0, -0.0));
    }
}

fn dart_layout(total: f64, x_end: f64, base_y: f64, apex_y: f64) -> Vec<Dart> {
    if total < 0.3 { return vec![]; }
    if total > 3.6 {
        vec![dart(x_end * 0.38, apex_y, total / 2.0, base_y), dart(x_end * 0.74, apex_y + 1.5, total / 2.0, base_y)]
    } else {
        vec![dart(x_end * 0.55, apex_y, total, base_y)]
    }
}

pub fn armhole_depth(m: &Measurements) -> f64 { m.bust / 8.0 + 8.0 }

pub fn effective_back_length(m: &Measurements) -> f64 { m.back_length.max(armhole_depth(m) + 8.0) }

pub fn draft_bodice(m: &Measurements, o: &DraftOpts) -> (Vec<Piece>, Vec<Seam>) {
    let bq = (m.bust + o.bust_ease) / 4.0;
    let wq = (m.waist + o.waist_ease) / 4.0;
    let ad = m.bust / 8.0 + 8.0; // armhole depth below CB neck level
    let nw = m.neck / 6.0 + 0.3;
    let sl = (m.shoulder_width / 2.0 - nw).max(6.0);
    let bl = m.back_length.max(ad + 8.0);
    let (a_b, a_f) = (20f64.to_radians(), 23f64.to_radians());

    // ---- back ----
    let snp_y = 2.0;
    let sp_b = v2(nw + sl * a_b.cos(), snp_y - sl * a_b.sin());
    let xs_b = bq + 0.5;
    let u_b = v2(xs_b, -ad);
    let d_b = sp_b.y - u_b.y;
    let e_b = (xs_b - wq).max(0.0);
    let xh_b = xs_b - 0.5 * e_b;
    let back_nodes = vec![
        with_out(node(0.0, 0.0, "neck"), nw * 0.55, 0.0),
        with_in(node(nw, snp_y, "shoulder"), -nw * 0.3, -0.6),
        with_out(node(sp_b.x, sp_b.y, "armhole"), -0.8, -d_b * 0.4),
        with_in(node(u_b.x, u_b.y, "side"), -(u_b.x - sp_b.x) * 0.7, 0.0),
        node(xh_b, -bl, "hem"),
        node(0.0, -bl, "cb"),
    ];
    let mut back = base_piece("Back Bodice", "upper", back_nodes, o);
    back.darts = dart_layout(0.5 * e_b, xh_b, -bl, -bl + 14.0);
    back.notches = vec![
        Notch { node: 3, t: 0.5, kind: "slit".into() },
        Notch { node: 2, t: 0.35, kind: "slit".into() },
        Notch { node: 2, t: 0.45, kind: "slit".into() },
    ];
    finish_darts(&mut back);

    // ---- front ----
    let sp_f = v2(nw + sl * a_f.cos(), snp_y - sl * a_f.sin());
    let xs_f = bq - 0.5;
    let u_f = v2(xs_f, -ad);
    let d_f = sp_f.y - u_f.y;
    let nd = nw + 1.5;
    let e_f = (xs_f - wq).max(0.0);
    let xh_f = xs_f - 0.5 * e_f;
    let front_nodes = vec![
        with_out(node(0.0, snp_y - nd, "neck"), nw * 0.6, 0.0),
        with_in(node(nw, snp_y, "shoulder"), -nw * 0.1, -nd * 0.6),
        with_out(node(sp_f.x, sp_f.y, "armhole"), -1.2, -d_f * 0.35),
        with_in(node(u_f.x, u_f.y, "side"), -(u_f.x - sp_f.x) * 0.75, 0.8),
        node(xh_f, -bl, "hem"),
        node(0.0, -bl, "cf"),
    ];
    let mut front = base_piece("Front Bodice", "upper", front_nodes, o);
    let bpx = (m.bust / 10.0).min(xh_f * 0.8);
    front.darts = if 0.5 * e_f > 0.3 { vec![dart(bpx, -(ad + 4.5), 0.5 * e_f, -bl)] } else { vec![] };
    front.notches = vec![
        Notch { node: 3, t: 0.5, kind: "slit".into() },
        Notch { node: 2, t: 0.4, kind: "slit".into() },
    ];
    finish_darts(&mut front);

    // ---- sleeve ----
    let arm_len = back.edge_len(2) + front.edge_len(2);
    let target = arm_len + o.cap_ease;
    let bw = m.bicep + o.sleeve_ease;
    let mk_cap = |ch: f64| -> (Node, Node, Node) {
        (
            with_out(node(0.0, 0.0, "cap_a"), bw * 0.04, ch * 0.45),
            {
                let mut t = node(bw / 2.0, ch, "cap_b");
                t.hin = v2(-bw * 0.18, 0.0);
                t.hout = v2(bw * 0.18, 0.0);
                t
            },
            with_in(node(bw, 0.0, "under_r"), -bw * 0.04, ch * 0.45),
        )
    };
    let cap_len = |ch: f64| -> f64 {
        let (a, b, c) = mk_cap(ch);
        let pa = flatten_cubic([a.p, a.p + a.hout, b.p + b.hin, b.p], 40);
        let pb = flatten_cubic([b.p, b.p + b.hout, c.p + c.hin, c.p], 40);
        poly_len(&pa) + poly_len(&pb)
    };
    let (mut lo, mut hi) = (1.0f64, 30.0f64);
    for _ in 0..60 {
        let mid = 0.5 * (lo + hi);
        if cap_len(mid) < target { lo = mid } else { hi = mid }
    }
    let ch = 0.5 * (lo + hi);
    let (n0, n1, n2) = mk_cap(ch);
    let hw = (m.wrist + 5.0).max(16.0);
    let ul = (m.sleeve_length - ch).max(10.0);
    let sleeve_nodes = vec![
        n0, n1, n2,
        node(bw / 2.0 + hw / 2.0, -ul, "hem"),
        node(bw / 2.0 - hw / 2.0, -ul, "under_l"),
    ];
    let mut sleeve = base_piece("Sleeve", "sleeve", sleeve_nodes, o);
    sleeve.notches = vec![
        Notch { node: 0, t: 1.0, kind: "slit".into() }, // top of cap
        Notch { node: 0, t: 0.55, kind: "slit".into() },
        Notch { node: 1, t: 0.4, kind: "slit".into() },
        Notch { node: 1, t: 0.5, kind: "slit".into() },
    ];
    // grain through the cap centre line
    sleeve.grain = (v2(bw / 2.0, ch * 0.8), v2(bw / 2.0, -ul * 0.8));

    let pieces_tmp = vec![front.clone(), back.clone(), sleeve.clone()];
    let seams = vec![
        sm(&pieces_tmp, "Front Bodice", 1, "Back Bodice", 1, false),
        sm(&pieces_tmp, "Front Bodice", 3, "Back Bodice", 3, false),
        sm(&pieces_tmp, "Front Bodice", 5, "Front Bodice", 5, false),
        sm(&pieces_tmp, "Back Bodice", 5, "Back Bodice", 5, false),
        sm(&pieces_tmp, "Front Bodice", 2, "Sleeve", 0, true),
        sm(&pieces_tmp, "Back Bodice", 2, "Sleeve", 1, false),
        sm(&pieces_tmp, "Sleeve", 2, "Sleeve", 4, true),
    ];
    (vec![front, back, sleeve], seams)
}

fn lower_waist_darts(piece: &mut Piece, total: f64, x_w: f64, apex_y: f64) {
    piece.darts = dart_layout(total, x_w, 0.0, apex_y);
    finish_darts(piece);
}

pub fn draft_skirt(m: &Measurements, o: &DraftOpts) -> (Vec<Piece>, Vec<Seam>) {
    let hq = (m.hip + o.hip_ease) / 4.0;
    let wq = (m.waist + 2.0) / 4.0;
    let hd = m.waist_to_hip;
    let l = m.skirt_length.max(hd + 5.0);
    let e = (hq - wq).max(0.0);
    let side_take = 0.4 * e;
    let dart_total = e - side_take;
    let x_w = hq - side_take;
    let mk = |name: &str, fold: &str, waist_drop: f64, apex: f64| -> Piece {
        let nodes = vec![
            node(0.0, 0.0, "waist"),
            with_out(node(x_w, 0.0, "side_a"), (hq - x_w) * 0.1, -hd * 0.4),
            with_in(node(hq, -hd, "side_b"), 0.0, hd * 0.45),
            node(hq, -l, "hem"),
            node(0.0, -l, fold),
        ];
        let mut p = base_piece(name, "lower", nodes, o);
        p.nodes[0].p.y += waist_drop;
        lower_waist_darts(&mut p, dart_total, x_w, apex);
        p.notches = vec![Notch { node: 1, t: 1.0, kind: "slit".into() }];
        p
    };
    let front = mk("Front Skirt", "cf", 0.0, -9.0);
    let back = mk("Back Skirt", "cb", 0.0, -12.0);
    let pieces_tmp = vec![front.clone(), back.clone()];
    let seams = vec![
        sm(&pieces_tmp, "Front Skirt", 1, "Back Skirt", 1, false),
        sm(&pieces_tmp, "Front Skirt", 2, "Back Skirt", 2, false),
        sm(&pieces_tmp, "Front Skirt", 4, "Front Skirt", 4, false),
        sm(&pieces_tmp, "Back Skirt", 4, "Back Skirt", 4, false),
    ];
    (vec![front, back], seams)
}

pub fn draft_trousers(m: &Measurements, o: &DraftOpts) -> (Vec<Piece>, Vec<Seam>) {
    let hq = (m.hip + o.hip_ease + 1.0) / 4.0;
    let wq = (m.waist + 2.0) / 4.0;
    let hd = m.waist_to_hip;
    let r = m.rise + 1.0;
    let e = (hq - wq).max(0.0);
    let side_take = 0.4 * e;
    let dart_total = e - side_take;
    let x_w = hq - side_take;
    let y_h = -(r + m.inseam);
    let y_k = -(r + m.inseam * 0.5 - 4.0);
    let knee_w = (m.knee + 6.0) / 2.0;
    let hem_w = (m.ankle + 17.0) / 2.0;
    let mk = |name: &str, ce: f64, dw: f64, cb_slant: f64, apex: f64| -> Piece {
        let xc = (hq - ce) / 2.0;
        let kw = knee_w + dw;
        let hw = hem_w + dw;
        let top = cb_slant;
        let mut n0 = node(cb_slant, top, "waist");
        n0.hin = v2(0.0, -0.45 * (r + top));
        let nodes = vec![
            n0,
            with_out(node(x_w, 0.0, "side_a"), (hq - x_w) * 0.1, -hd * 0.4),
            with_in(node(hq, -hd, "side_b"), 0.0, hd * 0.45),
            node(xc + kw / 2.0, y_k, "side_c"),
            node(xc + hw / 2.0, y_h, "hem"),
            node(xc - hw / 2.0, y_h, "inseam_c"),
            node(xc - kw / 2.0, y_k, "inseam_b"),
            with_out(node(-ce, -r, "crotch"), ce * 0.6, 0.0),
        ];
        let mut p = base_piece(name, "trouser", nodes, o);
        p.nodes[7].sa = Some(0.0);
        lower_waist_darts(&mut p, dart_total, x_w, apex);
        p.notches = vec![
            Notch { node: 1, t: 1.0, kind: "slit".into() },
            Notch { node: 2, t: 1.0, kind: "slit".into() },
            Notch { node: 6, t: 0.0, kind: "slit".into() },
        ];
        set_default_grain(&mut p);
        // grain along crease line
        let (lo, hi) = p.bounds();
        p.grain = (v2(xc, hi.y - 3.0), v2(xc, lo.y + 3.0));
        p
    };
    let front = mk("Front Trouser", 0.18 * hq, -0.5, 0.0, -9.0);
    let back = mk("Back Trouser", 0.26 * hq, 0.5, 1.8, -13.0);
    let pieces_tmp = vec![front.clone(), back.clone()];
    let mut seams = Vec::new();
    for e in [1usize, 2, 3, 5, 6] {
        seams.push(sm(&pieces_tmp, "Front Trouser", e, "Back Trouser", e, false));
    }
    seams.push(sm(&pieces_tmp, "Front Trouser", 7, "Front Trouser", 7, false));
    seams.push(sm(&pieces_tmp, "Back Trouser", 7, "Back Trouser", 7, false));
    (vec![front, back], seams)
}

pub fn draft(garment: &str, m: &Measurements, o: &DraftOpts) -> Result<Pattern, String> {
    validate(m)?;
    let (pieces, seams) = match garment {
        "bodice" => draft_bodice(m, o),
        "skirt" => draft_skirt(m, o),
        "trousers" => draft_trousers(m, o),
        g => return Err(format!("unknown garment '{}' (bodice | skirt | trousers)", g)),
    };
    Ok(Pattern { style: format!("{}-block", garment), size: "BASE".into(), garment: garment.into(), pieces, seams })
}

pub fn validate(m: &Measurements) -> Result<(), String> {
    if m.waist > m.hip + 30.0 || m.hip < 50.0 || m.bust < 50.0 || m.waist < 40.0 {
        return Err("measurements outside the supported range (bust/hip ≥ 50 cm, waist ≥ 40 cm)".into());
    }
    if m.back_length < 25.0 || m.back_length > 60.0 {
        return Err("back_length should be 25–60 cm".into());
    }
    if m.shoulder_width < 25.0 || m.shoulder_width > 60.0 {
        return Err("shoulder_width should be 25–60 cm".into());
    }
    Ok(())
}

#[derive(Clone, Debug)]
pub struct Check {
    pub name: String,
    pub value: f64,
    pub expected: f64,
    pub tol: f64,
}
impl Check {
    pub fn ok(&self) -> bool { (self.value - self.expected).abs() <= self.tol }
}

/// Fit/consistency checks used by the UI and tests.
pub fn checks(p: &Pattern, m: &Measurements, o: &DraftOpts) -> Vec<Check> {
    let mut c = Vec::new();
    let mut seam_check = |name: &str, a: &str, ae: usize, b: &str, be: usize, tol: f64| {
        if let (Some(pa), Some(pb)) = (p.piece(a), p.piece(b)) {
            c.push(Check { name: name.into(), value: pa.edge_len(ae), expected: pb.edge_len(be), tol });
        }
    };
    seam_check("Shoulder seam length (front vs back)", "Front Bodice", 1, "Back Bodice", 1, 0.3);
    seam_check("Side seam length (front vs back)", "Front Bodice", 3, "Back Bodice", 3, 1.5);
    seam_check("Skirt side seam (front vs back)", "Front Skirt", 1, "Back Skirt", 1, 0.5);
    seam_check("Trouser inseam (front vs back)", "Front Trouser", 5, "Back Trouser", 5, 0.5);
    if let (Some(f), Some(b), Some(s)) = (p.piece("Front Bodice"), p.piece("Back Bodice"), p.piece("Sleeve")) {
        let arm = f.edge_len(2) + b.edge_len(2);
        let cap = s.edge_len(0) + s.edge_len(1);
        c.push(Check { name: "Sleeve cap length = armhole + ease".into(), value: cap, expected: arm + o.cap_ease, tol: 0.2 });
        let wf: f64 = f.darts.iter().map(|d| d.a.dist(d.b)).sum();
        let wb: f64 = b.darts.iter().map(|d| d.a.dist(d.b)).sum();
        let hem_f = f.nodes[4].p.x - wf;
        let hem_b = b.nodes[4].p.x - wb;
        c.push(Check { name: "Bodice finished waist".into(), value: 4.0 * (hem_f + hem_b) / 2.0, expected: m.waist + o.waist_ease, tol: 0.5 });
    }
    for name in ["Front Skirt", "Front Trouser"] {
        if let Some(f) = p.piece(name) {
            let back = p.piece(&name.replace("Front", "Back")).unwrap();
            let dw = |q: &Piece| q.darts.iter().map(|d| d.a.dist(d.b)).sum::<f64>();
            let w_f = f.nodes[1].p.x - f.nodes[0].p.x - dw(f);
            let w_b = back.nodes[1].p.x - back.nodes[0].p.x - dw(back);
            c.push(Check { name: format!("{} finished waist", name.replace("Front ", "")), value: 2.0 * (w_f + w_b), expected: m.waist + 2.0, tol: 2.5 });
        }
    }
    c
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bodice_checks_pass_for_default() {
        let m = Measurements::default();
        let o = DraftOpts::default();
        let p = draft("bodice", &m, &o).unwrap();
        for c in checks(&p, &m, &o) {
            assert!(c.ok(), "check failed: {} value {} expected {}", c.name, c.value, c.expected);
        }
    }

    #[test]
    fn sleeve_cap_solves_to_target() {
        let m = Measurements::default();
        let o = DraftOpts::default();
        let p = draft("bodice", &m, &o).unwrap();
        let cap = p.piece("Sleeve").unwrap();
        let arm = p.piece("Front Bodice").unwrap().edge_len(2) + p.piece("Back Bodice").unwrap().edge_len(2);
        let got = cap.edge_len(0) + cap.edge_len(1);
        assert!((got - arm - o.cap_ease).abs() < 0.1, "{} vs {}", got, arm);
        assert!(cap.bounds().1.y > 5.0 && cap.bounds().1.y < 25.0);
    }

    #[test]
    fn all_garments_have_simple_positive_area_outlines() {
        let m = Measurements::default();
        for g in ["bodice", "skirt", "trousers"] {
            let p = draft(g, &m, &DraftOpts::default()).unwrap();
            for piece in &p.pieces {
                assert!(piece.area() > 100.0, "{} {}", g, piece.name);
                let (pts, _) = piece.flatten(16);
                assert!(!crate::mesh::self_intersects(&pts), "{} self-intersects", piece.name);
            }
        }
    }

    #[test]
    fn rejects_bad_measurements() {
        let mut m = Measurements::default();
        m.bust = 20.0;
        assert!(draft("bodice", &m, &DraftOpts::default()).is_err());
        assert!(draft("cape", &Measurements::default(), &DraftOpts::default()).is_err());
    }
}
