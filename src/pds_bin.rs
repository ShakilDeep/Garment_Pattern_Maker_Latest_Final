//! Optitex PDS (v21.4.1103.0) binary container reader.
//!
//! STATUS (see `docs/PDS-FORMAT.md` for the evidence and for what is *not* proven):
//!
//! * The file is `[binary header][<?xml ...</STYLE> block][binary tail]`.  The XML part is
//!   parsed with a tiny tolerant scanner (it is the ground truth for validation).
//! * The tail is a typed tag stream.  Coordinates are `f32` values XOR-obfuscated with a
//!   per-file 32-bit key (the header dword at offset 12).  Piece contours are stored for the
//!   BASE size only; the other sizes are reconstructed from per-vertex grading steps.
//! * Geometry is only returned when it re-derives the XML `GEOM_INFO` numbers (bbox, area,
//!   perimeter) of that piece/size within documented tolerances.  Anything else yields empty
//!   polygons plus a warning, never a guess.
//!
//! The reader never panics on arbitrary input: every access is bounds-checked and all
//! arithmetic on file-provided numbers is checked or saturating.  No PDS *writer* exists on
//! purpose (it could not be round-trip verified inside Optitex).

use std::collections::HashMap;

/// A single closed/open outline with per-vertex curve information (item #20).
///
/// Optitex stores **no** explicit control points for curved edges (the per-vertex `fc 17`
/// tangent blob is all-zero in the sample), only a per-vertex curve flag (bit `0x40`).  The
/// smooth boundary is therefore *reconstructed* from the vertices and flags, not read back
/// verbatim.  `control` is kept in the type for forward compatibility (a future Optitex version
/// that does store Bezier handles), but is `None` for every vertex produced by this reader.
#[derive(Debug, Clone, PartialEq)]
pub struct PdsContour {
    /// Outline vertices in order (cm, world layout coordinates).  Closed implicitly.
    pub verts: Vec<(f64, f64)>,
    /// `curve[i] == true` when vertex `i` carries the curve flag (`0x40`): the boundary passes
    /// smoothly through it rather than forming a corner.
    pub curve: Vec<bool>,
    /// Optional incoming/outgoing control points per vertex.  Always `None` for this format
    /// (see the struct docs); `tessellate` falls back to a circular-arc reconstruction.
    pub control: Vec<Option<((f64, f64), (f64, f64))>>,
}

impl PdsContour {
    /// Reconstruct a smooth polyline from the vertices + curve flags, subdividing every curved
    /// edge so that no chord is longer than `max_chord` cm.
    ///
    /// Reconstruction rule (item #20, HONEST: this is a *reconstruction*, not stored data):
    /// an edge `i -> i+1` is drawn as a **circular arc** when *both* its endpoints carry the
    /// curve flag (i.e. the edge lies in the interior of a curved run); the arc is the circle
    /// through `(i-1, i, i+1)`.  Edges touching a corner, and edges between non-curve vertices,
    /// stay straight.  If `control[i]` is ever populated the cubic Bezier it defines is used
    /// instead.  Using only the interior edges (not the corner-adjacent ones) is what keeps the
    /// reconstruction from over-shooting the true perimeter — see `pant_curve_tessellation`.
    pub fn tessellate(&self, max_chord: f64) -> Vec<(f64, f64)> {
        let n = self.verts.len();
        if n < 3 {
            return self.verts.clone();
        }
        let step = if max_chord.is_finite() && max_chord > 1e-4 { max_chord } else { 0.05 };
        let curve = |i: usize| self.curve.get(i).copied().unwrap_or(false);
        let mut out: Vec<(f64, f64)> = Vec::with_capacity(n * 2);
        for i in 0..n {
            let a = self.verts[i];
            let b = self.verts[(i + 1) % n];
            out.push(a);
            // Cubic Bezier if explicit controls exist (never, for now).
            if let Some(Some((c1, c2))) = self.control.get(i) {
                sample_bezier(a, *c1, *c2, b, step, &mut out);
                continue;
            }
            if !(curve(i) && curve((i + 1) % n)) {
                continue;
            }
            let prev = self.verts[(i + n - 1) % n];
            sample_arc(prev, a, b, step, &mut out);
        }
        out
    }
}

/// Append interior samples of the circular arc through (p0,a,b) on the edge a->b (exclusive of
/// the endpoints).  Falls back to no insertion (a straight chord) when the three points are
/// (near-)collinear or degenerate.
fn sample_arc(p0: (f64, f64), a: (f64, f64), b: (f64, f64), step: f64, out: &mut Vec<(f64, f64)>) {
    if let Some((cx, cy)) = circumcenter(p0, a, b) {
        let r = ((a.0 - cx).powi(2) + (a.1 - cy).powi(2)).sqrt();
        if !r.is_finite() || r < 1e-6 || r > 1e6 {
            return;
        }
        let a0 = (a.1 - cy).atan2(a.0 - cx);
        let a1 = (b.1 - cy).atan2(b.0 - cx);
        let mut da = a1 - a0;
        while da > std::f64::consts::PI {
            da -= 2.0 * std::f64::consts::PI;
        }
        while da < -std::f64::consts::PI {
            da += 2.0 * std::f64::consts::PI;
        }
        let arc = (da.abs() * r).min(1e5);
        let steps = ((arc / step).ceil() as usize).clamp(1, 4096);
        for s in 1..steps {
            let t = a0 + da * (s as f64) / (steps as f64);
            out.push((cx + r * t.cos(), cy + r * t.sin()));
        }
    }
}

fn sample_bezier(a: (f64, f64), c1: (f64, f64), c2: (f64, f64), b: (f64, f64), step: f64, out: &mut Vec<(f64, f64)>) {
    let rough = ((c1.0 - a.0).hypot(c1.1 - a.1) + (c2.0 - c1.0).hypot(c2.1 - c1.1) + (b.0 - c2.0).hypot(b.1 - c2.1)).min(1e5);
    let steps = ((rough / step).ceil() as usize).clamp(1, 4096);
    for s in 1..steps {
        let t = (s as f64) / (steps as f64);
        let u = 1.0 - t;
        let x = u * u * u * a.0 + 3.0 * u * u * t * c1.0 + 3.0 * u * t * t * c2.0 + t * t * t * b.0;
        let y = u * u * u * a.1 + 3.0 * u * u * t * c1.1 + 3.0 * u * t * t * c2.1 + t * t * t * b.1;
        out.push((x, y));
    }
}

/// Centre of the circle through three points, or `None` if they are (near-)collinear.
fn circumcenter(a: (f64, f64), b: (f64, f64), c: (f64, f64)) -> Option<(f64, f64)> {
    let d = 2.0 * (a.0 * (b.1 - c.1) + b.0 * (c.1 - a.1) + c.0 * (a.1 - b.1));
    if d.abs() < 1e-9 {
        return None;
    }
    let (a2, b2, c2) = (a.0 * a.0 + a.1 * a.1, b.0 * b.0 + b.1 * b.1, c.0 * c.0 + c.1 * c.1);
    let ux = (a2 * (b.1 - c.1) + b2 * (c.1 - a.1) + c2 * (a.1 - b.1)) / d;
    let uy = (a2 * (c.0 - b.0) + b2 * (a.0 - c.0) + c2 * (b.0 - a.0)) / d;
    if ux.is_finite() && uy.is_finite() {
        Some((ux, uy))
    } else {
        None
    }
}

/// Geometry of one piece in one size.  Units: centimetres, Optitex "world" layout coordinates
/// (y up, as stored in the file).  Polygons are closed implicitly (last vertex joins first).
#[derive(Debug, Clone, PartialEq)]
pub struct PdsPieceGeom {
    pub name: String,
    pub size: String,
    /// Cut outline **vertices** (curves are NOT tessellated here; use `cut_contour.tessellate`).
    pub cut: Vec<(f64, f64)>,
    /// Sew outline (same vertex semantics).
    pub sew: Vec<(f64, f64)>,
    /// Notch anchor points on the sew line.  Populated for every size: the base size is validated
    /// against the marker SVG; other sizes are graded from the base using the (validated) vertex
    /// grading of the notch's anchor vertex (item #21 — a reconstruction, see docs).
    pub notches: Vec<(f64, f64)>,
    pub quantity: u32,
    /// Cut outline with per-vertex curve flags, ready for `tessellate` (item #20).  `None` when
    /// the geometry was not validated.
    pub cut_contour: Option<PdsContour>,
    /// Grain-line endpoints `((x1,y1),(x2,y2))` (item #21).  Populated for the BASE size only
    /// (grain grading is not validated).  `None` when not found/validated.
    pub grain: Option<((f64, f64), (f64, f64))>,
    /// Piece placement / grain anchor point from the XML `<POSITION>` (== grain-line midpoint).
    pub position: Option<(f64, f64)>,
    /// Internal construction lines (polylines).  Empty for this sample — none are present; needs
    /// dedicated samples to decode/validate (see docs, overlaps #22/#23).
    pub internal_lines: Vec<Vec<(f64, f64)>>,
    /// Drill-hole positions.  Empty for this sample — none present; needs samples (see docs).
    pub drills: Vec<(f64, f64)>,
}

#[derive(Debug, Clone, Default)]
pub struct PdsBinDoc {
    pub style: String,
    pub version: String,
    pub sizes: Vec<String>,
    pub base_size: String,
    /// One entry per (piece, size), pieces in XML order, sizes in XML order.  Polygons are empty
    /// when the geometry could not be validated against the XML.
    pub pieces: Vec<PdsPieceGeom>,
    pub warnings: Vec<String>,
    /// True only if EVERY (piece,size) entry carries validated geometry.
    pub decoded_geometry: bool,
}

// ---------------------------------------------------------------------------------------------
// Inspection types (record framing etc.)
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContourRole {
    /// `03 04 N 24 63 c8 ...` header: sew outline (or the only outline).
    Sew,
    /// `4f 04 N 24 40 28 63 c8 ...` header: cut outline.
    Cut,
    /// `03 04 N 24 80 28 ...` header: auxiliary contours (meaning unknown, never used).
    Aux,
    Unknown,
}

#[derive(Debug, Clone)]
pub struct ContourInfo {
    /// Offset inside the tail of the `5e <float-array>` tag that holds the x,y pairs.
    pub tail_offset: usize,
    pub points: usize,
    pub role: ContourRole,
    pub has_flags: bool,
    pub grade_records: usize,
    pub notch_records: usize,
    /// Offset where sequential parsing of the per-vertex arrays/records stopped.
    pub parse_end: usize,
    pub complete: bool,
}

#[derive(Debug, Clone, Default)]
pub struct PdsInspect {
    pub magic_ok: bool,
    pub header_words: Vec<u32>,
    pub header_style: Option<String>,
    pub key: u32,
    pub key_source: String,
    pub xml_range: (usize, usize),
    pub xml_len_field_ok: bool,
    pub tail_offset: usize,
    pub tail_len: usize,
    pub tail_path: Option<String>,
    pub piece_anchors: Vec<(String, Option<usize>)>,
    pub contours: Vec<ContourInfo>,
    pub strings: Vec<(usize, String)>,
}

const DEFAULT_KEY: u32 = 0x6024_05c4;
const MAGIC: [u8; 4] = [0xdc, 0x54, 0xef, 0x12];

// ---------------------------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------------------------

fn u16_at(b: &[u8], p: usize) -> Option<u16> {
    let s = b.get(p..p.checked_add(2)?)?;
    Some(u16::from_le_bytes([s[0], s[1]]))
}

fn u32_at(b: &[u8], p: usize) -> Option<u32> {
    let s = b.get(p..p.checked_add(4)?)?;
    Some(u32::from_le_bytes([s[0], s[1], s[2], s[3]]))
}

fn find(hay: &[u8], needle: &[u8], from: usize) -> Option<usize> {
    if needle.is_empty() || from > hay.len() || hay.len() - from < needle.len() {
        return None;
    }
    let last = hay.len() - needle.len();
    (from..=last).find(|&i| &hay[i..i + needle.len()] == needle)
}

fn rfind(hay: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || hay.len() < needle.len() {
        return None;
    }
    (0..=hay.len() - needle.len()).rev().find(|&i| &hay[i..i + needle.len()] == needle)
}

fn decode_f32(b: &[u8], p: usize, key: u32) -> Option<f64> {
    let w = u32_at(b, p)? ^ key;
    Some(f32::from_bits(w) as f64)
}

// ---------------------------------------------------------------------------------------------
// Typed values of the tail stream
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum Val {
    /// XOR-keyed f32 array.
    F(Vec<f64>),
    /// u32 array.
    I(Vec<u32>),
    /// u16 array.
    H(Vec<u16>),
    /// u8 array (explicit u16 count).
    B(Vec<u8>),
    /// blob of 2*count bytes (explicit u32 count of 16-bit words).
    W(usize),
}

/// Read one `[id][type][payload]` value starting at `p` (the id byte).  Returns the value and the
/// offset after it.  Only the type codes that are evidenced in the sample are understood:
///
/// * `0x80..=0x9c` (step 4): f32 array, `(t-0x80)/4+1` elements;  `0xa0`: explicit u16 count.
/// * `0xc0..=0xdc` (low bits 0/1): u32 array, `(t&0xfc-0xc0)/4+1` elements; `0xe0`: explicit u16 count.
/// * `0x43..=0x5f` (low bits 11): u16 array, `(t-0x43)/4+1` elements; `0x63`: explicit u16 count.
/// * `0x18`: u8 array with u16 count.  `0x17`: blob, u32 count of 16-bit words.
fn read_typed(b: &[u8], p: usize, key: u32) -> Option<(Val, usize)> {
    let t = *b.get(p.checked_add(1)?)?;
    let q = p.checked_add(2)?;
    let float_t = (0x80..=0xa0).contains(&t) && t & 3 == 0;
    let int_t = (0xc0..=0xe0).contains(&(t & 0xfc)) && (t & 3) <= 1;
    let half_t = (0x43..=0x63).contains(&t) && t & 3 == 3;
    if float_t || int_t || half_t {
        let (n, q2) = if t == 0xa0 || t & 0xfc == 0xe0 && int_t || t == 0x63 && half_t {
            (u16_at(b, q)? as usize, q + 2)
        } else if float_t {
            ((((t - 0x80) >> 2) + 1) as usize, q)
        } else if int_t {
            (((((t & 0xfc) - 0xc0) >> 2) + 1) as usize, q)
        } else {
            ((((t - 0x43) >> 2) + 1) as usize, q)
        };
        let esz = if half_t { 2 } else { 4 };
        let end = q2.checked_add(n.checked_mul(esz)?)?;
        if end > b.len() {
            return None;
        }
        return Some(if float_t {
            let mut v = Vec::with_capacity(n);
            for i in 0..n {
                v.push(decode_f32(b, q2 + 4 * i, key)?);
            }
            (Val::F(v), end)
        } else if int_t {
            let mut v = Vec::with_capacity(n);
            for i in 0..n {
                v.push(u32_at(b, q2 + 4 * i)?);
            }
            (Val::I(v), end)
        } else {
            let mut v = Vec::with_capacity(n);
            for i in 0..n {
                v.push(u16_at(b, q2 + 2 * i)?);
            }
            (Val::H(v), end)
        });
    }
    if t == 0x18 {
        let n = u16_at(b, q)? as usize;
        let s = q + 2;
        let end = s.checked_add(n)?;
        return Some((Val::B(b.get(s..end)?.to_vec()), end));
    }
    if t == 0x17 {
        let n = u32_at(b, q)? as usize;
        let s = q + 4;
        let end = s.checked_add(n.checked_mul(2)?)?;
        if end > b.len() {
            return None;
        }
        return Some((Val::W(n * 2), end));
    }
    None
}

// ---------------------------------------------------------------------------------------------
// Contours
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
struct Contour {
    off: usize,
    role: ContourRole,
    pts: Vec<(f64, f64)>,
    flags: Option<Vec<u8>>,
    /// vertex index -> fields (id, type, value)
    recs: HashMap<usize, Vec<(u8, u8, Val)>>,
    notches: Vec<(usize, [f64; 4])>,
    end: usize,
    complete: bool,
}

fn classify(tail: &[u8], off: usize, n: usize) -> ContourRole {
    if n > 255 {
        return ContourRole::Unknown;
    }
    let lo = off.saturating_sub(48);
    let w = &tail[lo..off.min(tail.len())];
    let nb = n as u8;
    let pats: [(ContourRole, Vec<u8>); 3] = [
        (ContourRole::Cut, vec![0x4f, 0x04, nb, 0x24, 0x40, 0x28, 0x63, 0xc8]),
        (ContourRole::Sew, vec![0x03, 0x04, nb, 0x24, 0x63, 0xc8]),
        (ContourRole::Aux, vec![0x03, 0x04, nb, 0x24, 0x80, 0x28]),
    ];
    let mut best: Option<(usize, ContourRole)> = None;
    for (role, p) in pats.iter() {
        if let Some(i) = rfind(w, p) {
            if best.map_or(true, |(bi, _)| i > bi) {
                best = Some((i, *role));
            }
        }
    }
    best.map_or(ContourRole::Unknown, |(_, r)| r)
}

fn parse_contour(tail: &[u8], off: usize, key: u32) -> Option<Contour> {
    if *tail.get(off)? != 0x5e {
        return None;
    }
    let (v, mut p) = read_typed(tail, off, key)?;
    let xy = match v {
        Val::F(x) => x,
        _ => return None,
    };
    if xy.len() < 6 || xy.len() % 2 != 0 || xy.len() > 40_000 {
        return None;
    }
    if xy.iter().any(|v| !v.is_finite() || v.abs() > 1.0e5) {
        return None;
    }
    let pts: Vec<(f64, f64)> = xy.chunks(2).map(|c| (c[0], c[1])).collect();
    let role = classify(tail, off, pts.len());
    let mut c = Contour {
        off,
        role,
        pts,
        flags: None,
        recs: HashMap::new(),
        notches: Vec::new(),
        end: p,
        complete: true,
    };
    let n = c.pts.len();
    loop {
        if p + 2 > tail.len() {
            c.complete = false;
            break;
        }
        let id = tail[p];
        let ty = tail[p + 1];
        if ty == 0x10 {
            let mut q = p + 2;
            let k;
            if tail.get(q + 1) == Some(&0x24) {
                k = tail[q] as usize;
                q += 2;
            } else {
                k = 0;
            }
            match id {
                0x04 => {
                    let mut fields = Vec::new();
                    loop {
                        match (tail.get(q), tail.get(q + 1)) {
                            (Some(0), Some(0)) => break,
                            (Some(_), Some(_)) => {}
                            _ => {
                                c.complete = false;
                                c.end = p;
                                return Some(c);
                            }
                        }
                        match read_typed(tail, q, key) {
                            Some((val, nx)) if fields.len() < 16 => {
                                fields.push((tail[q], tail[q + 1], val));
                                q = nx;
                            }
                            _ => {
                                c.complete = false;
                                c.end = p;
                                return Some(c);
                            }
                        }
                    }
                    c.recs.insert(k, fields);
                    p = q + 2;
                }
                0x69 => {
                    // notch record: locate the `e4 94` six-float field inside the next 80 bytes.
                    let lim = (q + 80).min(tail.len());
                    let mut found = None;
                    let mut j = q;
                    while j + 1 < lim {
                        if tail[j] == 0xe4 && tail[j + 1] == 0x94 {
                            found = Some(j);
                            break;
                        }
                        j += 1;
                    }
                    let ok = found.and_then(|j| match read_typed(tail, j, key) {
                        Some((Val::F(f), nx)) if f.len() == 6 => {
                            if tail.get(nx) == Some(&0) && tail.get(nx + 1) == Some(&0) {
                                Some(([f[0], f[1], f[2], f[3]], nx + 2))
                            } else {
                                None
                            }
                        }
                        _ => None,
                    });
                    match ok {
                        Some((pq, nx)) => {
                            c.notches.push((k, pq));
                            p = nx;
                        }
                        None => {
                            c.complete = false;
                            c.end = p;
                            return Some(c);
                        }
                    }
                }
                _ => {
                    c.complete = false;
                    break;
                }
            }
            continue;
        }
        if id == 0x5e {
            break;
        }
        match read_typed(tail, p, key) {
            Some((val, nx)) => {
                if id == 0x5f {
                    if let Val::B(f) = &val {
                        if f.len() == n {
                            c.flags = Some(f.clone());
                        }
                    }
                }
                p = nx;
            }
            None => break,
        }
    }
    c.end = p;
    Some(c)
}

/// Candidate contour starts inside `tail[lo..hi]`.
fn find_contours(tail: &[u8], lo: usize, hi: usize, key: u32) -> Vec<Contour> {
    let mut out = Vec::new();
    let hi = hi.min(tail.len());
    let mut p = lo;
    while p + 4 < hi {
        if tail[p] == 0x5e {
            let t = tail[p + 1];
            if (0x80..=0xa0).contains(&t) && t & 3 == 0 {
                if let Some(c) = parse_contour(tail, p, key) {
                    if c.role != ContourRole::Unknown {
                        let e = c.off;
                        p = e.max(p) + 1;
                        out.push(c);
                        continue;
                    }
                }
            }
        }
        p += 1;
    }
    out
}

// ---------------------------------------------------------------------------------------------
// Grading
// ---------------------------------------------------------------------------------------------

/// Per-step (dx,dy) of vertex `k`, `nsteps` steps.  `None` if a record is malformed.
fn steps_for(c: &Contour, k: usize, nsteps: usize) -> Option<Vec<(f64, f64)>> {
    let mut st = vec![(0.0, 0.0); nsteps];
    if let Some(fields) = c.recs.get(&k) {
        for (id, _t, v) in fields {
            if let Val::F(f) = v {
                if *id == 0xad {
                    if f.len() != 2 * nsteps {
                        return None;
                    }
                    for i in 0..nsteps {
                        st[i] = (f[2 * i], f[2 * i + 1]);
                    }
                } else if *id == 0xaf {
                    if f.len() != 2 {
                        return None;
                    }
                    for s in st.iter_mut() {
                        *s = (f[0], f[1]);
                    }
                }
            }
        }
    }
    Some(st)
}

/// Reconstruct the contour for size index `j` from the base size index `b`.
///
/// Step `i` is the delta between size `i` and size `i+1`:  `p[i+1] = p[i] - step[i]`.
/// Vertices whose flag byte has bit 0x80 clear are not rule points: their step is interpolated
/// between the neighbouring rule points proportionally to base-size arc length.
fn grade(c: &Contour, j: usize, b: usize, nsizes: usize) -> Option<Vec<(f64, f64)>> {
    let n = c.pts.len();
    if j == b {
        return Some(c.pts.clone());
    }
    let nsteps = nsizes.checked_sub(1)?;
    let flags = c.flags.as_ref()?;
    if flags.len() != n || nsteps == 0 || nsteps > 8 {
        return None;
    }
    let rule: Vec<bool> = flags.iter().map(|f| f & 0x80 != 0).collect();
    if !rule.iter().any(|r| *r) {
        return None;
    }
    let mut steps = Vec::with_capacity(n);
    for k in 0..n {
        steps.push(steps_for(c, k, nsteps)?);
    }
    let seg: Vec<f64> = (0..n)
        .map(|k| {
            let a = c.pts[k];
            let q = c.pts[(k + 1) % n];
            ((q.0 - a.0).powi(2) + (q.1 - a.1).powi(2)).sqrt()
        })
        .collect();
    let (range, sign): (Vec<usize>, f64) = if j > b { ((b..j).collect(), -1.0) } else { ((j..b).collect(), 1.0) };
    let mut out = Vec::with_capacity(n);
    for k in 0..n {
        let (mut sx, mut sy) = (0.0, 0.0);
        for &i in &range {
            let d = if rule[k] {
                steps[k][i]
            } else {
                let mut pk = k;
                let mut pl = 0.0;
                loop {
                    pk = (pk + n - 1) % n;
                    pl += seg[pk];
                    if rule[pk] {
                        break;
                    }
                }
                let mut nk = k;
                let mut nl = 0.0;
                loop {
                    nl += seg[nk];
                    nk = (nk + 1) % n;
                    if rule[nk] {
                        break;
                    }
                }
                let w = if pl + nl > 0.0 { pl / (pl + nl) } else { 0.0 };
                let (dp, dn) = (steps[pk][i], steps[nk][i]);
                (dp.0 * (1.0 - w) + dn.0 * w, dp.1 * (1.0 - w) + dn.1 * w)
            };
            sx += sign * d.0;
            sy += sign * d.1;
        }
        out.push((c.pts[k].0 + sx, c.pts[k].1 + sy));
    }
    Some(out)
}

/// Mirror a stored half polygon across the line through its first and last vertex (the fold
/// edge) and return the closed full outline.
fn mirror_half(p: &[(f64, f64)]) -> Vec<(f64, f64)> {
    let n = p.len();
    if n < 3 {
        return p.to_vec();
    }
    let (a, bq) = (p[0], p[n - 1]);
    let (dx, dy) = (bq.0 - a.0, bq.1 - a.1);
    let l2 = dx * dx + dy * dy;
    if l2 < 1e-12 {
        return p.to_vec();
    }
    let refl = |q: (f64, f64)| {
        let t = ((q.0 - a.0) * dx + (q.1 - a.1) * dy) / l2;
        let foot = (a.0 + t * dx, a.1 + t * dy);
        (2.0 * foot.0 - q.0, 2.0 * foot.1 - q.1)
    };
    let mut out = p.to_vec();
    for q in p[1..n - 1].iter().rev() {
        out.push(refl(*q));
    }
    out
}

/// Per-vertex curve flags (bit `0x40`) aligned with the final polygon `poly`.  For HALF pieces
/// `poly` is `mirror_half(graded)` = `[0..n]` followed by the reflected middle `[n-2..1]`, so the
/// flags are mirrored the same way (reflection preserves curve/corner status).
fn build_contour(poly: &[(f64, f64)], src: &Contour, half: bool) -> PdsContour {
    let n = src.pts.len();
    let base: Vec<bool> = match &src.flags {
        Some(f) if f.len() == n => f.iter().map(|b| b & 0x40 != 0).collect(),
        _ => vec![false; n],
    };
    let mut curve = base.clone();
    if half && n >= 3 {
        for i in (1..n - 1).rev() {
            curve.push(base[i]);
        }
    }
    if curve.len() != poly.len() {
        curve = vec![false; poly.len()];
    }
    PdsContour { verts: poly.to_vec(), curve, control: vec![None; poly.len()] }
}

/// Notch anchor points graded to size `si` (item #21).  The notch anchor coincides with sew
/// vertex `k`; we shift the base notch by that vertex's (validated) grading delta.
fn graded_notches(src: &Contour, si: usize, base_idx: usize, nsizes: usize) -> Vec<(f64, f64)> {
    let mut ns: Vec<(usize, [f64; 4])> = src.notches.clone();
    ns.sort_by_key(|(k, _)| *k);
    let graded = grade(src, si, base_idx, nsizes);
    ns.iter()
        .map(|(k, q)| {
            let (dx, dy) = match &graded {
                Some(g) if *k < g.len() && *k < src.pts.len() => (g[*k].0 - src.pts[*k].0, g[*k].1 - src.pts[*k].1),
                _ => (0.0, 0.0),
            };
            (q[0] + dx, q[1] + dy)
        })
        .collect()
}

/// Validate a decoded grain line against the XML `<POSITION>` (item #21).
///
/// Only **y** is validated: the grain anchor's y equals POSITION y for 7/7 pant pieces (< 1e-3 cm).
/// The anchor's x does NOT equal POSITION x (FRONT 0.20 cm, BACK 0.41, FACING 0.76, belt 25.75 cm
/// off; only DRAWSTRING matches), so x is deliberately not used as evidence.
fn grain_ok(gr: &GrainRec, p: &XPiece) -> bool {
    match p.position {
        Some((px, py)) => {
            let _ = px;
            let y_ok = (gr.anchor.1 - py).abs() < 0.05;
            let x_ok = true;
            let ends_ok = gr.ends.0 .0.is_finite() && gr.ends.0 .1.is_finite() && gr.ends.1 .0.is_finite() && gr.ends.1 .1.is_finite();
            y_ok && x_ok && ends_ok && gr.angle.is_finite()
        }
        None => false,
    }
}

#[derive(Debug, Clone, Copy)]
struct Stats {
    w: f64,
    h: f64,
    area: f64,
    per: f64,
}

fn stats(p: &[(f64, f64)]) -> Stats {
    let n = p.len();
    let (mut a, mut l) = (0.0, 0.0);
    let (mut x0, mut x1, mut y0, mut y1) = (f64::MAX, f64::MIN, f64::MAX, f64::MIN);
    for i in 0..n {
        let (p1, p2) = (p[i], p[(i + 1) % n]);
        a += p1.0 * p2.1 - p2.0 * p1.1;
        l += ((p2.0 - p1.0).powi(2) + (p2.1 - p1.1).powi(2)).sqrt();
        x0 = x0.min(p1.0);
        x1 = x1.max(p1.0);
        y0 = y0.min(p1.1);
        y1 = y1.max(p1.1);
    }
    Stats { w: x1 - x0, h: y1 - y0, area: a.abs() / 2.0, per: l }
}

// ---------------------------------------------------------------------------------------------
// XML (tolerant scanner, no dependencies)
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
struct XGeom {
    size_x: Option<f64>,
    size_y: Option<f64>,
    area_cm2: Option<f64>,
    per: Option<f64>,
    sew_area_cm2: Option<f64>,
    sew_per: Option<f64>,
}

#[derive(Debug, Clone, Default)]
struct XPiece {
    name: String,
    quantity: u32,
    half: bool,
    /// `<POSITION X=.. Y=..>` — the grain-line anchor (== grain midpoint).  `None` if absent.
    position: Option<(f64, f64)>,
    geom: Vec<(String, XGeom)>,
}

#[derive(Debug, Clone, Default)]
struct XStyle {
    version: String,
    name: String,
    sizes: Vec<String>,
    base: String,
    cm_units: bool,
    pieces: Vec<XPiece>,
}

fn unescape(s: &str) -> String {
    s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&apos;", "'").replace("&amp;", "&")
}

fn tag_text<'a>(s: &'a str, tag: &str) -> Option<&'a str> {
    let open = format!("<{}>", tag);
    let close = format!("</{}>", tag);
    let a = s.find(&open)? + open.len();
    let b = s[a..].find(&close)? + a;
    Some(&s[a..b])
}

fn blocks<'a>(s: &'a str, tag: &str) -> Vec<&'a str> {
    let open = format!("<{}>", tag);
    let close = format!("</{}>", tag);
    let mut out = Vec::new();
    let mut pos = 0;
    while let Some(i) = s[pos..].find(&open) {
        let a = pos + i + open.len();
        match s[a..].find(&close) {
            Some(j) => {
                out.push(&s[a..a + j]);
                pos = a + j + close.len();
            }
            None => break,
        }
    }
    out
}

fn attr(s: &str, name: &str) -> Option<f64> {
    let key = format!("{}=\"", name);
    let mut from = 0;
    while let Some(i) = s[from..].find(&key) {
        let at = from + i;
        // make sure we matched a whole attribute name (e.g. AREA vs SEW_AREA)
        let prev_ok = at == 0 || !s.as_bytes()[at - 1].is_ascii_alphanumeric() && s.as_bytes()[at - 1] != b'_';
        let a = at + key.len();
        if prev_ok {
            let b = s[a..].find('"')? + a;
            return s[a..b].trim().parse::<f64>().ok();
        }
        from = a;
    }
    None
}

fn parse_xml(xml: &str) -> XStyle {
    let mut st = XStyle::default();
    st.version = tag_text(xml, "OPTITEX").unwrap_or("").trim().to_string();
    st.name = unescape(tag_text(xml, "NAME").unwrap_or("").trim());
    st.cm_units = match xml.find("<UNITS") {
        Some(i) => {
            let end = xml[i..].find('>').map(|e| i + e).unwrap_or(xml.len());
            let u = &xml[i..end];
            u.contains("LINEAR=\"cm\"") && u.contains("SQUARE=\"sq.m\"")
        }
        None => false,
    };
    if let Some(t) = tag_text(xml, "SIZES_TABLE") {
        for b in blocks(t, "SIZE") {
            if let Some(n) = tag_text(b, "NAME") {
                st.sizes.push(unescape(n.trim()));
            }
        }
        st.base = unescape(tag_text(t, "BASE_SIZE").unwrap_or("").trim());
    }
    for pb in blocks(xml, "PIECE") {
        let first_size = pb.find("<SIZE>").unwrap_or(pb.len());
        let head = &pb[..first_size];
        let mut p = XPiece::default();
        p.name = unescape(tag_text(head, "NAME").unwrap_or("").trim());
        p.quantity = tag_text(head, "QUANTITY").and_then(|q| q.trim().parse().ok()).unwrap_or(1);
        p.half = tag_text(head, "HALF").map_or(false, |h| !h.trim().is_empty());
        p.position = tag_text(head, "POSITION").and_then(|s| {
            // `X=188.0967 Y=299.0222`
            let x = s.find("X=").and_then(|i| s[i + 2..].split_whitespace().next()).and_then(|t| t.trim().parse::<f64>().ok());
            let y = s.find("Y=").and_then(|i| s[i + 2..].split_whitespace().next()).and_then(|t| t.trim().parse::<f64>().ok());
            match (x, y) {
                (Some(x), Some(y)) if x.is_finite() && y.is_finite() => Some((x, y)),
                _ => None,
            }
        });
        for sb in blocks(pb, "SIZE") {
            let sname = unescape(tag_text(sb, "NAME").unwrap_or("").trim());
            let mut g = XGeom::default();
            if let Some(i) = sb.find("<GEOM_INFO") {
                let e = sb[i..].find("/>").map(|e| i + e).unwrap_or(sb.len());
                let a = &sb[i..e];
                g.size_x = attr(a, "SIZE_X");
                g.size_y = attr(a, "SIZE_Y");
                g.area_cm2 = attr(a, "AREA").map(|v| v * 1.0e4);
                g.per = attr(a, "PERIMETER");
                g.sew_area_cm2 = attr(a, "SEW_AREA").map(|v| v * 1.0e4);
                g.sew_per = attr(a, "SEW_PERIMETER");
            }
            p.geom.push((sname, g));
        }
        st.pieces.push(p);
    }
    if st.sizes.is_empty() {
        if let Some(p) = st.pieces.first() {
            st.sizes = p.geom.iter().map(|(n, _)| n.clone()).collect();
        }
    }
    st
}

// ---------------------------------------------------------------------------------------------
// Container framing
// ---------------------------------------------------------------------------------------------

struct Frame {
    xml_start: usize,
    xml_end: usize,
    tail_start: usize,
    len_field_ok: bool,
}

fn frame(bytes: &[u8]) -> Result<Frame, String> {
    let xml_start = find(bytes, b"<?xml", 0).ok_or("no <?xml block found")?;
    let close = find(bytes, b"</STYLE>", xml_start).ok_or("no </STYLE> end tag")?;
    let mut xml_end = close + 8;
    let mut tail_start = xml_end;
    if bytes.get(xml_end) == Some(&0x0d) && bytes.get(xml_end + 1) == Some(&0x0a) {
        tail_start = xml_end + 2;
    }
    if tail_start > bytes.len() {
        tail_start = bytes.len();
    }
    if xml_end > bytes.len() {
        xml_end = bytes.len();
    }
    // u32 length field right before the XML = length of XML incl. trailing CRLF (proven on the pant sample).
    let len_field_ok = xml_start >= 4 && u32_at(bytes, xml_start - 4).map_or(false, |l| l as usize == tail_start - xml_start);
    Ok(Frame { xml_start, xml_end, tail_start, len_field_ok })
}

fn header_style(bytes: &[u8], xml_start: usize) -> Option<String> {
    // `01 04 <len> 20 <name>` somewhere in the header.
    let h = &bytes[..xml_start.min(bytes.len())];
    let i = find(h, &[0x01, 0x04], 0)?;
    let len = *h.get(i + 2)? as usize;
    if *h.get(i + 3)? != 0x20 {
        return None;
    }
    let s = h.get(i + 4..i + 4 + len)?;
    Some(String::from_utf8_lossy(s).into_owned())
}

/// Most frequent 4-byte window of the tail (the encoding of 0.0 under the XOR key).
fn detect_key(tail: &[u8]) -> Option<u32> {
    if tail.len() < 64 {
        return None;
    }
    let mut counts: HashMap<u32, usize> = HashMap::new();
    for i in 0..tail.len() - 3 {
        *counts.entry(u32::from_le_bytes([tail[i], tail[i + 1], tail[i + 2], tail[i + 3]])).or_insert(0) += 1;
    }
    let mut best: Option<(u32, usize)> = None;
    for (k, c) in counts {
        if k == 0 || k == 0xffff_ffff {
            continue;
        }
        if best.map_or(true, |(bk, bc)| c > bc || (c == bc && k < bk)) {
            best = Some((k, c));
        }
    }
    best.filter(|(_, c)| *c >= 16).map(|(k, _)| k)
}

fn ascii_strings(tail: &[u8], min: usize, cap: usize) -> Vec<(usize, String)> {
    let mut out = Vec::new();
    let mut i = 0;
    while i < tail.len() && out.len() < cap {
        if (0x20..0x7f).contains(&tail[i]) {
            let s = i;
            while i < tail.len() && (0x20..0x7f).contains(&tail[i]) {
                i += 1;
            }
            if i - s >= min {
                out.push((s, String::from_utf8_lossy(&tail[s..i]).into_owned()));
            }
        } else {
            i += 1;
        }
    }
    out
}

fn find_anchor(tail: &[u8], name: &str, from: usize) -> Option<usize> {
    let nb = name.as_bytes();
    if nb.is_empty() || nb.len() > 255 {
        return None;
    }
    let mut pat = vec![0x02, 0x10, nb.len() as u8, 0x20];
    pat.extend_from_slice(nb);
    find(tail, &pat, from)
}

/// Grain line of a piece (item #21), decoded from its region `[lo, hi)`.
///
/// Two records carry it (both `type 0x8c` = four keyed f32s):
/// * `55 8c  [scale, gx, gy, angle]`   — the grain **anchor** `(gx, gy)` and its direction.
/// * `c2 8c  [x1, y1, x2, y2]`         — the grain **line endpoints**.
///
/// PROVEN on the pant: the `c2 8c` endpoints' midpoint equals the `55 8c` anchor to < 1e-3 cm,
/// and the anchor y equals the XML `<POSITION>` y for every piece (x does not, see `grain_ok`).  The
/// finder returns the first `c2 8c` whose midpoint matches a `55 8c` anchor.
struct GrainRec {
    anchor: (f64, f64),
    angle: f64,
    ends: ((f64, f64), (f64, f64)),
}

fn read4(tail: &[u8], p: usize, key: u32) -> Option<[f64; 4]> {
    match read_typed(tail, p, key) {
        Some((Val::F(f), _)) if f.len() == 4 && f.iter().all(|v| v.is_finite() && v.abs() < 1e6) => {
            Some([f[0], f[1], f[2], f[3]])
        }
        _ => None,
    }
}

fn find_grain(tail: &[u8], lo: usize, hi: usize, key: u32) -> Option<GrainRec> {
    let hi = hi.min(tail.len());
    if lo >= hi {
        return None;
    }
    // anchor: `55 8c` with 4 floats.
    let mut anchor: Option<(f64, f64, f64)> = None;
    let mut p = lo;
    while p + 1 < hi {
        if tail[p] == 0x55 && tail[p + 1] == 0x8c {
            if let Some(f) = read4(tail, p, key) {
                anchor = Some((f[1], f[2], f[3]));
                break;
            }
        }
        p += 1;
    }
    let (ax, ay, angle) = anchor?;
    // endpoints: first `c2 8c` whose midpoint matches the anchor.
    let mut p = lo;
    while p + 1 < hi {
        if tail[p] == 0xc2 && tail[p + 1] == 0x8c {
            if let Some(f) = read4(tail, p, key) {
                let mid = ((f[0] + f[2]) / 2.0, (f[1] + f[3]) / 2.0);
                if (mid.0 - ax).abs() < 1e-2 && (mid.1 - ay).abs() < 1e-2 {
                    return Some(GrainRec { anchor: (ax, ay), angle, ends: ((f[0], f[1]), (f[2], f[3])) });
                }
            }
        }
        p += 1;
    }
    None
}

// ---------------------------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------------------------

const TOL_BBOX_CM: f64 = 0.2;
const TOL_PER_REL: f64 = 0.003;
const TOL_AREA_REL: f64 = 0.006;
const TOL_AREA_ABS_CM2: f64 = 0.6; // XML areas are rounded to 1e-4 m2 = 1 cm2

/// `bbox` is the bounding box of the STORED polygon (for HALF pieces the stored half: the XML
/// SIZE_X/SIZE_Y describe the half while AREA/PERIMETER describe the mirrored full piece).
fn check_cut(s: &Stats, bbox: (f64, f64), g: &XGeom) -> Result<(), String> {
    let (w, h, a, p) = match (g.size_x, g.size_y, g.area_cm2, g.per) {
        (Some(w), Some(h), Some(a), Some(p)) => (w, h, a, p),
        _ => return Err("XML has no cut GEOM_INFO".into()),
    };
    if (bbox.0 - w).abs() > TOL_BBOX_CM || (bbox.1 - h).abs() > TOL_BBOX_CM {
        return Err(format!("bbox {:.3}x{:.3} vs XML {:.3}x{:.3}", bbox.0, bbox.1, w, h));
    }
    if (s.per - p).abs() > TOL_PER_REL * p {
        return Err(format!("perimeter {:.3} vs XML {:.3}", s.per, p));
    }
    if (s.area - a).abs() > TOL_AREA_REL * a + TOL_AREA_ABS_CM2 {
        return Err(format!("area {:.2} cm2 vs XML {:.2}", s.area, a));
    }
    Ok(())
}

fn check_sew(s: &Stats, g: &XGeom) -> Result<(), String> {
    let (a, p) = match (g.sew_area_cm2, g.sew_per) {
        (Some(a), Some(p)) => (a, p),
        _ => return Err("XML has no sew GEOM_INFO".into()),
    };
    if (s.per - p).abs() > TOL_PER_REL * p {
        return Err(format!("sew perimeter {:.3} vs XML {:.3}", s.per, p));
    }
    if (s.area - a).abs() > TOL_AREA_REL * a + TOL_AREA_ABS_CM2 {
        return Err(format!("sew area {:.2} cm2 vs XML {:.2}", s.area, a));
    }
    Ok(())
}

// ---------------------------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------------------------

/// Container-level inspection (framing, key, string table, contour inventory).
pub fn inspect(bytes: &[u8]) -> Result<PdsInspect, String> {
    let fr = frame(bytes)?;
    let mut ins = PdsInspect::default();
    ins.xml_range = (fr.xml_start, fr.xml_end);
    ins.xml_len_field_ok = fr.len_field_ok;
    ins.tail_offset = fr.tail_start;
    let tail = &bytes[fr.tail_start.min(bytes.len())..];
    ins.tail_len = tail.len();
    ins.magic_ok = bytes.len() >= 4 && bytes[..4] == MAGIC;
    let hdr = &bytes[..fr.xml_start.min(bytes.len())];
    ins.header_words = (0..hdr.len() / 4).take(8).filter_map(|i| u32_at(hdr, i * 4)).collect();
    ins.header_style = header_style(bytes, fr.xml_start);
    let (key, src) = pick_keys(bytes, tail, ins.magic_ok).into_iter().next().unwrap_or((DEFAULT_KEY, "default".into()));
    ins.key = key;
    ins.key_source = src;
    let o = if tail.starts_with(&[0x0d, 0x0a]) { 2 } else { 0 };
    if tail.get(o) == Some(&0x24) && tail.get(o + 1) == Some(&0x0b) {
        if let Some(l) = u16_at(tail, o + 2) {
            if let Some(s) = tail.get(o + 4..o + 4 + l as usize) {
                ins.tail_path = Some(String::from_utf8_lossy(s).into_owned());
            }
        }
    }
    ins.strings = ascii_strings(tail, 6, 4000);
    let xml = String::from_utf8_lossy(&bytes[fr.xml_start..fr.xml_end.min(bytes.len())]).into_owned();
    let st = parse_xml(&xml);
    let mut from = 0;
    for p in &st.pieces {
        let a = find_anchor(tail, &p.name, from);
        if let Some(a) = a {
            from = a + 1;
        }
        ins.piece_anchors.push((p.name.clone(), a));
    }
    for c in find_contours(tail, 0, tail.len(), key) {
        ins.contours.push(ContourInfo {
            tail_offset: c.off,
            points: c.pts.len(),
            role: c.role,
            has_flags: c.flags.is_some(),
            grade_records: c.recs.len(),
            notch_records: c.notches.len(),
            parse_end: c.end,
            complete: c.complete,
        });
    }
    Ok(ins)
}

fn pick_keys(bytes: &[u8], tail: &[u8], magic_ok: bool) -> Vec<(u32, String)> {
    let mut v = Vec::new();
    if magic_ok {
        if let Some(k) = u32_at(bytes, 12) {
            v.push((k, "header dword @12".to_string()));
        }
    }
    if let Some(k) = detect_key(tail) {
        if !v.iter().any(|(x, _)| *x == k) {
            v.push((k, "most frequent tail dword".to_string()));
        }
    }
    if !v.iter().any(|(x, _)| *x == DEFAULT_KEY) {
        v.push((DEFAULT_KEY, "default (sample) key".to_string()));
    }
    v
}

/// Decode a PDS file.  Never panics.  `Err` only when no XML block can be found at all.
pub fn decode(bytes: &[u8]) -> Result<PdsBinDoc, String> {
    let fr = frame(bytes)?;
    let xml = String::from_utf8_lossy(&bytes[fr.xml_start..fr.xml_end.min(bytes.len())]).into_owned();
    let st = parse_xml(&xml);
    let mut doc = PdsBinDoc::default();
    doc.version = st.version.clone();
    doc.style = if st.name.is_empty() { header_style(bytes, fr.xml_start).unwrap_or_default() } else { st.name.clone() };
    doc.sizes = st.sizes.clone();
    doc.base_size = st.base.clone();
    if !fr.len_field_ok {
        doc.warnings.push("XML length field before the XML block does not match; header may be damaged".into());
    }
    if st.version != "21.4.1103.0" {
        doc.warnings.push(format!("Optitex version '{}' differs from the analysed 21.4.1103.0", st.version));
    }
    if st.pieces.is_empty() {
        doc.warnings.push("XML contains no <PIECE> blocks".into());
    }
    let tail: &[u8] = &bytes[fr.tail_start.min(bytes.len())..];
    let magic_ok = bytes.len() >= 4 && bytes[..4] == MAGIC;
    let nsizes = st.sizes.len();
    let base_idx = st.sizes.iter().position(|s| *s == st.base);

    // Pre-create empty entries (pieces x sizes).
    for p in &st.pieces {
        for s in &st.sizes {
            doc.pieces.push(PdsPieceGeom {
                name: p.name.clone(),
                size: s.clone(),
                cut: vec![],
                sew: vec![],
                notches: vec![],
                quantity: p.quantity,
                cut_contour: None,
                grain: None,
                position: p.position,
                internal_lines: vec![],
                drills: vec![],
            });
        }
    }
    let can_try = st.cm_units && base_idx.is_some() && !st.pieces.is_empty() && !tail.is_empty();
    if !st.cm_units {
        doc.warnings.push("XML units are not cm / sq.m; geometry decoding refused".into());
    }
    if base_idx.is_none() {
        doc.warnings.push("BASE_SIZE missing or not in size list; geometry decoding refused".into());
    }
    if !can_try {
        doc.decoded_geometry = false;
        return Ok(doc);
    }
    let base_idx = base_idx.unwrap_or(0);

    // Try each key candidate; keep the one that validates the most (piece,size) entries.
    // XML validation cannot see every key error: a flipped SIGN bit negates all coordinates (a point
    // reflection keeps bbox/area/perimeter) and low mantissa bits move points < 0.1 cm.  Ties are
    // therefore broken in favour of the candidate that equals the most frequent tail dword, i.e. the
    // keyed encoding of 0.0 (independent evidence, see `pds_key_*` tests / PDS-FORMAT.md section 2).
    let zero_enc = detect_key(tail);
    let total = st.pieces.len() * nsizes;
    let mut best: Option<(usize, bool, Vec<PdsPieceGeom>, Vec<String>)> = None;
    for (key, src) in pick_keys(bytes, tail, magic_ok) {
        let (entries, warns, ok) = decode_with_key(tail, &st, nsizes, base_idx, key);
        let is_zero_enc = zero_enc == Some(key);
        let better = best.as_ref().map_or(true, |(b, z, _, _)| ok > *b || (ok == *b && is_zero_enc && !*z));
        if better {
            let mut w = warns;
            if ok > 0 {
                w.insert(0, format!("XOR key {:#010x} taken from: {}", key, src));
            }
            best = Some((ok, is_zero_enc, entries, w));
        }
        if best.as_ref().map_or(false, |(b, z, _, _)| *b == total && (*z || zero_enc.is_none())) {
            break;
        }
    }
    let best = best.map(|(ok, _, e, w)| (ok, e, w));
    if let Some((ok, entries, warns)) = best {
        doc.pieces = entries;
        doc.warnings.extend(warns);
        doc.decoded_geometry = ok == st.pieces.len() * nsizes && ok > 0;
        if ok == 0 {
            doc.warnings.push("no piece/size geometry could be validated against the XML; none returned".into());
        }
    }
    Ok(doc)
}

fn decode_with_key(tail: &[u8], st: &XStyle, nsizes: usize, base_idx: usize, key: u32) -> (Vec<PdsPieceGeom>, Vec<String>, usize) {
    let mut warns = Vec::new();
    let mut entries = Vec::new();
    let mut ok_count = 0usize;
    // Anchors in XML order.
    let mut anchors: Vec<Option<usize>> = Vec::new();
    let mut from = 0;
    for p in &st.pieces {
        let a = find_anchor(tail, &p.name, from);
        if let Some(a) = a {
            from = a + 1;
        }
        anchors.push(a);
    }
    for (pi, p) in st.pieces.iter().enumerate() {
        let lo = anchors[pi];
        let hi = anchors.iter().skip(pi + 1).flatten().next().copied().unwrap_or(tail.len());
        let contours = match lo {
            Some(l) => find_contours(tail, l, hi, key),
            None => {
                warns.push(format!("piece '{}': name record not found in tail", p.name));
                Vec::new()
            }
        };
        let cuts: Vec<&Contour> = contours.iter().filter(|c| c.role == ContourRole::Cut).collect();
        let sews: Vec<&Contour> = contours.iter().filter(|c| c.role == ContourRole::Sew).collect();
        // Grain line (item #21): decoded once from the piece region, validated against POSITION.
        let grain = lo.and_then(|l| find_grain(tail, l, hi, key)).filter(|gr| grain_ok(gr, p));
        for (si, sname) in st.sizes.iter().enumerate() {
            let mut e = PdsPieceGeom {
                name: p.name.clone(),
                size: sname.clone(),
                cut: vec![],
                sew: vec![],
                notches: vec![],
                quantity: p.quantity,
                cut_contour: None,
                grain: None,
                position: p.position,
                internal_lines: vec![],
                drills: vec![],
            };
            let g = p.geom.iter().find(|(n, _)| n == sname).map(|(_, g)| g.clone());
            let g = match g {
                Some(g) => g,
                None => {
                    warns.push(format!("piece '{}' size '{}': no GEOM_INFO in XML, cannot validate", p.name, sname));
                    entries.push(e);
                    continue;
                }
            };
            // graded (pre-mirror) vertices + the final (mirrored, for HALF) polygon + bbox.
            let shape = |c: &Contour| -> Option<(Vec<(f64, f64)>, Vec<(f64, f64)>, (f64, f64))> {
                let graded = grade(c, si, base_idx, nsizes)?;
                let st = stats(&graded);
                let poly = if p.half { mirror_half(&graded) } else { graded.clone() };
                Some((graded, poly, (st.w, st.h)))
            };
            let mut fail: Vec<String> = Vec::new();
            // cut
            let mut cut_poly: Option<Vec<(f64, f64)>> = None;
            let mut cut_src: Option<&Contour> = None;
            for c in &cuts {
                match shape(c) {
                    Some((_graded, poly, bb)) => match check_cut(&stats(&poly), bb, &g) {
                        Ok(()) => {
                            cut_poly = Some(poly);
                            cut_src = Some(c);
                            break;
                        }
                        Err(m) => fail.push(format!("cut@{}: {}", c.off, m)),
                    },
                    None => fail.push(format!("cut@{}: grading data unusable", c.off)),
                }
            }
            // sew
            let mut sew_poly: Option<Vec<(f64, f64)>> = None;
            let mut sew_src: Option<&Contour> = None;
            let has_sew_xml = g.sew_area_cm2.is_some() && g.sew_per.is_some();
            for c in sews.iter() {
                match shape(c) {
                    Some((_graded, poly, bb)) => {
                        if has_sew_xml {
                            match check_sew(&stats(&poly), &g) {
                                Ok(()) => {
                                    sew_poly = Some(poly);
                                    sew_src = Some(c);
                                    break;
                                }
                                Err(m) => fail.push(format!("sew@{}: {}", c.off, m)),
                            }
                        } else if cuts.is_empty() {
                            // No separate cut contour and no SEW_* in XML: the single outline is
                            // both (DRAWSTRING in the sample); validate it as the cut outline.
                            match check_cut(&stats(&poly), bb, &g) {
                                Ok(()) => {
                                    cut_poly = Some(poly.clone());
                                    cut_src = Some(c);
                                    sew_poly = Some(poly);
                                    sew_src = Some(c);
                                    break;
                                }
                                Err(m) => fail.push(format!("outline@{}: {}", c.off, m)),
                            }
                        }
                    }
                    None => fail.push(format!("sew@{}: grading data unusable", c.off)),
                }
            }
            let need_sew = has_sew_xml;
            let good = cut_poly.is_some() && (!need_sew || sew_poly.is_some());
            if good {
                if let Some(poly) = cut_poly {
                    // cut contour with per-vertex curve flags (item #20), aligned with `poly`.
                    if let Some(src) = cut_src {
                        e.cut_contour = Some(build_contour(&poly, src, p.half));
                    }
                    e.cut = poly;
                }
                if let Some(poly) = sew_poly {
                    e.sew = poly;
                    if let Some(src) = sew_src {
                        // Notch grading (item #21): anchor vertex k is graded with the (validated)
                        // outline grading; the notch keeps its base offset.  Base size is directly
                        // validated against the marker; other sizes are reconstructions.
                        e.notches = graded_notches(src, si, base_idx, nsizes);
                    }
                }
                // Grain endpoints: base size only (grain grading is not validated).
                if si == base_idx {
                    e.grain = grain.as_ref().map(|gr| gr.ends);
                }
                ok_count += 1;
            } else {
                if contours.is_empty() && lo.is_some() {
                    fail.push("no contour objects recognised in the piece region".into());
                }
                warns.push(format!("piece '{}' size '{}': geometry NOT validated ({})", p.name, sname, fail.join("; ")));
            }
            entries.push(e);
        }
    }
    (entries, warns, ok_count)
}

// ---------------------------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn sample(name: &str) -> Option<Vec<u8>> {
        let dir = std::env::var("PDS_SAMPLE_DIR").unwrap_or_else(|_| "/home/claude/samples".into());
        let mut p = PathBuf::from(dir);
        p.push(name);
        match std::fs::read(&p) {
            Ok(b) => Some(b),
            Err(_) => {
                eprintln!("SKIP: sample {:?} not available", p);
                None
            }
        }
    }

    fn lcg(seed: &mut u64) -> u64 {
        *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        *seed >> 33
    }

    // ---- synthetic container (tests the machinery, NOT the truth of the format) ----------------

    fn enc_f(v: f32, key: u32) -> [u8; 4] {
        (v.to_bits() ^ key).to_le_bytes()
    }

    fn synthetic(key: u32, w: f32, h: f32) -> Vec<u8> {
        let area = (w * h) as f64 / 1.0e4;
        let per = 2.0 * (w + h) as f64;
        let xml = format!(
            "<?xml version=\"1.0\" standalone=\"no\"?>\r\n\r\n<STYLE>\r\n<OPTITEX>21.4.1103.0</OPTITEX>\r\n<UNITS LINEAR=\"cm\" SQUARE=\"sq.m\" />\r\n<NAME>SQ</NAME>\r\n<SIZES>1</SIZES>\r\n<PIECES>1</PIECES>\r\n<SIZES_TABLE><SIZE><NAME>S</NAME></SIZE><BASE_SIZE>S</BASE_SIZE></SIZES_TABLE>\r\n<PIECE><NAME>SQUARE</NAME><QUANTITY>3</QUANTITY><SIZE><NAME>S</NAME><GEOM_INFO SIZE_X=\"{:.4}\" SIZE_Y=\"{:.4}\" AREA=\"{:.4}\" PERIMETER=\"{:.4}\" /></SIZE></PIECE>\r\n</STYLE>\r\n",
            w, h, area, per
        );
        let mut b = Vec::new();
        b.extend_from_slice(&MAGIC);
        b.extend_from_slice(&0x25u32.to_le_bytes());
        b.extend_from_slice(&0x4au32.to_le_bytes());
        b.extend_from_slice(&key.to_le_bytes());
        b.extend_from_slice(&(xml.len() as u32).to_le_bytes());
        b.extend_from_slice(xml.as_bytes());
        // tail: anchor + cut header + contour + arrays
        b.extend_from_slice(&[0x02, 0x10, 6, 0x20]);
        b.extend_from_slice(b"SQUARE");
        b.extend_from_slice(&[0x4f, 0x04, 4, 0x24, 0x40, 0x28, 0x63, 0xc8]);
        b.extend_from_slice(&[0; 8]);
        b.extend_from_slice(&[0xff; 4]);
        b.extend_from_slice(&[0x5e, 0x9c]);
        for v in [0.0, 0.0, w, 0.0, w, h, 0.0, h] {
            b.extend_from_slice(&enc_f(v, key));
        }
        b.extend_from_slice(&[0x5f, 0x18, 4, 0, 0x80, 0x80, 0x80, 0x80]);
        b.extend_from_slice(&[0, 0, 0, 0]);
        b
    }

    /// Synthetic file whose tail also carries 40 keyed 0.0 values (as every real file does), so the
    /// "most frequent tail dword" key evidence exists.
    fn synthetic_padded(key: u32) -> Vec<u8> {
        let mut b = synthetic(key, 10.0, 10.0);
        for _ in 0..40 {
            b.extend_from_slice(&key.to_le_bytes());
        }
        b
    }

    #[test]
    fn synthetic_square_roundtrip() {
        let b = synthetic(0x1234_5678, 10.0, 10.0);
        let d = decode(&b).unwrap();
        assert!(d.decoded_geometry, "{:?}", d.warnings);
        assert_eq!(d.pieces.len(), 1);
        assert_eq!(d.pieces[0].cut.len(), 4);
        assert_eq!(d.pieces[0].quantity, 3);
        assert_eq!(d.style, "SQ");
    }

    #[test]
    fn synthetic_wrong_xml_is_rejected() {
        // Contour is 10x10 but the XML claims 12x10 => must NOT be returned.
        let mut b = synthetic(0x1234_5678, 10.0, 10.0);
        let s = String::from_utf8_lossy(&b).into_owned();
        let _ = s;
        let pos = find(&b, b"SIZE_X=\"10.0000\"", 0).unwrap();
        b[pos + 8] = b'1';
        b[pos + 9] = b'2';
        let d = decode(&b).unwrap();
        assert!(!d.decoded_geometry);
        assert!(d.pieces[0].cut.is_empty());
        assert!(d.warnings.iter().any(|w| w.contains("NOT validated")));
    }

    #[test]
    fn typed_reader_matches_documented_codes() {
        let k = 0u32;
        // f32 inline count 8 (0x9c), explicit count (0xa0)
        let mut b = vec![0x5e, 0x80];
        b.extend_from_slice(&1.5f32.to_bits().to_le_bytes());
        let (v, e) = read_typed(&b, 0, k).unwrap();
        assert_eq!(v, Val::F(vec![1.5]));
        assert_eq!(e, 6);
        let b = [0x62, 0xc4, 1, 0, 0, 0, 2, 0, 0, 0];
        assert_eq!(read_typed(&b, 0, k).unwrap().0, Val::I(vec![1, 2]));
        let b = [0xfd, 0x53, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0];
        assert_eq!(read_typed(&b, 0, k).unwrap().0, Val::H(vec![1; 5]));
        let b = [0x5f, 0x18, 2, 0, 9, 8];
        assert_eq!(read_typed(&b, 0, k).unwrap().0, Val::B(vec![9, 8]));
        // truncated
        assert!(read_typed(&[0x5f, 0x18, 9, 0, 1], 0, k).is_none());
        assert!(read_typed(&[0x5f], 0, k).is_none());
    }

    #[test]
    fn mirror_half_rectangle() {
        let half = [(0.0, 10.0), (5.0, 10.0), (5.0, 5.0), (5.0, 0.0), (0.0, 0.0)];
        let full = mirror_half(&half);
        let s = stats(&full);
        assert!((s.area - 100.0).abs() < 1e-9);
        assert!((s.per - 40.0).abs() < 1e-9 || (s.per - 30.0).abs() < 1e-9 || s.per > 0.0);
        assert!((s.w - 10.0).abs() < 1e-9 || (s.w - 5.0).abs() < 1e-9);
    }

    // ---- real sample -----------------------------------------------------------------------

    #[test]
    fn pant_decodes_and_validates_everything() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        assert_eq!(d.version, "21.4.1103.0");
        assert_eq!(d.style, "1079077- CROSS PKT PANT");
        assert_eq!(d.sizes, vec!["XS", "S", "M", "L", "XL"]);
        assert_eq!(d.base_size, "S");
        assert_eq!(d.pieces.len(), 7 * 5, "{:?}", d.warnings);
        assert!(d.decoded_geometry, "{:#?}", d.warnings);
        for p in &d.pieces {
            assert!(p.cut.len() >= 4, "{} {}", p.name, p.size);
        }
        // Known ground truth, base size S.
        let belt = d.pieces.iter().find(|p| p.name == "WAIST- BELT" && p.size == "S").unwrap();
        assert_eq!(belt.cut.len(), 8); // half (5) mirrored to full outline (8)
        let s = stats(&belt.cut);
        assert!((s.w - 105.6).abs() < 0.01, "{:?}", s);
        assert!((s.h - 13.0).abs() < 0.01);
        assert!((s.per - 237.2).abs() < 0.01);
        let front = d.pieces.iter().find(|p| p.name == "FRONT" && p.size == "S").unwrap();
        let s = stats(&front.cut);
        assert!((s.w - 108.8272).abs() < 0.001 && (s.h - 31.8795).abs() < 0.001, "{:?}", s);
        assert_eq!(front.quantity, 2);
        let pkt = d.pieces.iter().find(|p| p.name == "PKT-IN" && p.size == "S").unwrap();
        assert_eq!(pkt.notches.len(), 2);
        let facing = d.pieces.iter().find(|p| p.name == "FACING" && p.size == "S").unwrap();
        assert_eq!(facing.notches.len(), 2);
        let ds = d.pieces.iter().find(|p| p.name == "DRAWSTRING" && p.size == "XL").unwrap();
        assert!((stats(&ds.cut).w - 165.0).abs() < 0.01);
    }

    /// Prints (with --nocapture) and bounds the residuals against the XML numbers.
    #[test]
    fn pant_residuals_are_small() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        let x = parse_xml(&String::from_utf8_lossy(&b[69..15160]));
        let (mut wp, mut wa, mut wb) = (0.0f64, 0.0f64, 0.0f64);
        let mut base_p = 0.0f64;
        for xp in &x.pieces {
            for (sn, g) in &xp.geom {
                let e = d.pieces.iter().find(|e| e.name == xp.name && &e.size == sn).unwrap();
                let s = stats(&e.cut);
                let (gp, ga) = (g.per.unwrap(), g.area_cm2.unwrap());
                let dp = (s.per / gp - 1.0).abs() * 100.0;
                let da = (s.area / ga - 1.0).abs() * 100.0;
                wp = wp.max(dp);
                wa = wa.max(da);
                if sn == "S" {
                    base_p = base_p.max(dp);
                }
                if !xp.half {
                    wb = wb.max((s.w - g.size_x.unwrap()).abs()).max((s.h - g.size_y.unwrap()).abs());
                }
            }
        }
        eprintln!("cut residuals over 35 piece/sizes: max perimeter {:.3}% (base size {:.3}%), max area {:.3}%, max bbox {:.3} cm", wp, base_p, wa, wb);
        assert!(wp < 0.25 && base_p < 0.05 && wa < 0.4 && wb < 0.15);
    }

    #[test]
    fn pant_inspect_framing() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let i = inspect(&b).unwrap();
        assert!(i.magic_ok);
        assert!(i.xml_len_field_ok);
        assert_eq!(i.key, 0x6024_05c4);
        assert_eq!(i.header_style.as_deref(), Some("1079077- CROSS PKT PANT"));
        assert_eq!(i.xml_range.0, 69);
        assert_eq!(i.tail_offset, 15160);
        assert_eq!(i.tail_len, 75244); // 75246 in the .tail dump, which starts at the CRLF
        assert!(i.tail_path.as_deref().unwrap_or("").ends_with(".PDS"));
        assert!(i.piece_anchors.iter().all(|(_, a)| a.is_some()));
        assert!(i.contours.iter().filter(|c| c.role == ContourRole::Cut).count() == 6);
        assert!(i.contours.iter().filter(|c| c.role == ContourRole::Sew).count() == 7);
    }

    /// Independent check against the MARKER svg polygons (never used by the decoder): after
    /// aligning by one global translation (+ y flip, 0.01 cm units) every base-size cut vertex
    /// must lie within 0.1 cm of the marker outline.
    #[test]
    fn pant_matches_marker_svg() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        let xml = String::from_utf8_lossy(&b[..15160.min(b.len())]).into_owned();
        let m = &xml[xml.find("<MARKER").unwrap()..];
        let mut polys: Vec<Vec<(f64, f64)>> = Vec::new();
        let mut pos = 0;
        while let Some(i) = m[pos..].find("<polygon fill=\"#FFBE46\"") {
            let a = pos + i;
            let ps = m[a..].find("points=\"").unwrap() + a + 8;
            let pe = m[ps..].find('"').unwrap() + ps;
            let pts: Vec<(f64, f64)> = m[ps..pe]
                .split_whitespace()
                .map(|t| {
                    let mut it = t.split(',');
                    (it.next().unwrap().parse().unwrap(), it.next().unwrap().parse().unwrap())
                })
                .collect();
            polys.push(pts);
            pos = pe;
        }
        // marker order: belt right half, belt left half, FRONT, BACK, PKT-IN, FACING, DRAWSTRING, FACING1
        assert_eq!(polys.len(), 8);
        let order = [("FRONT", 2usize), ("BACK", 3), ("PKT-IN", 4), ("FACING", 5), ("DRAWSTRING", 6), ("FACING1", 7)];
        // global transform from belt right half: marker = ((x - 124.9967)*100, (399.462 - y)*100)
        let belt = d.pieces.iter().find(|p| p.name == "WAIST- BELT" && p.size == "S").unwrap();
        let bx0 = belt.cut.iter().map(|p| p.0).fold(f64::MAX, f64::min);
        let by1 = belt.cut.iter().map(|p| p.1).fold(f64::MIN, f64::max);
        let mx0 = polys[1].iter().map(|p| p.0).fold(f64::MAX, f64::min); // left half = full belt left edge
        let my0 = polys[1].iter().map(|p| p.1).fold(f64::MAX, f64::min);
        let (tx, ty) = (mx0 - bx0 * 100.0, my0 + by1 * 100.0);
        let dseg = |p: (f64, f64), a: (f64, f64), b: (f64, f64)| {
            let (dx, dy) = (b.0 - a.0, b.1 - a.1);
            let l = dx * dx + dy * dy;
            let u = if l == 0.0 { 0.0 } else { (((p.0 - a.0) * dx + (p.1 - a.1) * dy) / l).clamp(0.0, 1.0) };
            ((p.0 - a.0 - u * dx).powi(2) + (p.1 - a.1 - u * dy).powi(2)).sqrt()
        };
        for (name, pi) in order {
            let e = d.pieces.iter().find(|p| p.name == name && p.size == "S").unwrap();
            let poly = &polys[pi];
            let mut worst: f64 = 0.0;
            for v in &e.cut {
                let q = (v.0 * 100.0 + tx, ty - v.1 * 100.0);
                let dist = (0..poly.len()).map(|i| dseg(q, poly[i], poly[(i + 1) % poly.len()])).fold(f64::MAX, f64::min);
                worst = worst.max(dist);
            }
            assert!(worst < 10.0, "{}: decoded vertex {:.1} units (0.01 cm) from marker outline", name, worst);
        }
        // Notches: PKT-IN notch anchors coincide with the blue marker notch starts.
        let pkt = d.pieces.iter().find(|p| p.name == "PKT-IN" && p.size == "S").unwrap();
        let want = [(15258.0, 7920.0), (13738.0, 8423.0)];
        for w in want {
            assert!(
                pkt.notches.iter().any(|n| {
                    let q = (n.0 * 100.0 + tx, ty - n.1 * 100.0);
                    (q.0 - w.0).abs() < 2.0 && (q.1 - w.1).abs() < 2.0
                }),
                "notch {:?} not found in {:?}",
                w,
                pkt.notches
            );
        }
    }

    #[test]
    fn corrupted_shirt_xml_parses_geometry_refused() {
        let b = match sample("shirt_1078375_CORRUPTED_UPLOAD.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        assert_eq!(d.style, "1078375- Men Regular SS Shirt");
        assert_eq!(d.sizes, vec!["S", "M", "L", "XL", "XXL", "3XL"]);
        assert_eq!(d.pieces.len(), 7 * 6);
        assert!(!d.decoded_geometry);
        assert!(d.pieces.iter().all(|p| p.cut.is_empty() && p.sew.is_empty()));
        assert!(d.pieces.iter().any(|p| p.name == "back YK"));
        let i = inspect(&b).unwrap();
        assert!(!i.magic_ok);
    }

    #[test]
    fn fuzz_truncate_never_panics() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let mut seed = 7u64;
        for n in (0..b.len()).step_by(997).chain([0, 1, 4, 68, 69, 70, 15149, 15150, 15158, 15159, 15160, 15161, 15200, 20000]) {
            let _ = decode(&b[..n.min(b.len())]);
            let _ = inspect(&b[..n.min(b.len())]);
        }
        for _ in 0..40 {
            let n = (lcg(&mut seed) as usize) % b.len();
            let _ = decode(&b[..n]);
        }
    }

    #[test]
    fn fuzz_mangle_never_panics_and_never_lies() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let good = decode(&b).unwrap();
        let mut seed = 99u64;
        for round in 0..120 {
            let mut m = b.clone();
            let flips = 1 + (lcg(&mut seed) % 40) as usize;
            for _ in 0..flips {
                // keep the XML intact in most rounds so the geometry path is exercised
                let lo = if round % 3 == 0 { 0 } else { 15160 };
                let at = lo + (lcg(&mut seed) as usize) % (m.len() - lo);
                m[at] = (lcg(&mut seed) & 0xff) as u8;
            }
            if round % 5 == 0 {
                // UTF-8 replacement mangling like the corrupted shirt upload
                for x in m.iter_mut().skip(15160) {
                    if *x >= 0x80 {
                        *x = 0xbd;
                    }
                }
            }
            if let Ok(d) = decode(&m) {
                // any returned polygon must still satisfy the XML validation, i.e. either empty or
                // numerically consistent with the *unmodified* pant numbers.
                for (a, g) in d.pieces.iter().zip(good.pieces.iter()) {
                    if !a.cut.is_empty() && round % 3 != 0 {
                        let (sa, sg) = (stats(&a.cut), stats(&g.cut));
                        assert!((sa.per - sg.per).abs() < 0.01 * sg.per.max(1.0), "{} {}", a.name, a.size);
                    }
                }
            }
            let _ = inspect(&m);
        }
        // all-0xEF 0xBF 0xBD tail
        let mut m = b.clone();
        for (i, x) in m.iter_mut().enumerate().skip(15160) {
            *x = [0xef, 0xbf, 0xbd][i % 3];
        }
        let d = decode(&m).unwrap();
        assert!(!d.decoded_geometry);
    }

    // ---- item #20: curves ------------------------------------------------------------------

    /// Before/after perimeter error vs XML GEOM_INFO for every piece/size (printed with --nocapture).
    #[test]
    fn pant_curve_tessellation() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        let x = parse_xml(&String::from_utf8_lossy(&b[69..15160]));
        let (mut sum_v, mut sum_t, mut worse, mut n) = (0.0f64, 0.0f64, 0usize, 0usize);
        let (mut max_v, mut max_t) = (0.0f64, 0.0f64);
        for xp in &x.pieces {
            for (sn, g) in &xp.geom {
                let e = d.pieces.iter().find(|e| e.name == xp.name && &e.size == sn).unwrap();
                let c = e.cut_contour.as_ref().expect("validated piece has a contour");
                assert_eq!(c.verts, e.cut);
                assert_eq!(c.curve.len(), c.verts.len());
                let gp = g.per.unwrap();
                let ev = (stats(&e.cut).per / gp - 1.0).abs() * 100.0;
                let et = (stats(&c.tessellate(0.05)).per / gp - 1.0).abs() * 100.0;
                eprintln!("{:12} {:2}  vertex-only {:.4}%  tessellated {:.4}%", xp.name, sn, ev, et);
                sum_v += ev;
                sum_t += et;
                max_v = max_v.max(ev);
                max_t = max_t.max(et);
                if et > ev + 1e-9 {
                    worse += 1;
                }
                n += 1;
            }
        }
        eprintln!("CURVES: {} piece/sizes, mean |perimeter err| vertex {:.4}% -> tessellated {:.4}%, max {:.4}% -> {:.4}%, {} got worse", n, sum_v / n as f64, sum_t / n as f64, max_v, max_t, worse);
        assert!(sum_t < sum_v, "tessellation must reduce total perimeter error");
        assert!(max_t <= max_v + 1e-9);
    }

    #[test]
    fn tessellate_arc_and_degenerate() {
        // quarter circle r=10 sampled by 3 vertices, all flagged: interior edges become arcs.
        let pts: Vec<(f64, f64)> = (0..5).map(|i| { let t = i as f64 * 0.5 * std::f64::consts::FRAC_PI_2 / 2.0 * 2.0 / 2.0; (10.0 * t.cos(), 10.0 * t.sin()) }).collect();
        let c = PdsContour { verts: pts.clone(), curve: vec![true; 5], control: vec![None; 5] };
        let t = c.tessellate(0.1);
        assert!(t.len() > pts.len());
        for q in &t {
            let r = q.0.hypot(q.1);
            assert!(r.is_finite());
        }
        // no flags -> unchanged; hostile arguments never panic
        let c2 = PdsContour { verts: pts.clone(), curve: vec![false; 5], control: vec![] };
        assert_eq!(c2.tessellate(0.1), pts);
        for mc in [0.0, -1.0, f64::NAN, f64::INFINITY, 1e-300] {
            let _ = c.tessellate(mc);
        }
        let short = PdsContour { verts: vec![(0.0, 0.0), (1.0, 1.0)], curve: vec![], control: vec![] };
        assert_eq!(short.tessellate(0.1).len(), 2);
        let col = PdsContour { verts: vec![(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], curve: vec![true; 3], control: vec![None; 3] };
        assert_eq!(col.tessellate(0.1).len(), 3); // collinear: stays straight
        let bz = PdsContour { verts: pts.clone(), curve: vec![false; 5], control: vec![Some(((1.0, 1.0), (2.0, 1.0))), None, None, None, None] };
        assert!(bz.tessellate(0.1).len() > 5);
    }

    // ---- item #21: metadata ----------------------------------------------------------------

    #[test]
    fn pant_grain_matches_xml_position_and_marker() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        let mut with_grain = 0;
        for e in d.pieces.iter().filter(|e| e.size == "S") {
            let g = e.grain.unwrap_or_else(|| panic!("{} has no grain", e.name));
            let (_px, py) = e.position.unwrap();
            let mid = ((g.0 .0 + g.1 .0) / 2.0, (g.0 .1 + g.1 .1) / 2.0);
            assert!((mid.1 - py).abs() < 0.02, "{}: grain mid y {} vs POSITION {}", e.name, mid.1, py);
            with_grain += 1;
        }
        assert_eq!(with_grain, 7);
        // non-base sizes carry no grain (not validated)
        assert!(d.pieces.iter().filter(|e| e.size != "S").all(|e| e.grain.is_none()));
        // marker svg: the belt grain is the #FF6633 path M6310,9420 L6310,10668: vertical, 12.48 cm,
        // midpoint = POSITION.  Stored line: vertical (x1 == x2) and 6.24 cm = HALF of the marker
        // length (HYPOTHESIS: half-piece stores half the grain; length is NOT claimed validated).
        let belt = d.pieces.iter().find(|e| e.name == "WAIST- BELT" && e.size == "S").unwrap();
        let g = belt.grain.unwrap();
        assert!((g.0 .0 - g.1 .0).abs() < 1e-3, "belt grain must be vertical");
        let len = (g.0 .1 - g.1 .1).abs();
        assert!((len - 6.24).abs() < 0.01 && (2.0 * len - 12.48).abs() < 0.02, "belt grain length {}", len);
    }

    #[test]
    fn pant_quantity_and_notch_grading() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let d = decode(&b).unwrap();
        let x = parse_xml(&String::from_utf8_lossy(&b[69..15160]));
        for xp in &x.pieces {
            for e in d.pieces.iter().filter(|e| e.name == xp.name) {
                assert_eq!(e.quantity, xp.quantity);
            }
        }
        // PKT-IN has 2 notches in every size; notch-to-notch distance stays plausible (grading
        // moves the anchors with the sew outline; this is a reconstruction, see docs).
        for sz in ["XS", "S", "M", "L", "XL"] {
            let e = d.pieces.iter().find(|e| e.name == "PKT-IN" && e.size == sz).unwrap();
            assert_eq!(e.notches.len(), 2, "{}", sz);
            eprintln!("PKT-IN {} notches {:?}", sz, e.notches);
        }
        // no internal lines / drills exist in this sample
        assert!(d.pieces.iter().all(|e| e.internal_lines.is_empty() && e.drills.is_empty()));
    }

    // ---- item #24: key handling ------------------------------------------------------------

    #[test]
    fn key_header_equals_most_frequent_tail_dword() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let fr = frame(&b).unwrap();
        let tail = &b[fr.tail_start..];
        assert_eq!(u32_at(&b, 12), detect_key(tail));
    }

    #[test]
    fn damaged_header_key_is_recovered_from_tail() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let mut m = b.clone();
        m[12..16].copy_from_slice(&0xdead_beefu32.to_le_bytes());
        let d = decode(&m).unwrap();
        assert!(d.decoded_geometry, "{:?}", d.warnings);
        assert!(d.warnings.iter().any(|w| w.contains("most frequent tail dword")));
    }

    #[test]
    fn wrong_key_is_rejected() {
        let b = synthetic(0x1234_5678, 10.0, 10.0);
        let fr = frame(&b).unwrap();
        let xml = String::from_utf8_lossy(&b[fr.xml_start..fr.xml_end]).into_owned();
        let st = parse_xml(&xml);
        let tail = &b[fr.tail_start..];
        let (_, _, ok) = decode_with_key(tail, &st, 1, 0, 0x1234_5678);
        assert_eq!(ok, 1);
        for bad in [0u32, 0xffff_ffff, 0x6024_05c4, 0x1234_5678 ^ 0x0001_0000, 0x1234_5678 ^ 0x0100_0000] {
            let (e, _, ok) = decode_with_key(tail, &st, 1, 0, bad);
            assert_eq!(ok, 0, "key {:#x} must not validate", bad);
            assert!(e[0].cut.is_empty() && e[0].cut_contour.is_none());
        }
        // the full decode still finds the right key when the header word is wrong
        let mut m = synthetic_padded(0x1234_5678);
        m[12..16].copy_from_slice(&0x0badf00du32.to_le_bytes());
        assert!(decode(&m).unwrap().decoded_geometry);
    }

    #[test]
    fn pant_wrong_key_rejected() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let fr = frame(&b).unwrap();
        let st = parse_xml(&String::from_utf8_lossy(&b[fr.xml_start..fr.xml_end]));
        let tail = &b[fr.tail_start..];
        let (_, _, ok) = decode_with_key(tail, &st, 5, 1, 0x6024_05c4);
        assert_eq!(ok, 35);
        for bad in [0x6024_05c4u32 ^ 0x0001_0000, 0x6024_05c4 ^ 0x0100_0000, 0x0000_0000, 0x5fa4_05c4] {
            let (e, _, ok) = decode_with_key(tail, &st, 5, 1, bad);
            assert_eq!(ok, 0, "{:#x}", bad);
            assert!(e.iter().all(|p| p.cut.is_empty() && p.grain.is_none() && p.cut_contour.is_none()));
        }
    }

    /// Which single-bit errors of the key does XML validation catch?  (Printed.)  A flipped key bit k
    /// flips bit k of every stored f32; low mantissa bits move coordinates by < 0.2 cm and pass the
    /// XML tolerances, so the key is only determined by validation down to ~bit 12.  The exact key is
    /// still obtained from the header / most-frequent-dword candidates (tried first).
    #[test]
    fn pant_key_bit_sensitivity() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let fr = frame(&b).unwrap();
        let st = parse_xml(&String::from_utf8_lossy(&b[fr.xml_start..fr.xml_end]));
        let tail = &b[fr.tail_start..];
        let mut caught = Vec::new();
        let mut passed = Vec::new();
        for bit in 0..32 {
            let (_, _, ok) = decode_with_key(tail, &st, 5, 1, 0x6024_05c4 ^ (1u32 << bit));
            if ok == 0 { caught.push(bit) } else { passed.push((bit, ok)) }
        }
        eprintln!("key single-bit errors rejected: bits {:?}; still validate: {:?}", caught, passed);
        assert!(caught.contains(&24) && caught.contains(&16));
        // sign bit: undetectable by XML (point reflection) -> handled by the zero-encoding tie-break
        assert!(!caught.contains(&31) && !caught.contains(&0));
    }

    /// Header key with the SIGN bit flipped validates against the XML (reflected geometry!), so the
    /// tie-break must pick the tail-mode key and return the true, un-reflected coordinates.
    #[test]
    fn sign_flipped_header_key_does_not_reflect_geometry() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let good = decode(&b).unwrap();
        let mut m = b.clone();
        let k = u32_at(&m, 12).unwrap() ^ 0x8000_0000;
        m[12..16].copy_from_slice(&k.to_le_bytes());
        let d = decode(&m).unwrap();
        assert!(d.decoded_geometry);
        assert_eq!(d.pieces, good.pieces, "geometry must be identical to the intact decode");
        // synthetic too
        let sb = synthetic_padded(0x1234_5678);
        let mut sm = sb.clone();
        sm[12..16].copy_from_slice(&(0x1234_5678u32 ^ 0x8000_0000).to_le_bytes());
        let (a, c) = (decode(&sb).unwrap(), decode(&sm).unwrap());
        assert_eq!(a.pieces[0].cut, c.pieces[0].cut);
    }

    #[test]
    fn fuzz_new_fields_never_panic_or_lie() {
        let b = match sample("pant_1074664.PDS") {
            Some(b) => b,
            None => return,
        };
        let mut seed = 4242u64;
        for _ in 0..150 {
            let mut m = b.clone();
            for _ in 0..(1 + lcg(&mut seed) % 30) {
                let at = 15160 + (lcg(&mut seed) as usize) % (m.len() - 15160);
                m[at] = (lcg(&mut seed) & 0xff) as u8;
            }
            if let Ok(d) = decode(&m) {
                for e in &d.pieces {
                    if let Some(c) = &e.cut_contour {
                        assert_eq!(c.verts.len(), c.curve.len());
                        let t = c.tessellate(0.05);
                        assert!(t.iter().all(|q| q.0.is_finite() && q.1.is_finite()));
                    }
                    if let Some(g) = e.grain {
                        // a returned grain must still be consistent with the XML POSITION
                        let (_, py) = e.position.unwrap();
                        assert!((((g.0 .1 + g.1 .1) / 2.0) - py).abs() < 0.05);
                    }
                }
            }
        }
        for n in (15160..b.len()).step_by(1511) {
            let _ = decode(&b[..n]);
        }
    }

    #[test]
    fn garbage_inputs() {
        assert!(decode(&[]).is_err());
        assert!(decode(b"<?xml").is_err());
        assert!(decode(b"<?xml version='1.0'?><STYLE></STYLE>").is_ok());
        let mut seed = 5u64;
        for len in [1usize, 10, 100, 1000, 5000] {
            let v: Vec<u8> = (0..len).map(|_| (lcg(&mut seed) & 0xff) as u8).collect();
            let _ = decode(&v);
            let _ = inspect(&v);
        }
        // XML present with hostile numbers
        let x = b"<?xml?><STYLE><UNITS LINEAR=\"cm\" SQUARE=\"sq.m\" /><SIZES_TABLE><SIZE><NAME>S</NAME></SIZE><BASE_SIZE>S</BASE_SIZE></SIZES_TABLE><PIECE><NAME>A</NAME><SIZE><NAME>S</NAME><GEOM_INFO SIZE_X=\"1e999\" SIZE_Y=\"nan\" AREA=\"-1\" PERIMETER=\"\" /></SIZE></PIECE></STYLE>\r\n\x02\x10\x01\x20A\x5e\xa0\xff\xff";
        let d = decode(x).unwrap();
        assert!(!d.decoded_geometry);
    }
}
