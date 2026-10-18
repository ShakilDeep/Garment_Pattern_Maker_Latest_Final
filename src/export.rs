//! Exporters: cut-line geometry, SVG preview, AAMA/ASTM-style DXF (polyline or SPLINE curves,
//! graded nests, ASTM-style metadata). Layers, methods and the Optitex import checklist are in
//! docs/EXPORT.md.
//!
//! IMPORTANT: native Optitex `.pds` is a proprietary, undocumented format. This
//! crate deliberately does NOT emit guessed `.pds` bytes (they would be a
//! corrupt file). `export_pds` returns an explanatory error until real sample
//! files are available to derive/verify a writer. Use `dxf_aama` for Optitex
//! import (File > Import > DXF AAMA/ASTM).
use crate::geom::*;
use crate::model::*;
use std::fmt::Write;

/// Default chord tolerance (cm) for flattening curves in exports.
pub const DEFAULT_CHORD_TOL: f64 = 0.02;

/// How curved edges of the sew line are written to DXF.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CurveMode {
    /// Pure R12 polylines; curves flattened adaptively to `chord_tol` (maximum deviation).
    Polyline,
    /// Curved sew edges become true cubic-Bezier SPLINE entities (DXF R13+, header AC1014);
    /// straight runs stay POLYLINEs. The cut line is always an adaptively flattened polyline.
    Spline,
}

#[derive(Clone, Debug)]
pub struct ExportOpts {
    /// Maximum distance (cm) between the true curve and the exported polyline.
    pub chord_tol: f64,
    pub curves: CurveMode,
}
impl Default for ExportOpts {
    fn default() -> Self { ExportOpts { chord_tol: DEFAULT_CHORD_TOL, curves: CurveMode::Spline } }
}
impl ExportOpts {
    /// Pure-polyline R12 fallback (what `dxf_aama` uses).
    pub fn polyline() -> Self { ExportOpts { chord_tol: DEFAULT_CHORD_TOL, curves: CurveMode::Polyline } }
}

fn fin(v: V2) -> V2 { if v.x.is_finite() && v.y.is_finite() { v } else { V2::default() } }

/// Cubic control points of edge `i` if it is curved (has non-zero handles), else None.
pub fn edge_bezier(p: &Piece, i: usize) -> Option<[V2; 4]> {
    let n = p.nodes.len();
    if n == 0 { return None; }
    let (a, b) = (&p.nodes[i % n], &p.nodes[(i + 1) % n]);
    let (ho, hi) = (fin(a.hout), fin(b.hin));
    if ho == V2::default() && hi == V2::default() { return None; }
    Some([fin(a.p), fin(a.p) + ho, fin(b.p) + hi, fin(b.p)])
}

/// Outline flattened so no point of a true curve is farther than `tol` from the polyline.
/// Same contract as `Piece::flatten`: (points, edge index of each segment start).
pub fn flatten_adaptive(p: &Piece, tol: f64) -> (Vec<V2>, Vec<usize>) {
    let n = p.nodes.len();
    let (mut pts, mut seg) = (Vec::new(), Vec::new());
    for i in 0..n {
        match edge_bezier(p, i) {
            None => { pts.push(fin(p.nodes[i].p)); seg.push(i); }
            Some(c) => {
                let f = flatten_cubic_adaptive(c, tol);
                for q in &f[..f.len() - 1] { pts.push(*q); seg.push(i); }
            }
        }
    }
    (pts, seg)
}

/// (sew line, cut line) polygons for a piece, in pattern units (cm).
pub fn cut_outline(p: &Piece) -> (Vec<V2>, Vec<V2>) {
    let (sew, seg) = p.flatten(16);
    let d: Vec<f64> = seg.iter().map(|&e| p.nodes[e].sa.unwrap_or(p.sa)).collect();
    let cut = offset_polygon(&sew, &d);
    (sew, cut)
}

/// Like `cut_outline` but flattened to a chord tolerance `tol` (cm) instead of 16 steps/curve.
pub fn cut_outline_tol(p: &Piece, tol: f64) -> (Vec<V2>, Vec<V2>) {
    let (sew, seg) = flatten_adaptive(p, tol);
    let d: Vec<f64> = seg.iter().map(|&e| p.nodes[e].sa.unwrap_or(p.sa)).collect();
    let cut = offset_polygon_opts(&sew, &d, DEFAULT_MITER_LIMIT, DEFAULT_TRANSITION_MITER_LIMIT, (tol * 0.25).max(0.001));
    (sew, cut)
}

fn edge_point(p: &Piece, edge: usize, t: f64) -> (V2, V2) {
    let poly = p.edge_polyline(edge, 32);
    let (pt, tan) = point_at(&poly, t * poly_len(&poly));
    (pt, tan)
}

/// Outward unit normal for a tangent along the outline direction.
fn outward(sew: &[V2], tan: V2) -> V2 {
    if signed_area(sew) > 0.0 { v2(tan.y, -tan.x) } else { v2(-tan.y, tan.x) }
}

pub fn to_svg(pat: &Pattern, show_cut: bool) -> String {
    let gap = 6.0;
    let mut x = 2.0;
    let mut body = String::new();
    let mut maxh: f64 = 0.0;
    for pc in &pat.pieces {
        let (sew, cut) = cut_outline(pc);
        let lo_src = if show_cut { &cut } else { &sew };
        let (mut lo, mut hi) = (lo_src[0], lo_src[0]);
        for q in lo_src { lo = v2(lo.x.min(q.x), lo.y.min(q.y)); hi = v2(hi.x.max(q.x), hi.y.max(q.y)); }
        let map = |q: V2| v2(q.x - lo.x + x, hi.y - q.y + 2.0);
        let path = |pts: &[V2]| -> String {
            let mut s = String::from("M");
            for (i, q) in pts.iter().enumerate() {
                let m = map(*q);
                let _ = write!(s, "{}{:.2},{:.2}", if i == 0 { "" } else { " L" }, m.x, m.y);
            }
            s.push('Z');
            s
        };
        let _ = write!(body, "<g data-piece=\"{}\">", esc(&pc.name));
        if show_cut {
            let _ = write!(body, "<path d=\"{}\" fill=\"none\" stroke=\"#c0392b\" stroke-width=\"0.15\" stroke-dasharray=\"1,0.6\"/>", path(&cut));
        }
        let _ = write!(body, "<path d=\"{}\" fill=\"#f4efe6\" stroke=\"#222\" stroke-width=\"0.2\"/>", path(&sew));
        for l in &pc.internal {
            let mut s = String::from("M");
            for (i, q) in l.iter().enumerate() { let m = map(*q); let _ = write!(s, "{}{:.2},{:.2}", if i == 0 { "" } else { " L" }, m.x, m.y); }
            let _ = write!(body, "<path d=\"{}\" fill=\"none\" stroke=\"#2a6fdb\" stroke-width=\"0.15\"/>", s);
        }
        let (g0, g1) = (map(pc.grain.0), map(pc.grain.1));
        let _ = write!(body, "<line x1=\"{:.2}\" y1=\"{:.2}\" x2=\"{:.2}\" y2=\"{:.2}\" stroke=\"#555\" stroke-width=\"0.2\"/>", g0.x, g0.y, g1.x, g1.y);
        for nt in &pc.notches {
            if nt.node < pc.nodes.len() {
                let (pt, tan) = edge_point(pc, nt.node, nt.t);
                let inward = outward(&sew, tan) * -1.0;
                let (a, b) = (map(pt), map(pt + inward * 0.8));
                let _ = write!(body, "<line x1=\"{:.2}\" y1=\"{:.2}\" x2=\"{:.2}\" y2=\"{:.2}\" stroke=\"#222\" stroke-width=\"0.25\"/>", a.x, a.y, b.x, b.y);
            }
        }
        let c = map(v2((lo.x + hi.x) / 2.0, (lo.y + hi.y) / 2.0));
        let _ = write!(body, "<text x=\"{:.2}\" y=\"{:.2}\" font-size=\"2\" text-anchor=\"middle\" fill=\"#333\">{}</text></g>", c.x, c.y, esc(&pc.name));
        x += hi.x - lo.x + gap;
        maxh = maxh.max(hi.y - lo.y);
    }
    format!("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 {:.1} {:.1}\" width=\"{:.0}mm\" height=\"{:.0}mm\">{}</svg>", x, maxh + 4.0, x * 10.0, (maxh + 4.0) * 10.0, body)
}

fn esc(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

struct Dxf {
    s: String,
}
impl Dxf {
    fn g(&mut self, code: i32, v: impl std::fmt::Display) {
        let _ = write!(self.s, "{:>3}\r\n{}\r\n", code, v);
    }
    fn gf(&mut self, code: i32, v: f64) {
        let _ = write!(self.s, "{:>3}\r\n{:.2}\r\n", code, if v.is_finite() { v } else { 0.0 });
    }
    fn polyline(&mut self, layer: &str, pts: &[V2], closed: bool) {
        if pts.is_empty() { return; }
        self.g(0, "POLYLINE");
        self.g(8, layer);
        self.g(66, 1);
        self.g(70, if closed { 1 } else { 0 });
        for q in pts {
            self.g(0, "VERTEX");
            self.g(8, layer);
            self.gf(10, q.x);
            self.gf(20, q.y);
            self.gf(30, 0.0);
        }
        if closed {
            // repeat first vertex so importers that ignore the closed flag still see a closed loop
            self.g(0, "VERTEX");
            self.g(8, layer);
            self.gf(10, pts[0].x);
            self.gf(20, pts[0].y);
            self.gf(30, 0.0);
        }
        self.g(0, "SEQEND");
        self.g(8, layer);
    }
    /// Planar cubic Bezier as a clamped B-spline (degree 3, 4 control points, 8 knots).
    fn spline(&mut self, layer: &str, c: [V2; 4]) {
        self.g(0, "SPLINE");
        self.g(8, layer);
        self.g(210, "0.0");
        self.g(220, "0.0");
        self.g(230, "1.0");
        self.g(70, 8); // planar
        self.g(71, 3);
        self.g(72, 8);
        self.g(73, 4);
        self.g(74, 0);
        for k in [0, 0, 0, 0, 1, 1, 1, 1] { self.g(40, format!("{}.0", k)); }
        for q in c {
            self.gf(10, q.x);
            self.gf(20, q.y);
            self.gf(30, 0.0);
        }
    }
    fn text(&mut self, layer: &str, at: V2, h: f64, s: &str) {
        self.g(0, "TEXT");
        self.g(8, layer);
        self.gf(10, at.x);
        self.gf(20, at.y);
        self.gf(30, 0.0);
        self.gf(40, h);
        self.g(1, s);
    }
    fn line(&mut self, layer: &str, a: V2, b: V2) {
        self.g(0, "LINE");
        self.g(8, layer);
        self.gf(10, a.x);
        self.gf(20, a.y);
        self.gf(30, 0.0);
        self.gf(11, b.x);
        self.gf(21, b.y);
        self.gf(31, 0.0);
    }
    fn point(&mut self, layer: &str, at: V2, depth: f64, width: f64, angle_deg: f64) {
        self.g(0, "POINT");
        self.g(8, layer);
        self.gf(10, at.x);
        self.gf(20, at.y);
        self.gf(30, depth);
        self.gf(39, width);
        self.gf(50, angle_deg);
    }
    fn block_begin(&mut self, name: &str) {
        self.g(0, "BLOCK");
        self.g(8, "1");
        self.g(2, name);
        self.g(70, 64);
        self.gf(10, 0.0);
        self.gf(20, 0.0);
        self.gf(30, 0.0);
        self.g(3, name);
        self.g(1, "");
    }
    fn block_end(&mut self) {
        self.g(0, "ENDBLK");
        self.g(8, "1");
    }
    fn begin(&mut self, comments: &[String], opts: &ExportOpts) {
        for c in comments { self.g(999, c); }
        self.g(0, "SECTION");
        self.g(2, "HEADER");
        self.g(9, "$ACADVER");
        self.g(1, if opts.curves == CurveMode::Spline { "AC1014" } else { "AC1009" });
        if opts.curves == CurveMode::Spline {
            self.g(9, "$INSUNITS");
            self.g(70, 4); // millimetres
        }
        self.g(0, "ENDSEC");
        self.g(0, "SECTION");
        self.g(2, "BLOCKS");
    }
    fn finish(&mut self) {
        self.g(0, "ENDSEC");
        self.g(0, "SECTION");
        self.g(2, "ENTITIES");
        self.g(0, "ENDSEC");
        self.g(0, "EOF");
    }
}

/// Notch layer by type: t=80, castle=81, check=82, u=83; slit/v/other = generic layer 4.
fn notch_layer(kind: &str) -> &'static str {
    match kind { "t" => "80", "castle" => "81", "check" => "82", "u" => "83", _ => "4" }
}

fn block_name(s: &str) -> String {
    let t: String = s.chars().map(|c| if c.is_ascii_alphanumeric() { c } else { '_' }).collect();
    if t.is_empty() { "PIECE".into() } else { t }
}

fn is_fold(pc: &Piece) -> bool { pc.nodes.iter().any(|n| n.edge == "cf" || n.edge == "cb") }

fn bbox(p: &[V2]) -> (V2, V2) {
    let (mut a, mut b) = (p[0], p[0]);
    for q in p { a = v2(a.x.min(q.x), a.y.min(q.y)); b = v2(b.x.max(q.x), b.y.max(q.y)); }
    (a, b)
}

/// Write one piece BLOCK. Returns false (writing nothing) for degenerate pieces.
fn write_piece_block(d: &mut Dxf, pc: &Piece, size: &str, style: &str, opts: &ExportOpts, block: &str) -> bool {
    let mm = 10.0;
    if pc.nodes.len() < 3 { return false; }
    let (sew, cut) = cut_outline_tol(pc, opts.chord_tol);
    if sew.len() < 3 || cut.len() < 3 || sew.iter().chain(cut.iter()).any(|q| !q.x.is_finite() || !q.y.is_finite()) { return false; }
    let lo = bbox(&cut).0;
    let m = |q: V2| (fin(q) - lo) * mm;
    d.block_begin(block);
    let cut_m: Vec<V2> = cut.iter().map(|q| m(*q)).collect();
    d.polyline("1", &cut_m, true); // layer 1: cut boundary
    let (clo, chi) = bbox(&cut_m);
    let mid = v2((clo.x + chi.x) / 2.0, (clo.y + chi.y) / 2.0);
    let th = 6.0;
    let fold = is_fold(pc);
    let qty = if fold { pc.qty } else { pc.qty * if pc.mirror { 2 } else { 1 } };
    let gv = fin(pc.grain.1) - fin(pc.grain.0);
    let ang = if gv.len() < 1e-9 { 90.0 } else { gv.y.atan2(gv.x).to_degrees() };
    let lines = [
        format!("Piece Name: {}", pc.name),
        format!("Size Name: {}", size),
        format!("Quantity: {}", qty),
        format!("Material: {}", pc.material),
        format!("Style Name: {}", style),
        format!("Mirror: {}", if pc.mirror { "YES" } else { "NO" }),
        format!("Fold: {}", if fold { "YES" } else { "NO" }),
        format!("Grain Line: {:.1} deg", ang),
        format!("Nesting: Rotate=180 Flip={}", if pc.mirror { "YES" } else { "NO" }),
    ];
    let first = [2.0, 0.5, -1.0, -2.5, -4.0];
    for (k, t) in lines.iter().enumerate() {
        let off = if k < first.len() { first[k] } else { -4.0 - 1.5 * (k - first.len() + 1) as f64 };
        d.text("1", mid + v2(0.0, th * off), th, t);
    }
    d.line("7", m(pc.grain.0), m(pc.grain.1)); // layer 7: grain line
    if fold {
        if let Some(i) = pc.nodes.iter().position(|n| n.edge == "cf" || n.edge == "cb") {
            let (a, b) = (pc.nodes[i].p, pc.nodes[(i + 1) % pc.nodes.len()].p);
            d.line("6", m(a), m(b));
        }
    }
    for nt in &pc.notches {
        if nt.node >= pc.nodes.len() { continue; }
        let (pt, tan) = edge_point(pc, nt.node, nt.t);
        let out = outward(&sew, tan);
        let sa = pc.nodes[nt.node].sa.unwrap_or(pc.sa);
        let on_cut = pt + out * sa;
        let inw = out * -1.0;
        d.point(notch_layer(&nt.kind), m(on_cut), (sa * mm).min(5.0), 1.0, inw.y.atan2(inw.x).to_degrees());
    }
    for l in &pc.internal {
        let pts: Vec<V2> = l.iter().filter(|q| q.x.is_finite() && q.y.is_finite()).map(|q| m(*q)).collect();
        if pts.len() >= 2 { d.polyline("8", &pts, false); } // layer 8: internal lines
    }
    for dt in &pc.darts {
        let pts = [m(dt.a), m(dt.apex), m(dt.b)];
        if pts.iter().all(|q| q.x.is_finite() && q.y.is_finite()) { d.polyline("8", &pts, false); }
    }
    for q in &pc.drills {
        if q.x.is_finite() && q.y.is_finite() { d.point("13", m(*q), 0.0, 3.0, 0.0); } // layer 13: drill
    }
    // layer 14: sew line
    match opts.curves {
        CurveMode::Polyline => {
            let sew_m: Vec<V2> = sew.iter().map(|q| m(*q)).collect();
            d.polyline("14", &sew_m, true);
        }
        CurveMode::Spline => {
            let n = pc.nodes.len();
            let mut run: Vec<V2> = Vec::new();
            for i in 0..n {
                match edge_bezier(pc, i) {
                    None => {
                        if run.is_empty() { run.push(m(pc.nodes[i].p)); }
                        run.push(m(pc.nodes[(i + 1) % n].p));
                    }
                    Some(c) => {
                        if run.len() >= 2 { d.polyline("14", &run, false); }
                        run.clear();
                        d.spline("14", [m(c[0]), m(c[1]), m(c[2]), m(c[3])]);
                    }
                }
            }
            if run.len() >= 2 { d.polyline("14", &run, false); }
        }
    }
    d.block_end();
    true
}

const NOT_VERIFIED: &str = "PatternForge AAMA/ASTM-style DXF export (metric, mm). Not verified against Optitex; see docs/EXPORT.md.";

/// Write an AAMA/ASTM D6673-style DXF (R12-compatible polylines), metric (mm).
/// One BLOCK per piece per size; graded sizes repeat the pieces in order.
/// Curves are flattened to `DEFAULT_CHORD_TOL`; use [`dxf_aama_opts`] for SPLINE output.
pub fn dxf_aama(sizes: &[(String, &Pattern)], style: &str) -> String {
    dxf_aama_opts(sizes, style, &ExportOpts::polyline())
}

/// `dxf_aama` with explicit curve mode / chord tolerance.
pub fn dxf_aama_opts(sizes: &[(String, &Pattern)], style: &str, opts: &ExportOpts) -> String {
    let mut d = Dxf { s: String::new() };
    d.begin(&[NOT_VERIFIED.to_string()], opts);
    for (size, pat) in sizes {
        for pc in &pat.pieces {
            write_piece_block(&mut d, pc, size, style, opts, &block_name(&pc.name));
        }
    }
    d.finish();
    d.s
}

/// Graded DXF (polyline curves). See [`dxf_graded_opts`].
pub fn dxf_graded(sizes: &[(String, &Pattern)], base: &str, style: &str) -> String {
    dxf_graded_opts(sizes, base, style, &ExportOpts::polyline())
}

/// Graded export = per-size piece blocks + one nested-sizes block per piece.
///
/// 1. Base-size piece blocks come FIRST and are byte-identical to `dxf_aama_opts` for that
///    size (names unchanged).
/// 2. Every other size follows with the same block content, block names `<piece>_<size>`
///    (unique names; `Size Name:` text carries the real size).
/// 3. For each base piece a block `<piece>_NEST` overlays all sizes' cut and sew outlines
///    on layers `CUT_<size>` / `SEW_<size>`, aligned at the grain-line start point, so grade
///    growth can be checked visually. Sizes missing a piece are skipped for that piece.
/// This is the nested/per-size method, NOT ASTM D6673 point grade rules (see docs/EXPORT.md).
pub fn dxf_graded_opts(sizes: &[(String, &Pattern)], base: &str, style: &str, opts: &ExportOpts) -> String {
    let mut d = Dxf { s: String::new() };
    let mut notes = vec![NOT_VERIFIED.to_string()];
    let bi = sizes.iter().position(|(s, _)| s == base)
        .or_else(|| sizes.iter().position(|(s, _)| s.eq_ignore_ascii_case(base)))
        .unwrap_or(0);
    if let Some((bs, _)) = sizes.get(bi) {
        if bs != base { notes.push(format!("Base size '{}' not found; using '{}'.", base, bs)); }
        let all: Vec<&str> = sizes.iter().map(|(s, _)| s.as_str()).collect();
        notes.push(format!("Graded nest: base={} sizes={}", bs, all.join(",")));
    }
    d.begin(&notes, opts);
    if let Some((bsize, bpat)) = sizes.get(bi) {
        for pc in &bpat.pieces {
            write_piece_block(&mut d, pc, bsize, style, opts, &block_name(&pc.name));
        }
        for (k, (size, pat)) in sizes.iter().enumerate() {
            if k == bi { continue; }
            for pc in &pat.pieces {
                let name = format!("{}_{}", block_name(&pc.name), block_name(size));
                write_piece_block(&mut d, pc, size, style, opts, &name);
            }
        }
        let mm = 10.0;
        for bpc in &bpat.pieces {
            if bpc.nodes.len() < 3 { continue; }
            let (_, bcut) = cut_outline_tol(bpc, opts.chord_tol);
            if bcut.len() < 3 || bcut.iter().any(|q| !q.x.is_finite() || !q.y.is_finite()) { continue; }
            let blo = bbox(&bcut).0;
            d.block_begin(&format!("{}_NEST", block_name(&bpc.name)));
            for (size, pat) in sizes {
                let Some(pc) = pat.piece(&bpc.name) else { continue };
                if pc.nodes.len() < 3 { continue; }
                let (sew, cut) = cut_outline_tol(pc, opts.chord_tol);
                if sew.len() < 3 || cut.len() < 3 { continue; }
                let sh = fin(bpc.grain.0) - fin(pc.grain.0) - blo; // align grain-line starts
                let tag = block_name(size).to_uppercase();
                let mp = |p: &[V2]| -> Vec<V2> { p.iter().map(|q| (fin(*q) + sh) * mm).collect() };
                d.polyline(&format!("CUT_{}", tag), &mp(&cut), true);
                d.polyline(&format!("SEW_{}", tag), &mp(&sew), true);
            }
            d.block_end();
        }
    }
    d.finish();
    d.s
}

/// Native Optitex PDS is proprietary and undocumented; no writer is provided.
pub fn export_pds(_pat: &Pattern) -> Result<Vec<u8>, String> {
    Err("Native .pds export is not implemented: the Optitex PDS format is proprietary and undocumented, and a guessed \
         writer would produce files Optitex cannot open. Use 'Export for Optitex (DXF-AAMA)' and import it in Optitex \
         (File > Import > DXF AAMA/ASTM). To enable real PDS support, provide sample .pds files (see docs/PDS-SAMPLES.md)."
        .into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::draft::{draft, DraftOpts};

    /// Minimal DXF group reader for verification.
    fn groups(s: &str) -> Vec<(i32, String)> {
        let l: Vec<&str> = s.lines().collect();
        l.chunks(2).filter(|c| c.len() == 2).map(|c| (c[0].trim().parse().unwrap(), c[1].to_string())).collect()
    }

    #[test]
    fn cut_line_is_larger_by_seam_allowance() {
        let p = draft("skirt", &Measurements::default(), &DraftOpts::default()).unwrap();
        for pc in &p.pieces {
            let (sew, cut) = cut_outline(pc);
            let (a_s, a_c) = (signed_area(&sew).abs(), signed_area(&cut).abs());
            assert!(a_c > a_s * 1.05, "{} {} {}", pc.name, a_s, a_c);
        }
    }

    #[test]
    fn dxf_is_structurally_valid() {
        let p = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        let dxf = dxf_aama(&[("M".into(), &p)], "T");
        let g = groups(&dxf);
        assert_eq!(g.last().unwrap(), &(0, "EOF".to_string()));
        let count = |code: i32, v: &str| g.iter().filter(|(c, s)| *c == code && s == v).count();
        assert_eq!(count(0, "BLOCK"), 3);
        assert_eq!(count(0, "ENDBLK"), 3);
        assert_eq!(count(0, "POLYLINE"), count(0, "SEQEND"));
        assert!(count(0, "SECTION") == count(0, "ENDSEC"));
        assert!(g.iter().any(|(c, s)| *c == 1 && s == "Piece Name: Back Bodice"));
        // layer 1 boundary area (mm²) matches the cut-line area
        let mut verts: Vec<V2> = Vec::new();
        let mut in_l1 = false;
        let mut cur = (0.0, 0.0);
        let mut found = false;
        for (i, (c, s)) in g.iter().enumerate() {
            if *c == 0 && s == "POLYLINE" { in_l1 = g[i + 1].1 == "1"; verts.clear(); }
            if in_l1 && *c == 0 && s == "VERTEX" { cur = (g[i + 2].1.parse().unwrap(), g[i + 3].1.parse().unwrap()); verts.push(v2(cur.0, cur.1)); }
            if in_l1 && *c == 0 && s == "SEQEND" && !found {
                verts.pop(); // repeated closing vertex
                let area = signed_area(&verts).abs() / 100.0;
                let want = signed_area(&cut_outline(&p.pieces[0]).1).abs();
                assert!((area - want).abs() / want < 0.01, "{} vs {}", area, want);
                found = true;
            }
            if *c == 0 && s == "SEQEND" { in_l1 = false; }
        }
        assert!(found);
        let _ = cur;
    }

    #[test]
    fn graded_dxf_repeats_pieces_per_size() {
        let a = draft("trousers", &Measurements::default(), &DraftOpts::default()).unwrap();
        let dxf = dxf_aama(&[("S".into(), &a), ("M".into(), &a), ("L".into(), &a)], "T");
        assert_eq!(dxf.matches("BLOCK\r\n").count(), 6);
        assert_eq!(dxf.matches("ENDBLK\r\n").count(), 6);
        assert_eq!(dxf.matches("Size Name: L").count(), 2);
    }

    #[test]
    fn pds_is_refused_honestly() {
        let p = draft("skirt", &Measurements::default(), &DraftOpts::default()).unwrap();
        let e = export_pds(&p).unwrap_err();
        assert!(e.contains("proprietary"));
    }

    #[test]
    fn svg_contains_every_piece() {
        let p = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        let s = to_svg(&p, true);
        for pc in &p.pieces { assert!(s.contains(&pc.name)); }
        assert!(!s.contains("NaN"));
    }

    // ---------- helpers for the new tests ----------
    /// (entity type, layer) for the entity types we emit (VERTEX/SEQEND excluded).
    fn ents(g: &[(i32, String)]) -> Vec<(String, String)> {
        let mut v = Vec::new();
        for (i, (c, s)) in g.iter().enumerate() {
            if *c == 0 && ["POLYLINE", "LINE", "POINT", "TEXT", "SPLINE"].contains(&s.as_str()) {
                let layer = g[i + 1..].iter().find(|(c, _)| *c == 8).map(|(_, l)| l.clone()).unwrap_or_default();
                v.push((s.clone(), layer));
            }
        }
        v
    }
    fn count_ent(g: &[(i32, String)], ty: &str, layer: &str) -> usize {
        ents(g).iter().filter(|(t, l)| t == ty && l == layer).count()
    }
    /// Total length (cm) of everything on layer 14: polyline chains + exact Bezier splines.
    fn layer14_len_cm(g: &[(i32, String)]) -> f64 {
        let (mut total, mut i) = (0.0, 0);
        while i < g.len() {
            if g[i].0 == 0 && (g[i].1 == "POLYLINE" || g[i].1 == "SPLINE") && g[i + 1].1 == "14" {
                let is_spline = g[i].1 == "SPLINE";
                let mut j = i + 1;
                let mut pts: Vec<V2> = Vec::new();
                let (mut x, mut have_x) = (0.0, false);
                while j < g.len() && !(g[j].0 == 0 && (g[j].1 == "SEQEND" || (is_spline && j > i))) || (j < g.len() && g[j].0 == 0 && g[j].1 == "VERTEX") {
                    if g[j].0 == 10 { x = g[j].1.parse().unwrap(); have_x = true; }
                    if g[j].0 == 20 && have_x { pts.push(v2(x, g[j].1.parse().unwrap())); have_x = false; }
                    j += 1;
                }
                total += if is_spline && pts.len() == 4 {
                    poly_len(&flatten_cubic([pts[0], pts[1], pts[2], pts[3]], 4000))
                } else { poly_len(&pts) };
                i = j;
            } else { i += 1; }
        }
        total / 10.0
    }
    fn model_sew_len(p: &Pattern) -> f64 {
        p.pieces.iter().map(|pc| (0..pc.nodes.len()).map(|i| poly_len(&pc.edge_polyline(i, 4000))).sum::<f64>()).sum()
    }
    fn count_curved(p: &Pattern) -> usize {
        p.pieces.iter().map(|pc| (0..pc.nodes.len()).filter(|&i| edge_bezier(pc, i).is_some()).count()).sum()
    }

    #[test]
    fn spline_export_matches_model_curve_length() {
        let p = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        assert!(count_curved(&p) > 0);
        let model = model_sew_len(&p);
        // SPLINE mode: exact Bezier control points -> length equal within DXF rounding
        let ds = dxf_aama_opts(&[("M".into(), &p)], "T", &ExportOpts::default());
        let g = groups(&ds);
        assert_eq!(g.iter().filter(|(c, s)| *c == 0 && s == "SPLINE").count(), count_curved(&p));
        assert!(ds.contains("AC1014"));
        let ls = layer14_len_cm(&g);
        assert!((ls - model).abs() < 0.02, "spline {} vs model {}", ls, model);
        // POLYLINE mode: chord tolerance bounds the shortfall (polyline is inscribed)
        let dp = dxf_aama(&[("M".into(), &p)], "T");
        assert!(!dp.contains("SPLINE") && dp.contains("AC1009"));
        let lp = layer14_len_cm(&groups(&dp));
        assert!(lp <= model + 0.02 && (model - lp) / model < 0.001, "polyline {} vs model {}", lp, model);
    }

    #[test]
    fn chord_tolerance_is_controllable() {
        let p = draft("bodice", &Measurements::default(), &DraftOpts::default()).unwrap();
        let verts = |tol: f64| {
            let o = ExportOpts { chord_tol: tol, curves: CurveMode::Polyline };
            dxf_aama_opts(&[("M".into(), &p)], "T", &o).matches("VERTEX\r\n").count()
        };
        assert!(verts(0.5) < verts(0.02) && verts(0.02) < verts(0.002));
        // garbage tolerances never panic
        for t in [0.0, -1.0, f64::NAN, f64::INFINITY] {
            let o = ExportOpts { chord_tol: t, curves: CurveMode::Spline };
            assert!(dxf_aama_opts(&[("M".into(), &p)], "T", &o).ends_with("EOF\r\n"));
        }
    }

    fn meta_piece() -> Pattern {
        let mut nodes = vec![Node::corner(0., 0., "a"), Node::corner(20., 0., "b"), Node::corner(20., 20., "c"), Node::corner(0., 20., "d")];
        nodes[1].hout = v2(3., 5.);
        nodes[2].hin = v2(3., -5.);
        let nt = |kind: &str| Notch { node: 0, t: 0.5, kind: kind.into() };
        let pc = Piece {
            name: "Test Pc".into(), zone: "upper".into(), nodes,
            grain: (v2(10., 3.), v2(10., 17.)),
            notches: vec![nt("t"), nt("castle"), nt("check"), nt("u"), nt("slit")],
            darts: vec![Dart { apex: v2(10., 10.), a: v2(8., 2.), b: v2(12., 2.) }],
            internal: vec![vec![v2(2., 2.), v2(8., 8.)], vec![v2(3., 3.), v2(4., 9.), v2(5., 9.)]],
            drills: vec![v2(5., 5.), v2(6., 6.), v2(7., 7.)],
            sa: 1.0, mirror: true, qty: 1, material: "SHELL".into(),
        };
        Pattern { style: "S".into(), size: "M".into(), garment: "t".into(), pieces: vec![pc], seams: vec![] }
    }

    #[test]
    fn metadata_layers_and_counts() {
        let p = meta_piece();
        for opts in [ExportOpts::default(), ExportOpts::polyline()] {
            let dxf = dxf_aama_opts(&[("M".into(), &p)], "Sty", &opts);
            let g = groups(&dxf);
            let c = |t: &str, l: &str| count_ent(&g, t, l);
            assert_eq!(c("POLYLINE", "1"), 1, "cut boundary");
            assert_eq!(c("LINE", "7"), 1, "grain");
            assert_eq!(c("POLYLINE", "8"), 3, "2 internal + 1 dart");
            assert_eq!(c("POINT", "13"), 3, "drills");
            for l in ["80", "81", "82", "83", "4"] { assert_eq!(c("POINT", l), 1, "notch layer {}", l); }
            assert_eq!(c("TEXT", "1"), 9);
            if opts.curves == CurveMode::Spline {
                assert_eq!(c("SPLINE", "14"), 1);
                assert_eq!(c("POLYLINE", "14"), 2);
            } else {
                assert_eq!(c("POLYLINE", "14"), 1);
            }
            for t in ["Piece Name: Test Pc", "Size Name: M", "Quantity: 2", "Material: SHELL", "Style Name: Sty",
                      "Mirror: YES", "Fold: NO", "Grain Line: 90.0 deg", "Nesting: Rotate=180 Flip=YES"] {
                assert!(g.iter().any(|(c, s)| *c == 1 && s == t), "missing {}", t);
            }
            // grain line is 14 cm = 140 mm long and vertical
            let i = g.iter().position(|(c, s)| *c == 0 && s == "LINE").unwrap();
            let f = |code: i32| -> f64 { g[i..i + 14].iter().find(|(c, _)| *c == code).unwrap().1.parse().unwrap() };
            assert!((f(21) - f(20) - 140.0).abs() < 0.02 && (f(11) - f(10)).abs() < 0.02);
        }
    }

    #[test]
    fn degenerate_pieces_never_panic() {
        let mut p = meta_piece();
        p.pieces[0].nodes.truncate(2);
        let mut q = meta_piece();
        q.pieces[0].nodes[1].hout = v2(f64::NAN, f64::INFINITY);
        q.pieces[0].grain = (v2(1., 1.), v2(1., 1.));
        q.pieces[0].notches.push(Notch { node: 99, t: 0.5, kind: "t".into() });
        for pat in [&p, &q] {
            for o in [ExportOpts::default(), ExportOpts::polyline()] {
                assert!(dxf_aama_opts(&[("M".into(), pat)], "T", &o).ends_with("EOF\r\n"));
                assert!(dxf_graded_opts(&[("M".into(), pat), ("L".into(), pat)], "M", "T", &o).ends_with("EOF\r\n"));
            }
        }
        assert!(dxf_graded(&[], "M", "T").ends_with("EOF\r\n"));
        let a = draft("skirt", &Measurements::default(), &DraftOpts::default()).unwrap();
        let d = dxf_graded(&[("S".into(), &a)], "XL", "T");
        assert!(d.contains("not found") && d.contains("Size Name: S"));
    }

    #[test]
    fn graded_dxf_has_every_size_and_base_matches_dxf_aama() {
        use crate::grade::{default_rules, grade};
        let g = grade("bodice", &Measurements::default(), &DraftOpts::default(), &default_rules(), &[-1, 0, 1]).unwrap();
        let sizes: Vec<(String, &Pattern)> = g.iter().map(|s| (s.label.clone(), &s.pattern)).collect();
        let dxf = dxf_graded(&sizes, "M", "T");
        let np = g[1].pattern.pieces.len();
        for (lab, _) in &sizes {
            assert_eq!(dxf.matches(&format!("Size Name: {}\r\n", lab)).count(), np, "size {}", lab);
            let tag = lab.to_uppercase();
            assert_eq!(count_ent(&groups(&dxf), "POLYLINE", &format!("CUT_{}", tag)), np);
            assert_eq!(count_ent(&groups(&dxf), "POLYLINE", &format!("SEW_{}", tag)), np);
        }
        assert!(dxf.contains("Back_Bodice_S") && dxf.contains("Back_Bodice_L") && dxf.contains("Back_Bodice_NEST"));
        // base-size blocks are byte-identical to dxf_aama for that size and come first
        let plain = dxf_aama(&[("M".into(), &g[1].pattern)], "T");
        let a = plain.find("  0\r\nBLOCK\r\n").unwrap();
        let b = plain.rfind("ENDBLK\r\n  8\r\n1\r\n").unwrap() + "ENDBLK\r\n  8\r\n1\r\n".len();
        let base_blocks = &plain[a..b];
        let at = dxf.find(base_blocks).expect("base blocks not found verbatim");
        assert!(!dxf[..at].contains("Size Name: S") && !dxf[..at].contains("Size Name: L"));
        // nest block: the L outline is bigger than the S outline
        let gg = groups(&dxf);
        let ext = |layer: &str| -> f64 {
            let i = (0..gg.len()).find(|&i| gg[i].0 == 0 && gg[i].1 == "POLYLINE" && gg[i + 1].1 == layer).unwrap();
            let (mut lo, mut hi) = (f64::MAX, f64::MIN);
            let mut j = i;
            while !(gg[j].0 == 0 && gg[j].1 == "SEQEND") {
                if gg[j].0 == 10 { let x: f64 = gg[j].1.parse().unwrap(); lo = lo.min(x); hi = hi.max(x); }
                j += 1;
            }
            hi - lo
        };
        assert!(ext("CUT_L") > ext("CUT_S"));
    }

    #[test]
    fn cut_line_corner_handling_before_after() {
        use crate::garments::{draft_shirt, GarmentOpts, ShirtSpec};
        let clen = |p: &[V2]| -> f64 { (0..p.len()).map(|i| p[i].dist(p[(i + 1) % p.len()])).sum() };
        // 1. exact law on a rectangle: cut = sew + 8*sa
        let pc = {
            let mut p = meta_piece().pieces.remove(0);
            p.nodes = vec![Node::corner(0., 0., "a"), Node::corner(30., 0., "b"), Node::corner(30., 12., "c"), Node::corner(0., 12., "d")];
            p
        };
        let (sew, cut) = cut_outline(&pc);
        assert!((clen(&cut) - (clen(&sew) + 8.0 * pc.sa)).abs() < 1e-9);
        // 2. shirt sleeve vs XML (Sleeve L: PERIMETER 129.8, SEW_PERIMETER 118.1)
        let shirt = draft_shirt(&ShirtSpec::default(), &GarmentOpts::default()).unwrap();
        let sl = shirt.piece("Sleeve").unwrap();
        let (sew, seg) = sl.flatten(16);
        let d: Vec<f64> = seg.iter().map(|&e| sl.nodes[e].sa.unwrap_or(sl.sa)).collect();
        let (old, new) = (clen(&offset_polygon_legacy(&sew, &d)), clen(&offset_polygon_smart(&sew, &d)));
        println!("SLEEVE L cut perimeter: before {:.2} ({:+.2}%)  after {:.2} ({:+.2}%)  XML 129.8", old, 100.0 * (old - 129.8) / 129.8, new, 100.0 * (new - 129.8) / 129.8);
        // the drafter is calibrated to the classic miter offset (`old`); the arc-join variant must stay within 3%
        assert!((new - 129.8).abs() / 129.8 < 0.03 && (old - 129.8).abs() / 129.8 < 0.03);
        // 3. pant FRONT decoded from the sample PDS: cut-sew delta vs the file's own cut polygon
        let Ok(bytes) = std::fs::read("/home/claude/samples/pant_1074664.PDS") else { return };
        let doc = crate::pds_bin::decode(&bytes).unwrap();
        let g = doc.pieces.iter().find(|g| g.name == "FRONT" && g.size == doc.base_size).unwrap();
        let mut sewp: Vec<V2> = g.sew.iter().map(|&(x, y)| v2(x, y)).collect();
        if signed_area(&sewp) < 0.0 { sewp.reverse(); }
        let cutp: Vec<V2> = g.cut.iter().map(|&(x, y)| v2(x, y)).collect();
        let dist = |q: V2| -> f64 {
            (0..cutp.len()).map(|i| {
                let (a, b) = (cutp[i], cutp[(i + 1) % cutp.len()]);
                let ab = b - a; let l2 = ab.dot(ab);
                let t = if l2 < 1e-12 { 0.0 } else { ((q - a).dot(ab) / l2).clamp(0.0, 1.0) };
                (q - (a + ab * t)).len()
            }).fold(f64::MAX, f64::min)
        };
        let n = sewp.len();
        let per_edge: Vec<f64> = (0..n).map(|i| dist(sewp[i].lerp(sewp[(i + 1) % n], 0.5))).collect();
        let file_delta = clen(&cutp) - clen(&sewp);
        let ld = clen(&offset_polygon_legacy(&sewp, &per_edge)) - clen(&sewp);
        let nd = clen(&offset_polygon_smart(&sewp, &per_edge)) - clen(&sewp);
        println!("PANT FRONT S (per-edge SA from file): file delta {:.4}  before {:.4}  after {:.4}", file_delta, ld, nd);
        assert!((nd - file_delta).abs() <= (ld - file_delta).abs() + 1e-9);
    }
}
