//! Import of the *readable* parts of Optitex `.PDS` files.
//!
//! A `.PDS` is a proprietary binary container. Embedded in it (in clear text, even
//! when the binary parts are damaged) is a `<?xml ...?><STYLE>...</STYLE>` block with
//! the style summary, per-piece/per-size `GEOM_INFO` and a `<MARKER>` SVG preview of
//! the base size laid out on a marker. This module scans the raw bytes for that block,
//! parses it with a small tolerant XML scanner and:
//!
//! * extracts style / piece / size metadata,
//! * extracts marker outlines (cut polygon, sew polygon, notches, grain line),
//! * derives the marker unit scale by least squares against `GEOM_INFO` and assigns
//!   each outline to a named piece (reporting the match error per outline),
//! * builds a PatternForge [`Pattern`] (y-up cm, straight segments only).
//!
//! HONESTY NOTE: the result is a preview-quality outline at the base size taken from
//! the marker SVG. It is NOT the parametric / graded Optitex geometry (no curves, no
//! other sizes, integer marker resolution, mirrored/rotated placement as in the marker).
//!
//! The parser never panics on malformed input; all numbers must be finite and sizes
//! are capped (see the `MAX_*` constants).
use crate::geom::*;
use crate::json::Json;
use crate::model::{Node, Notch, Pattern, Piece};
use std::collections::HashMap;

const MAX_INPUT: usize = 256 << 20;
const MAX_XML: usize = 64 << 20;
const MAX_ELEMS: usize = 400_000;
const MAX_DEPTH: usize = 64;
const MAX_PIECES: usize = 500;
const MAX_SIZES: usize = 200;
const MAX_OUTLINES: usize = 1000;
const MAX_POINTS_PER_POLY: usize = 50_000;
const MAX_TOTAL_POINTS: usize = 2_000_000;
const MAX_COORD: f64 = 1e8;
const MAX_NUM: f64 = 1e9;
const MATCH_MAX_COST: f64 = 0.15;

pub const CUT_FILL: &str = "#FFBE46";
pub const BACKGROUND_FILL: &str = "#CCCC33";
pub const SEW_FILL: &str = "#000000";
pub const NOTCH_FILL: &str = "#0000FF";
pub const GRAIN_FILL: &str = "#FF6633";

pub const PREVIEW_WARNING: &str = "geometry_source=marker_svg_preview: outlines are the BASE SIZE as laid out in the marker SVG (integer marker units, straight segments only, no curves/handles). This is preview-quality, NOT the parametric or graded Optitex geometry; other sizes are not reconstructed.";

type Pt = (f64, f64);

// ---------------------------------------------------------------------------
// 1. Locating the XML block in the raw bytes
// ---------------------------------------------------------------------------

fn find_bytes(h: &[u8], n: &[u8], from: usize) -> Option<usize> {
    if n.is_empty() || from >= h.len() || h.len() - from < n.len() {
        return None;
    }
    h[from..].windows(n.len()).position(|w| w == n).map(|p| p + from)
}

fn rfind_bytes(h: &[u8], n: &[u8], from: usize) -> Option<usize> {
    if n.is_empty() || from >= h.len() || h.len() - from < n.len() {
        return None;
    }
    h[from..].windows(n.len()).rposition(|w| w == n).map(|p| p + from)
}

/// Returns (xml text decoded lossily, truncated?) found by scanning bytes for
/// `<?xml` / `<STYLE` ... `</STYLE>`.
pub fn extract_xml_block(bytes: &[u8]) -> Result<(String, bool), String> {
    if bytes.is_empty() {
        return Err("empty input".into());
    }
    if bytes.len() > MAX_INPUT {
        return Err(format!("input too large ({} bytes, max {})", bytes.len(), MAX_INPUT));
    }
    // first `<STYLE` followed by '>' or whitespace
    let mut from = 0;
    let style = loop {
        match find_bytes(bytes, b"<STYLE", from) {
            None => return Err("no <STYLE> block found (not an Optitex PDS with an embedded XML summary?)".into()),
            Some(p) => {
                let nx = bytes.get(p + 6).copied().unwrap_or(0);
                if nx == b'>' || nx.is_ascii_whitespace() {
                    break p;
                }
                from = p + 6;
            }
        }
    };
    // include an `<?xml` declaration if it sits just before
    let lo = style.saturating_sub(512);
    let start = match rfind_bytes(&bytes[..style], b"<?xml", lo) {
        Some(p) => p,
        None => style,
    };
    let (end, truncated) = match rfind_bytes(bytes, b"</STYLE>", style) {
        Some(p) => (p + 8, false),
        None => (bytes.len(), true),
    };
    if end - start > MAX_XML {
        return Err(format!("XML block too large ({} bytes)", end - start));
    }
    Ok((String::from_utf8_lossy(&bytes[start..end]).into_owned(), truncated))
}

// ---------------------------------------------------------------------------
// 2. Tolerant XML scanner
// ---------------------------------------------------------------------------

#[derive(Default, Debug, Clone)]
struct Elem {
    name: String,
    attrs: Vec<(String, String)>,
    kids: Vec<Elem>,
    text: String,
}

impl Elem {
    fn attr(&self, k: &str) -> Option<&str> {
        self.attrs.iter().find(|(n, _)| n.eq_ignore_ascii_case(k)).map(|(_, v)| v.as_str())
    }
    fn is(&self, n: &str) -> bool {
        self.name.eq_ignore_ascii_case(n)
    }
    fn child(&self, n: &str) -> Option<&Elem> {
        self.kids.iter().find(|k| k.is(n))
    }
    fn children<'a>(&'a self, n: &'a str) -> impl Iterator<Item = &'a Elem> + 'a {
        self.kids.iter().filter(move |k| k.is(n))
    }
    fn child_text(&self, n: &str) -> String {
        self.child(n).map(|c| c.text.trim().to_string()).unwrap_or_default()
    }
    fn find_desc(&self, n: &str) -> Option<&Elem> {
        for k in &self.kids {
            if k.is(n) {
                return Some(k);
            }
            if let Some(f) = k.find_desc(n) {
                return Some(f);
            }
        }
        None
    }
}

fn decode_entities(s: &str) -> String {
    if !s.contains('&') {
        return s.to_string();
    }
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(p) = rest.find('&') {
        out.push_str(&rest[..p]);
        let tail = &rest[p..];
        match tail.find(';').filter(|&e| e <= 10) {
            Some(e) => {
                let ent = &tail[1..e];
                let rep = match ent {
                    "amp" => Some('&'),
                    "lt" => Some('<'),
                    "gt" => Some('>'),
                    "quot" => Some('"'),
                    "apos" => Some('\''),
                    _ => {
                        if let Some(h) = ent.strip_prefix("#x").or_else(|| ent.strip_prefix("#X")) {
                            u32::from_str_radix(h, 16).ok().and_then(char::from_u32)
                        } else if let Some(d) = ent.strip_prefix('#') {
                            d.parse::<u32>().ok().and_then(char::from_u32)
                        } else {
                            None
                        }
                    }
                };
                match rep {
                    Some(c) => {
                        out.push(c);
                        rest = &tail[e + 1..];
                    }
                    None => {
                        out.push('&');
                        rest = &tail[1..];
                    }
                }
            }
            None => {
                out.push('&');
                rest = &tail[1..];
            }
        }
    }
    out.push_str(rest);
    out
}

fn parse_attrs(s: &str) -> Vec<(String, String)> {
    let b = s.as_bytes();
    let mut i = 0;
    let mut out = Vec::new();
    while i < b.len() {
        while i < b.len() && (b[i].is_ascii_whitespace() || b[i] == b'/') {
            i += 1;
        }
        let ks = i;
        while i < b.len() && !b[i].is_ascii_whitespace() && b[i] != b'=' && b[i] != b'/' {
            i += 1;
        }
        if i == ks {
            i += 1;
            continue;
        }
        let key = &s[ks..i];
        while i < b.len() && b[i].is_ascii_whitespace() {
            i += 1;
        }
        if i < b.len() && b[i] == b'=' {
            i += 1;
            while i < b.len() && b[i].is_ascii_whitespace() {
                i += 1;
            }
            let val;
            if i < b.len() && (b[i] == b'"' || b[i] == b'\'') {
                let q = b[i];
                i += 1;
                let vs = i;
                while i < b.len() && b[i] != q {
                    i += 1;
                }
                val = &s[vs..i];
                i = (i + 1).min(b.len());
            } else {
                let vs = i;
                while i < b.len() && !b[i].is_ascii_whitespace() && b[i] != b'/' {
                    i += 1;
                }
                val = &s[vs..i];
            }
            out.push((key.to_string(), decode_entities(val)));
        } else {
            out.push((key.to_string(), String::new()));
        }
    }
    out
}

/// Tolerant parse: unclosed elements are auto-closed at EOF, stray/mismatched close tags are
/// ignored (or close back to the matching ancestor), a truncated trailing tag is dropped.
fn parse_xml(s: &str, warns: &mut Vec<String>) -> Result<Elem, String> {
    let b = s.as_bytes();
    let mut stack: Vec<Elem> = vec![Elem { name: "#root".into(), ..Default::default() }];
    let mut i = 0;
    let mut count = 0usize;
    let mut stray = 0usize;
    while i < b.len() {
        let lt = match b[i..].iter().position(|&c| c == b'<') {
            Some(p) => i + p,
            None => {
                push_text(&mut stack, &s[i..]);
                break;
            }
        };
        if lt > i {
            push_text(&mut stack, &s[i..lt]);
        }
        let rest = &b[lt..];
        if rest.starts_with(b"<!--") {
            match find_bytes(b, b"-->", lt + 4) {
                Some(e) => i = e + 3,
                None => break,
            }
        } else if rest.starts_with(b"<![CDATA[") {
            match find_bytes(b, b"]]>", lt + 9) {
                Some(e) => {
                    push_text(&mut stack, &s[lt + 9..e]);
                    i = e + 3;
                }
                None => break,
            }
        } else if rest.starts_with(b"<?") {
            match find_bytes(b, b"?>", lt + 2) {
                Some(e) => i = e + 2,
                None => break,
            }
        } else if rest.starts_with(b"<!") {
            match b[lt..].iter().position(|&c| c == b'>') {
                Some(e) => i = lt + e + 1,
                None => break,
            }
        } else if rest.starts_with(b"</") {
            let e = match b[lt..].iter().position(|&c| c == b'>') {
                Some(e) => lt + e,
                None => break,
            };
            let name = s[lt + 2..e].trim();
            let depth = stack.len();
            let found = (1..depth).rev().find(|&k| stack[k].name.eq_ignore_ascii_case(name));
            match found {
                Some(k) => {
                    while stack.len() > k {
                        close_top(&mut stack);
                    }
                }
                None => stray += 1,
            }
            i = e + 1;
        } else {
            // open tag; scan to '>' honouring quotes
            let mut j = lt + 1;
            let mut q: u8 = 0;
            let mut end = None;
            while j < b.len() {
                let c = b[j];
                if q != 0 {
                    if c == q {
                        q = 0;
                    }
                } else if c == b'"' || c == b'\'' {
                    q = c;
                } else if c == b'>' {
                    end = Some(j);
                    break;
                }
                j += 1;
            }
            let e = match end {
                Some(e) => e,
                None => break, // truncated tag
            };
            let mut inner = &s[lt + 1..e];
            let selfclose = inner.ends_with('/');
            if selfclose {
                inner = &inner[..inner.len() - 1];
            }
            let ns = inner.find(|c: char| c.is_ascii_whitespace()).unwrap_or(inner.len());
            let name = inner[..ns].trim();
            if name.is_empty() || !name.chars().next().map_or(false, |c| c.is_alphabetic() || c == '_') {
                // not a real tag (stray '<' in garbage text)
                i = lt + 1;
                continue;
            }
            count += 1;
            if count > MAX_ELEMS {
                return Err(format!("too many XML elements (>{})", MAX_ELEMS));
            }
            let el = Elem { name: name.to_string(), attrs: parse_attrs(&inner[ns..]), ..Default::default() };
            if selfclose {
                if let Some(top) = stack.last_mut() {
                    top.kids.push(el);
                }
            } else {
                if stack.len() >= MAX_DEPTH {
                    return Err(format!("XML nesting deeper than {}", MAX_DEPTH));
                }
                stack.push(el);
            }
            i = e + 1;
        }
    }
    if stack.len() > 1 {
        warns.push("XML block ended inside an open element (truncated); open elements were auto-closed".into());
    }
    while stack.len() > 1 {
        close_top(&mut stack);
    }
    if stray > 0 {
        warns.push(format!("{} stray/mismatched closing tag(s) ignored", stray));
    }
    Ok(stack.pop().unwrap_or_default())
}

fn close_top(stack: &mut Vec<Elem>) {
    if stack.len() > 1 {
        if let Some(e) = stack.pop() {
            if let Some(p) = stack.last_mut() {
                p.kids.push(e);
            }
        }
    }
}

fn push_text(stack: &mut [Elem], t: &str) {
    let t = t.trim();
    if t.is_empty() {
        return;
    }
    if let Some(top) = stack.last_mut() {
        if top.text.len() < 4096 {
            if !top.text.is_empty() {
                top.text.push(' ');
            }
            top.text.push_str(&decode_entities(t));
        }
    }
}

// ---------------------------------------------------------------------------
// 3. Numbers, paths
// ---------------------------------------------------------------------------

fn parse_f(s: &str) -> Option<f64> {
    s.trim().parse::<f64>().ok().filter(|v| v.is_finite() && v.abs() <= MAX_NUM)
}

fn lead_num(s: &str) -> Option<f64> {
    // leading float of e.g. "180 deg."
    let t = s.trim();
    let end = t
        .find(|c: char| !(c.is_ascii_digit() || c == '.' || c == '-' || c == '+' || c == 'e' || c == 'E'))
        .unwrap_or(t.len());
    parse_f(&t[..end])
}

fn parse_u32(s: &str) -> Option<u32> {
    s.trim().parse::<u32>().ok()
}

/// All numbers in a string separated by whitespace/commas (e.g. SVG `points`).
fn numbers_in(s: &str) -> (Vec<f64>, bool) {
    let mut v = Vec::new();
    let mut bad = false;
    for t in s.split(|c: char| c.is_ascii_whitespace() || c == ',') {
        if t.is_empty() {
            continue;
        }
        match parse_f(t) {
            Some(x) => v.push(x),
            None => bad = true,
        }
    }
    (v, bad)
}

#[derive(Clone, Copy, Debug)]
enum Tok {
    Cmd(char),
    Num(f64),
    Bad,
}

fn tokenize_path(d: &str) -> Vec<Tok> {
    let b = d.as_bytes();
    let mut i = 0;
    let mut out = Vec::new();
    while i < b.len() {
        let c = b[i];
        if c.is_ascii_whitespace() || c == b',' {
            i += 1;
        } else if b"MmLlHhVvZzCcSsQqTtAa".contains(&c) {
            out.push(Tok::Cmd(c as char));
            i += 1;
        } else if c == b'-' || c == b'+' || c == b'.' || c.is_ascii_digit() {
            let st = i;
            if b[i] == b'-' || b[i] == b'+' {
                i += 1;
            }
            while i < b.len() && b[i].is_ascii_digit() {
                i += 1;
            }
            if i < b.len() && b[i] == b'.' {
                i += 1;
                while i < b.len() && b[i].is_ascii_digit() {
                    i += 1;
                }
            }
            if i < b.len() && (b[i] == b'e' || b[i] == b'E') {
                let mut k = i + 1;
                if k < b.len() && (b[k] == b'-' || b[k] == b'+') {
                    k += 1;
                }
                if k < b.len() && b[k].is_ascii_digit() {
                    while k < b.len() && b[k].is_ascii_digit() {
                        k += 1;
                    }
                    i = k;
                }
            }
            if i == st {
                i += 1;
                out.push(Tok::Bad);
            } else {
                match parse_f(&d[st..i]) {
                    Some(v) => out.push(Tok::Num(v)),
                    None => out.push(Tok::Bad),
                }
            }
        } else {
            out.push(Tok::Bad);
            i += 1;
        }
    }
    out
}

/// Parse SVG path data into subpaths of points. Curves/arcs are approximated by their end
/// points (flagged through `curved`). Never panics; malformed tails are dropped.
fn parse_path(d: &str, curved: &mut bool, bad: &mut bool) -> Vec<Vec<Pt>> {
    let toks = tokenize_path(d);
    let mut subs: Vec<Vec<Pt>> = Vec::new();
    let mut cur_sub: Vec<Pt> = Vec::new();
    let mut cur: Pt = (0.0, 0.0);
    let mut start: Pt = (0.0, 0.0);
    let mut i = 0;
    let mut cmd = ' ';
    let mut npts = 0usize;
    while i < toks.len() {
        match toks[i] {
            Tok::Cmd(c) => {
                cmd = c;
                i += 1;
                if c == 'Z' || c == 'z' {
                    if !cur_sub.is_empty() {
                        subs.push(std::mem::take(&mut cur_sub));
                    }
                    cur = start;
                }
                continue;
            }
            Tok::Bad => {
                *bad = true;
                i += 1;
                continue;
            }
            Tok::Num(_) => {}
        }
        let up = cmd.to_ascii_uppercase();
        let n = match up {
            'M' | 'L' | 'T' => 2,
            'H' | 'V' => 1,
            'C' => 6,
            'S' | 'Q' => 4,
            'A' => 7,
            _ => {
                // numbers without a command
                *bad = true;
                i += 1;
                continue;
            }
        };
        let mut a = [0.0f64; 7];
        let mut ok = true;
        for k in 0..n {
            match toks.get(i + k) {
                Some(Tok::Num(v)) => a[k] = *v,
                _ => {
                    ok = false;
                    break;
                }
            }
        }
        if !ok {
            *bad = true;
            i += 1;
            continue;
        }
        i += n;
        let rel = cmd.is_ascii_lowercase();
        let (bx, by) = if rel { cur } else { (0.0, 0.0) };
        let np: Pt = match up {
            'M' | 'L' | 'T' => (bx + a[0], by + a[1]),
            'H' => (if rel { cur.0 + a[0] } else { a[0] }, cur.1),
            'V' => (cur.0, if rel { cur.1 + a[0] } else { a[0] }),
            'C' => {
                *curved = true;
                (bx + a[4], by + a[5])
            }
            'S' | 'Q' => {
                *curved = true;
                (bx + a[2], by + a[3])
            }
            _ => {
                *curved = true;
                (bx + a[5], by + a[6])
            }
        };
        if up == 'M' {
            if !cur_sub.is_empty() {
                subs.push(std::mem::take(&mut cur_sub));
            }
            start = np;
            // subsequent implicit pairs are lineto
            cmd = if rel { 'l' } else { 'L' };
        } else if cur_sub.is_empty() {
            // path continuing after Z without M
            cur_sub.push(cur);
        }
        cur_sub.push(np);
        cur = np;
        npts += 1;
        if npts > MAX_POINTS_PER_POLY {
            break;
        }
    }
    if !cur_sub.is_empty() {
        subs.push(cur_sub);
    }
    subs
}

fn dedupe_closed(mut p: Vec<Pt>) -> Vec<Pt> {
    p.dedup();
    while p.len() > 1 && p.first() == p.last() {
        p.pop();
    }
    p
}

fn poly_area(p: &[Pt]) -> f64 {
    let n = p.len();
    if n < 3 {
        return 0.0;
    }
    let mut s = 0.0;
    for i in 0..n {
        let (a, b) = (p[i], p[(i + 1) % n]);
        s += a.0 * b.1 - b.0 * a.1;
    }
    s.abs() * 0.5
}

fn poly_perim(p: &[Pt]) -> f64 {
    let n = p.len();
    if n < 2 {
        return 0.0;
    }
    (0..n).map(|i| dist(p[i], p[(i + 1) % n])).sum()
}

fn dist(a: Pt, b: Pt) -> f64 {
    ((a.0 - b.0).powi(2) + (a.1 - b.1).powi(2)).sqrt()
}

fn bbox(p: &[Pt]) -> Option<(f64, f64, f64, f64)> {
    let f = p.first()?;
    let mut r = (f.0, f.1, f.0, f.1);
    for q in p {
        r = (r.0.min(q.0), r.1.min(q.1), r.2.max(q.0), r.3.max(q.1));
    }
    Some(r)
}

// ---------------------------------------------------------------------------
// 4. Document model (XML part)
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Default)]
pub struct SizeGeom {
    pub name: String,
    pub size_x: Option<f64>,
    pub size_y: Option<f64>,
    pub area_m2: Option<f64>,
    pub perimeter: Option<f64>,
    pub sew_area_m2: Option<f64>,
    pub sew_perimeter: Option<f64>,
}

#[derive(Clone, Debug, Default)]
pub struct SizeSum {
    pub name: String,
    pub sum_area_m2: Option<f64>,
    pub sum_perimeter: Option<f64>,
    pub sum_sew_area_m2: Option<f64>,
    pub sum_sew_perimeter: Option<f64>,
}

#[derive(Clone, Debug, Default)]
pub struct Nesting {
    pub rotation: String,
    pub rotation_deg: Option<f64>,
    pub tilt: String,
    pub tilt_deg: Option<f64>,
    pub shrink: String,
    pub opposite: String,
}

#[derive(Clone, Debug, Default)]
pub struct PdsPiece {
    pub name: String,
    pub code: String,
    pub unique: String,
    pub description: String,
    pub material: String,
    pub best_quality: String,
    pub quantity: u32,
    pub half: String,
    pub position: Option<(f64, f64)>,
    pub nesting: Nesting,
    pub sizes: Vec<SizeGeom>,
    pub notch_count: Option<u32>,
    pub t_notch_count: Option<u32>,
    pub internal_length_cm: Option<f64>,
}

impl PdsPiece {
    /// Piece shown as two mirrored halves in the marker / geometry given for the folded half.
    pub fn is_closed_half(&self) -> bool {
        self.half.trim().eq_ignore_ascii_case("CLOSE")
    }
    pub fn size(&self, name: &str) -> Option<&SizeGeom> {
        self.sizes.iter().find(|s| s.name == name)
    }
}

#[derive(Clone, Debug, Default)]
pub struct PdsStyle {
    pub name: String,
    pub version: String,
    pub date: String,
    pub units: String,
    pub square_units: String,
    pub filename: String,
    pub sizes: Vec<String>,
    pub size_table: Vec<SizeSum>,
    pub base_size: String,
    pub sizes_declared: Option<u32>,
    pub pieces_declared: Option<u32>,
}

#[derive(Clone, Debug, Default)]
pub struct MarkerOutline {
    pub cut: Vec<Pt>,
    pub sew: Option<Vec<Pt>>,
    pub notches: Vec<[Pt; 2]>,
    pub grain: Option<[Pt; 2]>,
    pub internal: Vec<Vec<Pt>>,
}

#[derive(Clone, Debug, Default)]
pub struct Marker {
    pub view_factor: Option<f64>,
    pub svg_width: String,
    pub svg_height: String,
    /// viewBox (min_x, min_y, width, height) in marker units
    pub view_box: (f64, f64, f64, f64),
    pub outlines: Vec<MarkerOutline>,
}

#[derive(Clone, Debug, Default)]
pub struct PdsDocument {
    pub style: PdsStyle,
    pub pieces: Vec<PdsPiece>,
    pub marker: Option<Marker>,
    pub warnings: Vec<String>,
}

fn parse_style(st: &Elem, warns: &mut Vec<String>) -> PdsStyle {
    let mut s = PdsStyle {
        name: st.child_text("NAME"),
        version: st.child_text("OPTITEX"),
        date: st.child_text("DATE"),
        filename: st.child_text("FILENAME"),
        sizes_declared: parse_u32(&st.child_text("SIZES")),
        pieces_declared: parse_u32(&st.child_text("PIECES")),
        ..Default::default()
    };
    if let Some(u) = st.child("UNITS") {
        s.units = u.attr("LINEAR").unwrap_or("").to_string();
        s.square_units = u.attr("SQUARE").unwrap_or("").to_string();
    }
    if s.units.is_empty() {
        s.units = "cm".into();
        warns.push("UNITS LINEAR missing; assuming cm".into());
    } else if !s.units.eq_ignore_ascii_case("cm") {
        warns.push(format!("UNITS LINEAR is '{}', not cm: GEOM_INFO is interpreted as cm without conversion", s.units));
    }
    if let Some(t) = st.child("SIZES_TABLE") {
        for z in t.children("SIZE").take(MAX_SIZES) {
            let nm = z.child_text("NAME");
            if nm.is_empty() {
                continue;
            }
            s.sizes.push(nm.clone());
            let g = |k: &str| parse_f(&z.child_text(k));
            s.size_table.push(SizeSum {
                name: nm,
                sum_area_m2: g("SUM_AREA"),
                sum_perimeter: g("SUM_PERIMETER"),
                sum_sew_area_m2: g("SUM_SEW_AREA"),
                sum_sew_perimeter: g("SUM_SEW_PERIMETER"),
            });
        }
        s.base_size = t.child_text("BASE_SIZE");
    }
    s
}

fn parse_piece(p: &Elem, warns: &mut Vec<String>) -> PdsPiece {
    let mut pc = PdsPiece {
        name: p.child_text("NAME"),
        code: p.child_text("CODE"),
        unique: p.child_text("UNIQUE"),
        description: p.child_text("DESCRIPTION"),
        material: p.child_text("MATERIAL"),
        best_quality: p.child_text("BEST_QUALITY"),
        half: p.child_text("HALF"),
        quantity: 1,
        ..Default::default()
    };
    let q = p.child_text("QUANTITY");
    if !q.is_empty() {
        match parse_u32(&q) {
            Some(v) => pc.quantity = v.min(9999),
            None => warns.push(format!("piece '{}': bad QUANTITY '{}', using 1", pc.name, q)),
        }
    }
    let pos = p.child_text("POSITION");
    if !pos.is_empty() {
        let mut x = None;
        let mut y = None;
        for t in pos.split_whitespace() {
            if let Some(v) = t.strip_prefix("X=").or_else(|| t.strip_prefix("x=")) {
                x = parse_f(v);
            } else if let Some(v) = t.strip_prefix("Y=").or_else(|| t.strip_prefix("y=")) {
                y = parse_f(v);
            }
        }
        if let (Some(x), Some(y)) = (x, y) {
            pc.position = Some((x, y));
        }
    }
    if let Some(n) = p.child("NESTING_ENABLES") {
        let g = |k: &str| n.attr(k).unwrap_or("").to_string();
        pc.nesting = Nesting {
            rotation: g("ROTATION"),
            rotation_deg: lead_num(&g("ROTATION")),
            tilt: g("TILT"),
            tilt_deg: lead_num(&g("TILT")),
            shrink: g("Shrink"),
            opposite: g("OPPOSITE"),
        };
    }
    for z in p.children("SIZE").take(MAX_SIZES) {
        let mut sg = SizeGeom { name: z.child_text("NAME"), ..Default::default() };
        if let Some(g) = z.child("GEOM_INFO") {
            let sname = sg.name.clone();
            let mut f = |k: &str| match g.attr(k) {
                None => None,
                Some(v) => {
                    let r = parse_f(v);
                    if r.is_none() {
                        warns.push(format!("piece '{}' size '{}': rejected non-finite/invalid {}='{}'", pc.name, sname, k, v));
                    }
                    r
                }
            };
            sg.size_x = f("SIZE_X");
            sg.size_y = f("SIZE_Y");
            sg.area_m2 = f("AREA");
            sg.perimeter = f("PERIMETER");
            sg.sew_area_m2 = f("SEW_AREA");
            sg.sew_perimeter = f("SEW_PERIMETER");
        }
        pc.sizes.push(sg);
    }
    if let Some(i) = p.child("INTERNALS") {
        if let Some(n) = i.child("NOTCH") {
            pc.notch_count = parse_u32(&n.child_text("COUNT"));
            if let Some(t) = n.child("T_NOTCH") {
                pc.t_notch_count = parse_u32(&t.child_text("COUNT"));
            }
        }
        if let Some(sl) = i.child("SUM_LENGTH") {
            pc.internal_length_cm = parse_f(&sl.child_text("LENGTH"));
        }
    }
    pc
}

// --- marker SVG ---

struct Shape {
    fill: String,
    from_polygon: bool,
    polys: Vec<Vec<Pt>>,
}

fn style_fill(e: &Elem) -> Option<String> {
    if let Some(st) = e.attr("style") {
        for part in st.split(';') {
            let mut it = part.splitn(2, ':');
            if let (Some(k), Some(v)) = (it.next(), it.next()) {
                if k.trim().eq_ignore_ascii_case("fill") {
                    return Some(v.trim().to_ascii_uppercase());
                }
            }
        }
    }
    e.attr("fill").map(|v| v.trim().to_ascii_uppercase())
}

#[derive(Default)]
struct SvgStats {
    curved: bool,
    bad_path: bool,
    odd_points: bool,
    total_points: usize,
    over_cap: bool,
}

fn collect_shapes(e: &Elem, inherited: &str, out: &mut Vec<Shape>, st: &mut SvgStats, depth: usize) {
    if depth > MAX_DEPTH {
        return;
    }
    for k in &e.kids {
        let fill = style_fill(k).unwrap_or_else(|| inherited.to_string());
        if k.is("g") {
            collect_shapes(k, &fill, out, st, depth + 1);
        } else if k.is("polygon") || k.is("polyline") {
            let (nums, bad) = numbers_in(k.attr("points").unwrap_or(""));
            if bad {
                st.bad_path = true;
            }
            if nums.len() % 2 == 1 {
                st.odd_points = true;
            }
            let pts: Vec<Pt> = nums.chunks_exact(2).map(|c| (c[0], c[1])).collect();
            st.total_points += pts.len();
            out.push(Shape { fill, from_polygon: k.is("polygon"), polys: vec![pts] });
        } else if k.is("path") {
            let subs = parse_path(k.attr("d").unwrap_or(""), &mut st.curved, &mut st.bad_path);
            st.total_points += subs.iter().map(|s| s.len()).sum::<usize>();
            out.push(Shape { fill, from_polygon: false, polys: subs });
        } else if k.is("line") {
            let g = |n: &str| k.attr(n).and_then(parse_f);
            if let (Some(a), Some(b), Some(c), Some(d)) = (g("x1"), g("y1"), g("x2"), g("y2")) {
                out.push(Shape { fill, from_polygon: false, polys: vec![vec![(a, b), (c, d)]] });
            }
        }
        if st.total_points > MAX_TOTAL_POINTS {
            st.over_cap = true;
            return;
        }
    }
}

fn pts_ok(p: &[Pt]) -> bool {
    p.len() <= MAX_POINTS_PER_POLY && p.iter().all(|q| q.0.is_finite() && q.1.is_finite() && q.0.abs() <= MAX_COORD && q.1.abs() <= MAX_COORD)
}

fn parse_marker(root: &Elem, warns: &mut Vec<String>) -> Option<Marker> {
    let mk = root.find_desc("MARKER")?;
    let view = mk.child("VIEW");
    let svg = match mk.find_desc("svg") {
        Some(s) => s,
        None => {
            warns.push("MARKER has no <svg>; no outlines available".into());
            return None;
        }
    };
    let mut m = Marker {
        view_factor: view.and_then(|v| v.attr("FACTOR")).and_then(parse_f),
        svg_width: svg.attr("width").unwrap_or("").to_string(),
        svg_height: svg.attr("height").unwrap_or("").to_string(),
        ..Default::default()
    };
    let mut vb = None;
    if let Some(v) = svg.attr("viewBox") {
        let (n, _) = numbers_in(v);
        if n.len() == 4 && n[2] > 0.0 && n[3] > 0.0 {
            vb = Some((n[0], n[1], n[2], n[3]));
        }
    }
    let mut shapes = Vec::new();
    let mut st = SvgStats::default();
    collect_shapes(svg, "", &mut shapes, &mut st, 0);
    if st.over_cap {
        warns.push(format!("marker SVG exceeds {} points; remaining shapes ignored", MAX_TOTAL_POINTS));
    }
    if st.curved {
        warns.push("marker SVG paths contain curve/arc commands; approximated by their end points".into());
    }
    if st.bad_path || st.odd_points {
        warns.push("marker SVG contained malformed/non-finite numbers; affected values were dropped".into());
    }
    let mut cur: Option<MarkerOutline> = None;
    let mut done: Vec<MarkerOutline> = Vec::new();
    let mut bg: Option<(f64, f64, f64, f64)> = None;
    let mut ignored_colors: Vec<String> = Vec::new();
    let mut dropped_polys = 0usize;
    let mut orphan = 0usize;
    let mut skipped_over_cap = 0usize;
    for sh in shapes {
        let fill = sh.fill.as_str();
        if fill == CUT_FILL && sh.from_polygon {
            if let Some(c) = cur.take() {
                done.push(c);
            }
            let pts = dedupe_closed(sh.polys.into_iter().next().unwrap_or_default());
            if pts.len() < 3 || !pts_ok(&pts) || poly_area(&pts) <= 0.0 {
                dropped_polys += 1;
                continue;
            }
            if done.len() >= MAX_OUTLINES {
                skipped_over_cap += 1;
                continue;
            }
            cur = Some(MarkerOutline { cut: pts, ..Default::default() });
        } else if fill == BACKGROUND_FILL {
            if bg.is_none() {
                bg = bbox(sh.polys.first().map(|p| p.as_slice()).unwrap_or(&[]));
            }
        } else if fill == SEW_FILL || fill == NOTCH_FILL || fill == GRAIN_FILL {
            let Some(o) = cur.as_mut() else {
                orphan += 1;
                continue;
            };
            for sub in sh.polys {
                if !pts_ok(&sub) {
                    dropped_polys += 1;
                    continue;
                }
                if fill == NOTCH_FILL {
                    if sub.len() >= 2 {
                        o.notches.push([sub[0], sub[sub.len() - 1]]);
                    }
                } else if fill == GRAIN_FILL {
                    if sub.len() >= 2 && o.grain.is_none() {
                        o.grain = Some([sub[0], sub[sub.len() - 1]]);
                    } else if sub.len() >= 2 {
                        o.internal.push(sub);
                    }
                } else {
                    let closed = dedupe_closed(sub.clone());
                    if closed.len() >= 3 && o.sew.is_none() && poly_area(&closed) > 0.0 {
                        o.sew = Some(closed);
                    } else if sub.len() >= 2 {
                        o.internal.push(sub);
                    }
                }
            }
        } else if !fill.is_empty() && !ignored_colors.iter().any(|c| c == fill) && ignored_colors.len() < 8 {
            ignored_colors.push(fill.to_string());
        }
    }
    if let Some(c) = cur.take() {
        done.push(c);
    }
    if dropped_polys > 0 {
        warns.push(format!("{} marker polygon(s) dropped (degenerate or out-of-range coordinates)", dropped_polys));
    }
    if orphan > 0 {
        warns.push(format!("{} marker element(s) appeared before any cut outline and were ignored", orphan));
    }
    if skipped_over_cap > 0 {
        warns.push(format!("marker has more than {} outlines; extra outlines ignored", MAX_OUTLINES));
    }
    if !ignored_colors.is_empty() {
        warns.push(format!("marker elements with unrecognised fill ignored: {}", ignored_colors.join(", ")));
    }
    m.view_box = match vb.or_else(|| bg.map(|b| (b.0, b.1, b.2 - b.0, b.3 - b.1))) {
        Some(v) => v,
        None => {
            // fall back to the extent of all cut polygons
            let mut all: Vec<Pt> = Vec::new();
            for o in &done {
                all.extend_from_slice(&o.cut);
            }
            match bbox(&all) {
                Some(b) => {
                    warns.push("marker viewBox missing; using the extent of the outlines".into());
                    (0.0, 0.0, b.2.max(1.0), b.3.max(1.0))
                }
                None => (0.0, 0.0, 1.0, 1.0),
            }
        }
    };
    m.outlines = done;
    Some(m)
}

/// Parse the readable parts of a PDS file (or of a bare extracted XML file).
pub fn parse_pds(bytes: &[u8]) -> Result<PdsDocument, String> {
    let (xml, truncated) = extract_xml_block(bytes)?;
    let mut warnings = Vec::new();
    if truncated {
        warnings.push("no closing </STYLE> found: the XML block is truncated; data after the cut-off is missing".into());
    }
    let root = parse_xml(&xml, &mut warnings)?;
    let st = root.find_desc("STYLE").ok_or("no <STYLE> element could be parsed")?;
    let style = parse_style(st, &mut warnings);
    let mut pieces = Vec::new();
    let mut n = 0;
    for p in st.children("PIECE") {
        n += 1;
        if n > MAX_PIECES {
            warnings.push(format!("more than {} pieces; extra pieces ignored", MAX_PIECES));
            break;
        }
        pieces.push(parse_piece(p, &mut warnings));
    }
    let marker = parse_marker(st, &mut warnings);
    if marker.is_none() {
        warnings.push("no <MARKER> found: only metadata is available, no outlines/pattern".into());
    }
    Ok(PdsDocument { style, pieces, marker, warnings })
}

/// Piece metadata only (no marker geometry).
pub fn import_pds_pieces(bytes: &[u8]) -> Result<Vec<PdsPiece>, String> {
    parse_pds(bytes).map(|d| d.pieces)
}

// ---------------------------------------------------------------------------
// 5. Matching outlines to pieces + scale derivation
// ---------------------------------------------------------------------------

struct OutM {
    a: f64, // longer bbox side (units)
    b: f64,
    w: f64,
    h: f64,
    per: f64,
    area: f64,
    sew_per: Option<f64>,
    sew_area: Option<f64>,
    sew_edges: Vec<f64>,
}

fn out_metrics(o: &MarkerOutline) -> OutM {
    let (x0, y0, x1, y1) = bbox(&o.cut).unwrap_or((0.0, 0.0, 0.0, 0.0));
    let (w, h) = (x1 - x0, y1 - y0);
    let sew_edges = o.sew.as_ref().map(|s| (0..s.len()).map(|i| dist(s[i], s[(i + 1) % s.len()])).collect()).unwrap_or_default();
    OutM {
        a: w.max(h),
        b: w.min(h),
        w,
        h,
        per: poly_perim(&o.cut),
        area: poly_area(&o.cut),
        sew_per: o.sew.as_ref().map(|s| poly_perim(s)),
        sew_area: o.sew.as_ref().map(|s| poly_area(s)),
        sew_edges,
    }
}

/// Expected metrics of a piece at the base size, expressed for what the marker shows
/// (for `HALF=CLOSE` pieces the marker shows the folded half: GEOM_INFO AREA/PERIMETER
/// are for the closed (full) piece).
struct Exp {
    a: Option<f64>,
    b: Option<f64>,
    x: Option<f64>,
    y: Option<f64>,
    per_variants: Vec<f64>,
    area_cm2: Option<f64>,
    sew_per: Option<f64>,
    sew_area_cm2: Option<f64>,
    closed: bool,
    cap: usize,
}

fn expectation(p: &PdsPiece, base: &str) -> Option<Exp> {
    let g = p.size(base)?;
    let closed = p.is_closed_half();
    let (a, b) = match (g.size_x, g.size_y) {
        (Some(x), Some(y)) => (Some(x.max(y)), Some(x.min(y))),
        _ => (None, None),
    };
    let per_variants = match g.perimeter {
        None => vec![],
        Some(pp) if closed => {
            // closed perimeter = 2 * (half perimeter - fold length); the fold is one of the bbox sides
            let mut v = Vec::new();
            for f in [g.size_x, g.size_y].into_iter().flatten() {
                v.push(pp / 2.0 + f);
            }
            if v.is_empty() {
                v.push(pp / 2.0);
            }
            v
        }
        Some(pp) => vec![pp],
    };
    let k = if closed { 0.5 } else { 1.0 };
    let area_cm2 = g.area_m2.map(|v| v * 1e4 * k).filter(|v| *v > 0.0);
    let sew_area_cm2 = g.sew_area_m2.map(|v| v * 1e4 * k).filter(|v| *v > 0.0);
    if a.is_none() && per_variants.is_empty() && area_cm2.is_none() {
        return None;
    }
    Some(Exp {
        a,
        b,
        x: g.size_x,
        y: g.size_y,
        per_variants,
        area_cm2,
        sew_per: g.sew_perimeter,
        sew_area_cm2,
        closed,
        cap: if closed { 2 } else { 1 },
    })
}

fn rel(x: f64, y: f64) -> f64 {
    (x - y).abs() / y.abs().max(1e-9)
}

#[derive(Clone, Copy, Debug, Default)]
struct Comp {
    dims: Option<f64>,
    per: Option<f64>,
    area: Option<f64>,
}

fn comp(o: &OutM, e: &Exp, s: f64) -> Comp {
    let dims = match (e.a, e.b) {
        (Some(a), Some(b)) => Some(rel(o.a / s, a).max(rel(o.b / s, b))),
        _ => None,
    };
    let per = e.per_variants.iter().map(|&p| rel(o.per / s, p)).fold(None, |m: Option<f64>, v| Some(m.map_or(v, |m| m.min(v))));
    let area = e.area_cm2.map(|a| rel(o.area / (s * s), a));
    Comp { dims, per, area }
}

fn cost(c: &Comp) -> f64 {
    let mut num = 0.0;
    let mut den = 0.0;
    if let Some(v) = c.dims {
        num += 2.0 * v;
        den += 2.0;
    }
    if let Some(v) = c.per {
        num += v;
        den += 1.0;
    }
    if let Some(v) = c.area {
        num += v;
        den += 1.0;
    }
    if den == 0.0 { f64::INFINITY } else { num / den }
}

fn eval_scale(os: &[OutM], es: &[Option<Exp>], s: f64) -> f64 {
    let mut tot = 0.0;
    for o in os {
        let mut best: f64 = 0.3;
        for e in es.iter().flatten() {
            best = best.min(cost(&comp(o, e, s)));
        }
        tot += best;
    }
    tot
}

#[derive(Clone, Debug)]
struct Assign {
    piece: usize,
    cost: f64,
    comp: Comp,
    extra: bool,
}

fn assign(os: &[OutM], es: &[Option<Exp>], s: f64) -> Vec<Option<Assign>> {
    let mut trip: Vec<(i64, usize, usize, f64, Comp)> = Vec::new();
    for (oi, o) in os.iter().enumerate() {
        for (pj, e) in es.iter().enumerate() {
            if let Some(e) = e {
                let c = comp(o, e, s);
                let k = cost(&c);
                if k <= MATCH_MAX_COST {
                    trip.push(((k * 1000.0).round() as i64, oi, pj, k, c));
                }
            }
        }
    }
    trip.sort_by(|x, y| (x.0, x.1, x.2).cmp(&(y.0, y.1, y.2)));
    let mut res: Vec<Option<Assign>> = vec![None; os.len()];
    let mut used = vec![0usize; es.len()];
    for t in &trip {
        let cap = es[t.2].as_ref().map(|e| e.cap).unwrap_or(1);
        if res[t.1].is_none() && used[t.2] < cap {
            used[t.2] += 1;
            res[t.1] = Some(Assign { piece: t.2, cost: t.3, comp: t.4, extra: false });
        }
    }
    // leftovers: best piece regardless of capacity (e.g. quantity > 1 laid out several times)
    for t in &trip {
        if res[t.1].is_none() {
            res[t.1] = Some(Assign { piece: t.2, cost: t.3, comp: t.4, extra: true });
        }
    }
    res
}

struct ScaleFit {
    s: f64,
    assumed: bool,
    rms_rel: Option<f64>,
    pairs: usize,
}

fn fit_scale(os: &[OutM], es: &[Option<Exp>], warns: &mut Vec<String>) -> ScaleFit {
    // 1. vote for plausible ratios from shape-consistent (a, b) pairs
    let mut votes: HashMap<i64, u32> = HashMap::new();
    for o in os {
        if o.b <= 0.0 {
            continue;
        }
        for e in es.iter().flatten() {
            if let (Some(a), Some(b)) = (e.a, e.b) {
                if a > 1e-9 && b > 1e-9 {
                    let (r1, r2) = (o.a / a, o.b / b);
                    if rel(r1, r2) < 0.03 && r1 > 0.0 {
                        *votes.entry((r1.ln() / 0.01).round() as i64).or_insert(0) += 1;
                    }
                }
            }
        }
    }
    let mut keys: Vec<(u32, i64)> = votes
        .iter()
        .map(|(&k, &v)| (v + votes.get(&(k - 1)).copied().unwrap_or(0) + votes.get(&(k + 1)).copied().unwrap_or(0), k))
        .collect();
    keys.sort_by(|x, y| y.cmp(x));
    let mut best: Option<(f64, f64)> = None; // (score, scale)
    for (_, k) in keys.iter().take(8) {
        let s = (*k as f64 * 0.01).exp();
        if !(1e-3..=1e6).contains(&s) {
            continue;
        }
        let sc = eval_scale(os, es, s);
        if best.map_or(true, |b| sc < b.0 - 1e-12) {
            best = Some((sc, s));
        }
    }
    let (mut s, assumed) = match best {
        Some((_, s)) => (s, false),
        None => {
            warns.push("could not derive the marker unit scale from GEOM_INFO (no shape-consistent outline/piece pair); assuming 100 marker units per cm (the value observed on sample files)".into());
            (100.0, true)
        }
    };
    if assumed {
        return ScaleFit { s, assumed, rms_rel: None, pairs: 0 };
    }
    // 2. least-squares refinement on the matched pairs: minimise sum (u - s*c)^2, with trimming of
    // pairs that disagree by >3% (e.g. folded pieces whose fold length is unknown). Perimeters of
    // folded (HALF=CLOSE) pieces are not used because the fold length is not in GEOM_INFO.
    let mut rms = None;
    let mut npairs = 0;
    for _ in 0..4 {
        let asg = assign(os, es, s);
        let mut pairs: Vec<(f64, f64)> = Vec::new();
        for (oi, a) in asg.iter().enumerate() {
            let Some(a) = a else { continue };
            if a.cost > 0.08 {
                continue;
            }
            let (o, Some(e)) = (&os[oi], es[a.piece].as_ref()) else { continue };
            if let (Some(ea), Some(eb)) = (e.a, e.b) {
                pairs.push((o.a, ea));
                pairs.push((o.b, eb));
            }
            if !e.closed {
                if let Some(&pv) = e.per_variants.first() {
                    pairs.push((o.per, pv));
                }
            }
        }
        pairs.retain(|(u, c)| *c > 1e-9 && rel(u / s, *c) <= 0.03);
        let (mut suc, mut scc) = (0.0, 0.0);
        for (u, c) in &pairs {
            suc += u * c;
            scc += c * c;
        }
        if pairs.is_empty() || scc <= 0.0 {
            break;
        }
        let ns = suc / scc;
        if !ns.is_finite() || ns <= 0.0 {
            break;
        }
        s = ns;
        npairs = pairs.len();
        let ms: f64 = pairs.iter().map(|(u, c)| rel(u / s, *c).powi(2)).sum::<f64>() / pairs.len() as f64;
        rms = Some(ms.sqrt());
    }
    ScaleFit { s, assumed: false, rms_rel: rms, pairs: npairs }
}

/// Confidence from the worst of dims / perimeter error. For folded (HALF=CLOSE) pieces the
/// perimeter depends on the unknown fold length, so area (error halved: area ~ scale^2) is used.
fn confidence(c: &Comp, closed: bool) -> &'static str {
    let per = if closed { c.area.map(|a| a * 0.5) } else { c.per };
    let w = [c.dims, per].iter().flatten().fold(0.0f64, |m, v| m.max(*v));
    if c.dims.is_none() && per.is_none() {
        return "low";
    }
    if w <= 0.02 {
        "high"
    } else if w <= 0.05 {
        "medium"
    } else {
        "low"
    }
}

// ---------------------------------------------------------------------------
// 6. Pattern construction
// ---------------------------------------------------------------------------

fn ccw(mut p: Vec<V2>) -> Vec<V2> {
    if signed_area(&p) < 0.0 {
        p.reverse();
    }
    p
}

fn seg_dist(p: V2, a: V2, b: V2) -> (f64, f64) {
    let ab = b - a;
    let l2 = ab.dot(ab);
    let t = if l2 < 1e-18 { 0.0 } else { ((p - a).dot(ab) / l2).clamp(0.0, 1.0) };
    (p.dist(a + ab * t), t)
}

fn poly_dist(p: V2, poly: &[V2]) -> f64 {
    let n = poly.len();
    (0..n).map(|i| seg_dist(p, poly[i], poly[(i + 1) % n]).0).fold(f64::INFINITY, f64::min)
}

/// Uniform seam allowance (length-weighted median of sew-edge-to-cut distances) and per-edge
/// overrides where an edge deviates by more than 2 mm (e.g. fold edges with 0).
fn seam_allowance(sew: &[V2], cut: &[V2]) -> (f64, Vec<Option<f64>>) {
    let n = sew.len();
    let mut d: Vec<(f64, f64)> = Vec::new(); // (dist, len)
    let mut per_edge = vec![0.0; n];
    for i in 0..n {
        let (a, b) = (sew[i], sew[(i + 1) % n]);
        let mid = a.lerp(b, 0.5);
        per_edge[i] = poly_dist(mid, cut);
        let l = a.dist(b);
        if l > 1e-6 {
            d.push((per_edge[i], l));
        }
    }
    d.sort_by(|x, y| x.0.partial_cmp(&y.0).unwrap_or(std::cmp::Ordering::Equal));
    let tot: f64 = d.iter().map(|x| x.1).sum();
    let mut acc = 0.0;
    let mut med = 0.0;
    for (v, l) in &d {
        acc += l;
        if acc >= tot / 2.0 {
            med = *v;
            break;
        }
    }
    let med = ((med * 100.0).round() / 100.0).clamp(0.0, 10.0);
    let ov = per_edge
        .iter()
        .map(|&v| if (v - med).abs() > 0.2 { Some(((v * 100.0).round() / 100.0).clamp(0.0, 10.0)) } else { None })
        .collect();
    (med, ov)
}

struct BuiltPiece {
    piece: Piece,
    sa: f64,
    origin_cm: (f64, f64),
}

fn build_piece(name: &str, o: &MarkerOutline, s: f64, vb_maxy: f64, meta: Option<&PdsPiece>) -> BuiltPiece {
    let (x0, _y0, _x1, y1) = bbox(&o.cut).unwrap_or((0.0, 0.0, 0.0, 0.0));
    // marker is y-down: flip so the bbox min sits at (0,0) y-up cm
    let tf = |p: Pt| v2((p.0 - x0) / s, (y1 - p.1) / s);
    let cut: Vec<V2> = ccw(o.cut.iter().map(|&p| tf(p)).collect());
    let sew: Option<Vec<V2>> = o.sew.as_ref().map(|sp| ccw(sp.iter().map(|&p| tf(p)).collect()));
    let base: &Vec<V2> = sew.as_ref().unwrap_or(&cut);
    let (sa, ov) = match &sew {
        Some(sw) => seam_allowance(sw, &cut),
        None => (0.0, vec![None; base.len()]),
    };
    let nodes: Vec<Node> = base
        .iter()
        .enumerate()
        .map(|(i, p)| {
            let mut n = Node::corner(p.x, p.y, &format!("e{}", i));
            n.sa = ov.get(i).copied().flatten();
            n
        })
        .collect();
    let mut notches = Vec::new();
    for nt in &o.notches {
        let (p0, p1) = (tf(nt[0]), tf(nt[1]));
        let (d0, d1) = (poly_dist(p0, base), poly_dist(p1, base));
        let p = if d0 <= d1 { p0 } else { p1 };
        let n = base.len();
        let mut best = (f64::INFINITY, 0usize, 0.0);
        for i in 0..n {
            let (d, t) = seg_dist(p, base[i], base[(i + 1) % n]);
            if d < best.0 {
                best = (d, i, t);
            }
        }
        notches.push(Notch { node: best.1, t: best.2, kind: "slit".into() });
    }
    let grain = match &o.grain {
        Some(g) => (tf(g[0]), tf(g[1])),
        None => (v2(0.0, 0.0), v2(0.0, -10.0)),
    };
    let internal: Vec<Vec<V2>> = o.internal.iter().map(|l| l.iter().map(|&p| tf(p)).collect()).collect();
    let (qty, mirror, material) = match meta {
        Some(m) => {
            let mir = m.quantity >= 2 && m.quantity % 2 == 0 && !m.nesting.opposite.is_empty() && !m.nesting.opposite.eq_ignore_ascii_case("none");
            (m.quantity.clamp(1, 99), mir, if m.material.is_empty() { "SELF".to_string() } else { m.material.clone() })
        }
        None => (1, false, "SELF".to_string()),
    };
    BuiltPiece {
        piece: Piece {
            name: name.to_string(),
            zone: "imported".into(),
            nodes,
            grain,
            notches,
            darts: vec![],
            internal,
            drills: vec![],
            sa,
            mirror,
            qty,
            material,
        },
        sa,
        origin_cm: (x0 / s, (vb_maxy - y1) / s),
    }
}

// ---------------------------------------------------------------------------
// 7. Public entry: JSON
// ---------------------------------------------------------------------------

fn jn(x: f64) -> Json {
    Json::Num(if x.is_finite() { x } else { 0.0 })
}
fn jo(x: Option<f64>) -> Json {
    match x {
        Some(v) if v.is_finite() => Json::Num(v),
        _ => Json::Null,
    }
}
fn jpt(p: Pt) -> Json {
    Json::nums(&[p.0, p.1])
}
fn jpoly(p: &[Pt]) -> Json {
    Json::Arr(p.iter().map(|&q| jpt(q)).collect())
}
fn jstrs(v: &[String]) -> Json {
    Json::Arr(v.iter().map(|s| Json::str(s)).collect())
}
fn pct(x: Option<f64>) -> Json {
    jo(x.map(|v| (v * 1e5).round() / 1e5))
}

fn piece_json(p: &PdsPiece) -> Json {
    let n = &p.nesting;
    let nest = Json::obj()
        .set("rotation", Json::str(&n.rotation))
        .set("rotation_deg", jo(n.rotation_deg))
        .set("tilt", Json::str(&n.tilt))
        .set("tilt_deg", jo(n.tilt_deg))
        .set("shrink", Json::str(&n.shrink))
        .set("opposite", Json::str(&n.opposite));
    let sizes = Json::Arr(
        p.sizes
            .iter()
            .map(|s| {
                Json::obj()
                    .set("name", Json::str(&s.name))
                    .set("size_x", jo(s.size_x))
                    .set("size_y", jo(s.size_y))
                    .set("area_m2", jo(s.area_m2))
                    .set("perimeter", jo(s.perimeter))
                    .set("sew_area_m2", jo(s.sew_area_m2))
                    .set("sew_perimeter", jo(s.sew_perimeter))
            })
            .collect(),
    );
    Json::obj()
        .set("name", Json::str(&p.name))
        .set("code", Json::str(&p.code))
        .set("unique", Json::str(&p.unique))
        .set("description", Json::str(&p.description))
        .set("material", Json::str(&p.material))
        .set("best_quality", Json::str(&p.best_quality))
        .set("quantity", jn(p.quantity as f64))
        .set("half", Json::str(&p.half))
        .set("position", match p.position { Some((x, y)) => Json::obj().set("x", jn(x)).set("y", jn(y)), None => Json::Null })
        .set("nesting", nest)
        .set("sizes", sizes)
        .set("notch_count", jo(p.notch_count.map(|v| v as f64)))
        .set("t_notch_count", jo(p.t_notch_count.map(|v| v as f64)))
        .set("internal_length_cm", jo(p.internal_length_cm))
}

/// One row of the matching diagnostics (also exposed for tests / UIs).
#[derive(Clone, Debug)]
pub struct MatchInfo {
    pub outline: usize,
    pub piece: Option<usize>,
    pub piece_name: Option<String>,
    pub cost: f64,
    pub dims_err: Option<f64>,
    pub perimeter_err: Option<f64>,
    pub area_err: Option<f64>,
    pub sew_perimeter_err: Option<f64>,
    pub sew_area_err: Option<f64>,
    pub confidence: &'static str,
    pub rotated_90: bool,
    /// piece is a folded half (HALF=CLOSE): perimeter errors are only indicative (fold length unknown)
    pub closed_half: bool,
    pub extra_instance: bool,
    pub ambiguous_with: Vec<String>,
    pub size_cm: (f64, f64),
}

pub struct Analysis {
    pub doc: PdsDocument,
    pub marker_size: String,
    pub units_per_cm: f64,
    pub matches: Vec<MatchInfo>,
    pub json: Json,
}

/// Full import: parse + scale derivation + matching + Pattern. See module docs.
pub fn import_pds(bytes: &[u8]) -> Result<Json, String> {
    analyze_pds(bytes).map(|a| a.json)
}

pub fn analyze_pds(bytes: &[u8]) -> Result<Analysis, String> {
    let doc = parse_pds(bytes)?;
    let mut warns: Vec<String> = Vec::new();
    warns.push(PREVIEW_WARNING.to_string());
    warns.push("the binary part of the PDS is not read; only the clear-text XML summary and marker preview are used".into());
    warns.extend(doc.warnings.iter().cloned());
    let st = &doc.style;

    // base size
    let mut base = st.base_size.clone();
    if base.is_empty() {
        base = st.sizes.first().cloned().or_else(|| doc.pieces.iter().find_map(|p| p.sizes.first().map(|s| s.name.clone()))).unwrap_or_default();
        warns.push(format!("BASE_SIZE missing; using '{}'", base));
    } else if !st.sizes.is_empty() && !st.sizes.contains(&base) {
        warns.push(format!("BASE_SIZE '{}' is not in SIZES_TABLE", base));
    }
    if let Some(n) = st.sizes_declared {
        if n as usize != st.sizes.len() {
            warns.push(format!("SIZES says {} but SIZES_TABLE lists {}", n, st.sizes.len()));
        }
    }
    if let Some(n) = st.pieces_declared {
        if n as usize != doc.pieces.len() {
            warns.push(format!("PIECES says {} but {} PIECE elements were parsed", n, doc.pieces.len()));
        }
    }
    // internal consistency: SUM_* == sum(quantity * piece value) at the base size
    let mut sums = Json::Null;
    if let Some(row) = st.size_table.iter().find(|r| r.name == base) {
        let mut sa = 0.0;
        let mut sp = 0.0;
        let mut complete = !doc.pieces.is_empty();
        for p in &doc.pieces {
            match p.size(&base).and_then(|g| Some((g.area_m2?, g.perimeter?))) {
                Some((a, pp)) => {
                    sa += a * p.quantity as f64;
                    sp += pp * p.quantity as f64;
                }
                None => complete = false,
            }
        }
        let ea = row.sum_area_m2.filter(|_| complete).map(|d| rel(sa, d));
        let ep = row.sum_perimeter.filter(|_| complete).map(|d| rel(sp, d));
        for (lbl, e) in [("SUM_AREA", ea), ("SUM_PERIMETER", ep)] {
            if let Some(e) = e {
                if e > 0.01 {
                    warns.push(format!("{} of SIZES_TABLE differs {:.1}% from sum(quantity*piece value): XML may be incomplete", lbl, e * 100.0));
                }
            }
        }
        sums = Json::obj()
            .set("size", Json::str(&base))
            .set("sum_area_m2_declared", jo(row.sum_area_m2))
            .set("sum_area_m2_computed", jn(sa))
            .set("sum_area_rel_err", pct(ea))
            .set("sum_perimeter_declared", jo(row.sum_perimeter))
            .set("sum_perimeter_computed", jn(sp))
            .set("sum_perimeter_rel_err", pct(ep));
    }

    let style_json = Json::obj()
        .set("name", Json::str(&st.name))
        .set("version", Json::str(&st.version))
        .set("date", Json::str(&st.date))
        .set("units", Json::str(&st.units))
        .set("filename", Json::str(&st.filename))
        .set("sizes", jstrs(&st.sizes))
        .set("base_size", Json::str(&base))
        .set("pieces_count", jn(doc.pieces.len() as f64))
        .set("pieces_declared", jo(st.pieces_declared.map(|v| v as f64)))
        .set("sizes_declared", jo(st.sizes_declared.map(|v| v as f64)))
        .set(
            "size_table",
            Json::Arr(
                st.size_table
                    .iter()
                    .map(|r| {
                        Json::obj()
                            .set("name", Json::str(&r.name))
                            .set("sum_area_m2", jo(r.sum_area_m2))
                            .set("sum_perimeter", jo(r.sum_perimeter))
                            .set("sum_sew_area_m2", jo(r.sum_sew_area_m2))
                            .set("sum_sew_perimeter", jo(r.sum_sew_perimeter))
                    })
                    .collect(),
            ),
        )
        .set("base_sums_check", sums);

    // ---- marker / matching ----
    let empty = Marker::default();
    let mk = doc.marker.as_ref().unwrap_or(&empty);
    let os: Vec<OutM> = mk.outlines.iter().map(out_metrics).collect();
    // The marker need not show the BASE size (e.g. base L but marker laid out in M), so every
    // size is tried; the one that explains the outlines best wins (ties favour the base size).
    let mut cand_sizes: Vec<String> = vec![base.clone()];
    for n in st.sizes.iter().chain(doc.pieces.iter().flat_map(|p| p.sizes.iter().map(|z| &z.name))) {
        if !n.is_empty() && !cand_sizes.contains(n) && cand_sizes.len() <= MAX_SIZES {
            cand_sizes.push(n.clone());
        }
    }
    let mut chosen: Option<(f64, String, Vec<Option<Exp>>, ScaleFit, Vec<Option<Assign>>, Vec<String>)> = None;
    if !os.is_empty() {
        for sz in &cand_sizes {
            let es: Vec<Option<Exp>> = doc.pieces.iter().map(|p| expectation(p, sz)).collect();
            if es.iter().all(|e| e.is_none()) {
                continue;
            }
            let mut w = Vec::new();
            let fit = fit_scale(&os, &es, &mut w);
            let asg = assign(&os, &es, fit.s);
            let score: f64 = asg.iter().map(|a| a.as_ref().map_or(0.3, |a| a.cost)).sum::<f64>() + if fit.assumed { 1e3 } else { 0.0 };
            if chosen.as_ref().map_or(true, |c| score < c.0 - 1e-4) {
                chosen = Some((score, sz.clone(), es, fit, asg, w));
            }
        }
    }
    let marker_size;
    let es: Vec<Option<Exp>>;
    let mut fit = ScaleFit { s: 100.0, assumed: true, rms_rel: None, pairs: 0 };
    let mut assigns: Vec<Option<Assign>> = vec![None; os.len()];
    match chosen {
        Some((_, sz, e, f, a, w)) => {
            marker_size = sz;
            es = e;
            fit = f;
            assigns = a;
            warns.extend(w);
        }
        None => {
            marker_size = base.clone();
            es = doc.pieces.iter().map(|p| expectation(p, &base)).collect();
            if doc.marker.is_some() && os.is_empty() {
                warns.push("marker contains no cut outlines".into());
            }
        }
    }
    if !os.is_empty() && marker_size != base {
        warns.push(format!("the marker shows size '{}' (best match to GEOM_INFO), not BASE_SIZE '{}'; the pattern is imported at '{}'", marker_size, base, marker_size));
    }
    for (p, e) in doc.pieces.iter().zip(&es) {
        if e.is_none() {
            warns.push(format!("piece '{}' has no usable GEOM_INFO at size '{}': cannot be matched", p.name, marker_size));
        }
    }
    let s = fit.s;

    // naming: instance counter per piece
    let mut inst_count: Vec<usize> = vec![0; doc.pieces.len()];
    let mut names: Vec<String> = Vec::new();
    let mut matches: Vec<MatchInfo> = Vec::new();
    let mut unmatched = 0usize;
    for (oi, a) in assigns.iter().enumerate() {
        let o = &os[oi];
        match a {
            Some(a) => {
                let p = &doc.pieces[a.piece];
                inst_count[a.piece] += 1;
                let nm = if inst_count[a.piece] == 1 { p.name.clone() } else { format!("{} ({})", p.name, inst_count[a.piece]) };
                names.push(nm);
                let e = es[a.piece].as_ref();
                let sew_per_err = match (e.and_then(|e| e.sew_per), o.sew_per, e.map(|e| e.closed)) {
                    (Some(sp), Some(osp), Some(true)) => {
                        // closed: full = 2*(half - fold); fold edge is one of the sew polygon edges
                        o.sew_edges.iter().map(|f| rel(2.0 * (osp / s - f / s), sp)).fold(None, |m: Option<f64>, v| Some(m.map_or(v, |m| m.min(v))))
                    }
                    (Some(sp), Some(osp), _) => Some(rel(osp / s, sp)),
                    _ => None,
                };
                let sew_area_err = match (e.and_then(|e| e.sew_area_cm2), o.sew_area) {
                    (Some(ea), Some(oa)) => Some(rel(oa / (s * s), ea)),
                    _ => None,
                };
                let rotated = match e.and_then(|e| e.x.zip(e.y)) {
                    Some((x, y)) => (x - y).abs() / x.max(y).max(1e-9) > 0.02 && ((o.w >= o.h) != (x >= y)),
                    None => false,
                };
                let amb: Vec<String> = es
                    .iter()
                    .enumerate()
                    .filter(|(j, e)| *j != a.piece && e.is_some())
                    .filter(|(j, e)| {
                        let c = cost(&comp(o, e.as_ref().unwrap(), s));
                        c <= a.cost + 0.003 && doc.pieces[*j].name != p.name
                    })
                    .map(|(j, _)| doc.pieces[j].name.clone())
                    .collect();
                let conf = confidence(&a.comp, e.map_or(false, |e| e.closed));
                if conf != "high" {
                    warns.push(format!(
                        "outline {} -> '{}': {} confidence match (dims err {:.1}%, perimeter err {:.1}%)",
                        oi,
                        p.name,
                        conf,
                        a.comp.dims.unwrap_or(0.0) * 100.0,
                        a.comp.per.unwrap_or(0.0) * 100.0
                    ));
                }
                if !amb.is_empty() {
                    warns.push(format!("outline {} -> '{}' is indistinguishable by GEOM_INFO from: {}; assignment among them is arbitrary", oi, p.name, amb.join(", ")));
                }
                matches.push(MatchInfo {
                    outline: oi,
                    piece: Some(a.piece),
                    piece_name: Some(p.name.clone()),
                    cost: a.cost,
                    dims_err: a.comp.dims,
                    perimeter_err: a.comp.per,
                    area_err: a.comp.area,
                    sew_perimeter_err: sew_per_err,
                    sew_area_err,
                    confidence: conf,
                    rotated_90: rotated,
                    closed_half: e.map_or(false, |e| e.closed),
                    extra_instance: a.extra,
                    ambiguous_with: amb,
                    size_cm: (o.w / s, o.h / s),
                });
            }
            None => {
                unmatched += 1;
                names.push(format!("OUTLINE_{}", oi));
                warns.push(format!("outline {} ({:.1} x {:.1} cm) matches no piece in GEOM_INFO (e.g. a marker ruler/label); imported unnamed", oi, o.w / s, o.h / s));
                matches.push(MatchInfo {
                    outline: oi,
                    piece: None,
                    piece_name: None,
                    cost: f64::INFINITY,
                    dims_err: None,
                    perimeter_err: None,
                    area_err: None,
                    sew_perimeter_err: None,
                    sew_area_err: None,
                    confidence: "none",
                    rotated_90: false,
                    closed_half: false,
                    extra_instance: false,
                    ambiguous_with: vec![],
                    size_cm: (o.w / s, o.h / s),
                });
            }
        }
    }
    if !mk.outlines.is_empty() {
        for (j, p) in doc.pieces.iter().enumerate() {
            if inst_count[j] == 0 && es[j].is_some() {
                warns.push(format!("piece '{}' has no matching outline in the marker", p.name));
            }
        }
    }
    let _ = unmatched;
    let n_extra = matches.iter().filter(|m| m.extra_instance).count();
    if n_extra > 0 {
        warns.push(format!("{} outline(s) are additional instances of an already-matched piece (piece laid out more than expected)", n_extra));
    }
    if fit.assumed && !os.is_empty() {
        warns.push("unit scale is ASSUMED, not validated against GEOM_INFO".into());
    } else if let Some(r) = fit.rms_rel {
        if r > 0.02 {
            warns.push(format!("unit-scale fit residual is {:.1}% (>2%): marker and GEOM_INFO agree poorly", r * 100.0));
        }
    }

    // ---- pattern ----
    let vb = mk.view_box;
    let vb_maxy = vb.1 + vb.3;
    let mut pat_pieces: Vec<Piece> = Vec::new();
    let mut built: Vec<BuiltPiece> = Vec::new();
    for (oi, o) in mk.outlines.iter().enumerate() {
        let meta = assigns[oi].as_ref().map(|a| &doc.pieces[a.piece]);
        let b = build_piece(&names[oi], o, s, vb_maxy, meta);
        pat_pieces.push(b.piece.clone());
        built.push(b);
    }
    let pattern = Pattern {
        style: if st.name.is_empty() { "Imported PDS".into() } else { st.name.clone() },
        size: marker_size.clone(),
        garment: "imported".into(),
        pieces: pat_pieces,
        seams: vec![],
    };

    // ---- JSON assembly ----
    let outlines_json: Vec<Json> = mk
        .outlines
        .iter()
        .enumerate()
        .map(|(oi, o)| {
            let m = &matches[oi];
            let mut mj = Json::obj()
                .set("confidence", Json::str(m.confidence))
                .set("size_cm", Json::nums(&[m.size_cm.0, m.size_cm.1]))
                .set("rotated_90", Json::Bool(m.rotated_90))
                .set("closed_half", Json::Bool(m.closed_half))
                .set("extra_instance", Json::Bool(m.extra_instance));
            if m.piece.is_some() {
                mj = mj
                    .set("cost", jn(m.cost))
                    .set("dims_err", pct(m.dims_err))
                    .set("perimeter_err", pct(m.perimeter_err))
                    .set("area_err", pct(m.area_err))
                    .set("sew_perimeter_err", pct(m.sew_perimeter_err))
                    .set("sew_area_err", pct(m.sew_area_err))
                    .set("ambiguous_with", jstrs(&m.ambiguous_with));
            }
            Json::obj()
                .set("index", jn(oi as f64))
                .set("piece", match &m.piece_name { Some(n) => Json::str(n), None => Json::Null })
                .set("piece_index", jo(m.piece.map(|v| v as f64)))
                .set("name", Json::str(&names[oi]))
                .set("cut", jpoly(&o.cut))
                .set("sew", match &o.sew { Some(s) => jpoly(s), None => Json::Null })
                .set("notches", Json::Arr(o.notches.iter().map(|n| Json::Arr(vec![jpt(n[0]), jpt(n[1])])).collect()))
                .set("grain", match &o.grain { Some(g) => Json::Arr(vec![jpt(g[0]), jpt(g[1])]), None => Json::Null })
                .set("internal", Json::Arr(o.internal.iter().map(|l| jpoly(l)).collect()))
                .set("seam_allowance_cm", jn(built[oi].sa))
                .set("origin_cm", Json::nums(&[built[oi].origin_cm.0, built[oi].origin_cm.1]))
                .set("match", mj)
        })
        .collect();

    let pieces_json: Vec<Json> = doc
        .pieces
        .iter()
        .enumerate()
        .map(|(j, p)| {
            let ms: Vec<&MatchInfo> = matches.iter().filter(|m| m.piece == Some(j)).collect();
            let worst = ms.iter().filter_map(|m| m.perimeter_err).fold(None, |a: Option<f64>, v| Some(a.map_or(v, |a| a.max(v))));
            let conf = if ms.is_empty() {
                "none"
            } else if ms.iter().all(|m| m.confidence == "high") {
                "high"
            } else if ms.iter().any(|m| m.confidence == "low") {
                "low"
            } else {
                "medium"
            };
            let mnotch: usize = ms.iter().map(|m| mk.outlines[m.outline].notches.len()).sum();
            piece_json(p)
                .set("outlines", Json::Arr(ms.iter().map(|m| jn(m.outline as f64)).collect()))
                .set("match_confidence", Json::str(conf))
                .set("worst_perimeter_err", pct(worst))
                .set("marker_notch_count", jn(mnotch as f64))
        })
        .collect();

    let marker_json = Json::obj()
        .set("width", jn(vb.2))
        .set("height", jn(vb.3))
        .set("view_box", Json::nums(&[vb.0, vb.1, vb.2, vb.3]))
        .set("width_cm", jn(vb.2 / s))
        .set("height_cm", jn(vb.3 / s))
        .set("units_per_cm", jn(s))
        .set("size", Json::str(&marker_size))
        .set("units", Json::str("marker units (svg integer coordinates, y down)"))
        .set(
            "scale_fit",
            Json::obj()
                .set("method", Json::str("least squares of outline bbox/perimeter vs GEOM_INFO at base size"))
                .set("assumed", Json::Bool(fit.assumed))
                .set("rms_rel_err", pct(fit.rms_rel))
                .set("pairs", jn(fit.pairs as f64)),
        )
        .set("view_factor", jo(mk.view_factor))
        .set("svg_width", Json::str(&mk.svg_width))
        .set("svg_height", Json::str(&mk.svg_height))
        .set("outlines", Json::Arr(outlines_json));

    let json = Json::obj()
        .set("style", style_json)
        .set("pieces", Json::Arr(pieces_json))
        .set("marker", marker_json)
        .set("pattern", pattern.to_json())
        .set("warnings", jstrs(&warns))
        .set("geometry_source", Json::str("marker_svg_preview"));
    Ok(Analysis { doc, marker_size, units_per_cm: s, matches, json })
}

// ---------------------------------------------------------------------------
// 8. Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn samples_dir() -> String {
        std::env::var("PDS_SAMPLES_DIR").unwrap_or_else(|_| "/home/claude/samples".into())
    }
    fn sample(name: &str) -> Option<Vec<u8>> {
        match std::fs::read(format!("{}/{}", samples_dir(), name)) {
            Ok(b) => Some(b),
            Err(_) => {
                eprintln!("SKIP: sample {} not found in {}", name, samples_dir());
                None
            }
        }
    }
    const PANT: &str = "pant_1074664.PDS";
    const SHIRT: &str = "shirt_1078375_CORRUPTED_UPLOAD.PDS";

    fn table(a: &Analysis) -> String {
        let mut s = String::new();
        s.push_str(&format!("units_per_cm = {:.4}\n", a.units_per_cm));
        s.push_str("idx piece                  dims(cm)         cost   dims%  perim%  area%  sewP%  sewA%  conf   rot amb\n");
        for m in &a.matches {
            s.push_str(&format!(
                "{:>3} {:<22} {:>6.2}x{:<7.2} {:>6.4} {:>6.2} {:>7.2} {:>6.2} {:>6.2} {:>6.2}  {:<6} {:<3} {}\n",
                m.outline,
                m.piece_name.clone().unwrap_or("-".into()),
                m.size_cm.0,
                m.size_cm.1,
                if m.cost.is_finite() { m.cost } else { -1.0 },
                m.dims_err.unwrap_or(f64::NAN) * 100.0,
                m.perimeter_err.unwrap_or(f64::NAN) * 100.0,
                m.area_err.unwrap_or(f64::NAN) * 100.0,
                m.sew_perimeter_err.unwrap_or(f64::NAN) * 100.0,
                m.sew_area_err.unwrap_or(f64::NAN) * 100.0,
                m.confidence,
                if m.rotated_90 { "yes" } else { "no" },
                m.ambiguous_with.join("|"),
            ));
        }
        s
    }

    // ---------- XML scanner ----------
    #[test]
    fn xml_scanner_tolerant() {
        let mut w = vec![];
        let r = parse_xml("<?xml version=\"1.0\"?><!-- c --><A x='1' y=\"a&amp;b\"><B/><C>t &lt; u<D></C><![CDATA[raw<>]]></A>", &mut w).unwrap();
        let a = r.child("A").unwrap();
        assert_eq!(a.attr("Y"), Some("a&b"));
        assert!(a.child("B").is_some());
        let c = a.child("C").unwrap();
        assert_eq!(c.text, "t < u");
        assert!(c.child("D").is_some(), "unclosed D closed by </C>");
        assert!(a.text.contains("raw<>"));
        // truncated tag + unclosed elements
        let r = parse_xml("<A><B>1</B><C att=\"x", &mut w).unwrap();
        assert_eq!(r.child("A").unwrap().child_text("B"), "1");
        assert!(w.iter().any(|m| m.contains("truncated")));
        // stray close
        let mut w2 = vec![];
        parse_xml("<A></Z></A>", &mut w2).unwrap();
        assert!(w2.iter().any(|m| m.contains("stray")));
        // quotes with '>' inside attribute
        let r = parse_xml("<A t=\"a>b\"><B/></A>", &mut vec![]).unwrap();
        assert_eq!(r.child("A").unwrap().attr("t"), Some("a>b"));
        assert!(r.child("A").unwrap().child("B").is_some());
    }

    #[test]
    fn xml_depth_and_count_caps() {
        let deep = "<A>".repeat(MAX_DEPTH + 10);
        assert!(parse_xml(&deep, &mut vec![]).is_err());
        let many = "<A/>".repeat(MAX_ELEMS + 1);
        assert!(parse_xml(&many, &mut vec![]).is_err());
    }

    #[test]
    fn find_block_in_binary_and_corruption() {
        let mut b = vec![0xEF, 0xBF, 0xBD, 0x00, 0x01];
        b.extend_from_slice(b"<?xml version=\"1.0\"?>\r\n<STYLE><NAME>x</NAME></STYLE>");
        b.extend_from_slice(&[0xEF, 0xBF, 0xBD, 0xFF]);
        let (x, t) = extract_xml_block(&b).unwrap();
        assert!(x.starts_with("<?xml") && x.ends_with("</STYLE>") && !t);
        assert!(extract_xml_block(b"nothing here").is_err());
        assert!(extract_xml_block(b"").is_err());
        let (x, t) = extract_xml_block(b"junk<STYLE><NAME>a</NAME>").unwrap();
        assert!(t && x.starts_with("<STYLE>"));
        // "<STYLES" must not count
        assert!(extract_xml_block(b"<STYLESHEET></STYLESHEET>").is_err());
        // non-utf8 in filename decodes lossily
        let mut b = b"<STYLE><FILENAME>C:\\x".to_vec();
        b.extend_from_slice(&[0xE9, 0xFF]);
        b.extend_from_slice(b"\\a.PDS</FILENAME></STYLE>");
        let d = parse_pds(&b).unwrap();
        assert!(d.style.filename.starts_with("C:\\x") && d.style.filename.ends_with("\\a.PDS"));
    }

    // ---------- paths ----------
    #[test]
    fn path_parser() {
        let (mut c, mut bad) = (false, false);
        let p = parse_path("M10,10 L20,10 20,20 H5 V30 Z", &mut c, &mut bad);
        assert_eq!(p.len(), 1);
        assert_eq!(p[0], vec![(10., 10.), (20., 10.), (20., 20.), (5., 20.), (5., 30.)]);
        assert!(!c && !bad);
        let p = parse_path("m1 1 l1 0 0 1 z M5 5 L6 6", &mut c, &mut bad);
        assert_eq!(p.len(), 2);
        assert_eq!(p[0], vec![(1., 1.), (2., 1.), (2., 2.)]);
        let p = parse_path("M0,0 C1,1 2,2 3,3", &mut c, &mut bad);
        assert!(c);
        assert_eq!(p[0].last(), Some(&(3., 3.)));
        let mut bad2 = false;
        let p = parse_path("M0,0 L1e999,5 L2,2 L x", &mut c, &mut bad2);
        assert!(bad2);
        assert!(p.iter().flatten().all(|q| q.0.is_finite() && q.1.is_finite()));
        let _ = parse_path("", &mut c, &mut bad);
        let _ = parse_path("L", &mut c, &mut bad);
        let _ = parse_path("M 1", &mut c, &mut bad);
        let _ = parse_path("1 2 3", &mut c, &mut bad);
    }

    #[test]
    fn numbers_reject_non_finite() {
        assert_eq!(parse_f("nan"), None);
        assert_eq!(parse_f("inf"), None);
        assert_eq!(parse_f("-Infinity"), None);
        assert_eq!(parse_f("1e999"), None);
        assert_eq!(parse_f("2e9"), None);
        assert_eq!(parse_f(" 3.5 "), Some(3.5));
        assert_eq!(lead_num("180 deg."), Some(180.0));
        assert_eq!(lead_num("deg"), None);
    }

    // ---------- synthetic round trip ----------
    fn synth(scale: f64, rotate: bool, extra_style: &str) -> String {
        // piece R: 20 x 10 cm rectangle, sew inset 1 cm, one notch, grain; piece T: 12 x 6 triangle-ish
        let (rw, rh) = if rotate { (10.0 * scale, 20.0 * scale) } else { (20.0 * scale, 10.0 * scale) };
        let f = |v: f64| v.round() as i64;
        let (x0, y0) = (100i64, 100i64);
        let rect = format!("{},{} {},{} {},{} {},{}", x0, y0, x0 + f(rw), y0, x0 + f(rw), y0 + f(rh), x0, y0 + f(rh));
        let inset = f(scale);
        let sew = format!("M{},{} L{},{} L{},{} L{},{} Z", x0 + inset, y0 + inset, x0 + f(rw) - inset, y0 + inset, x0 + f(rw) - inset, y0 + f(rh) - inset, x0 + inset, y0 + f(rh) - inset);
        let tx = 5000i64;
        let tri = format!("{},{} {},{} {},{} {},{}", tx, 200, tx + f(12.0 * scale), 200, tx + f(12.0 * scale), 200 + f(7.0 * scale), tx, 200 + f(7.0 * scale));
        format!(
            r##"<?xml version="1.0"?><STYLE><OPTITEX>1</OPTITEX><UNITS LINEAR="cm" SQUARE="sq.m"/><NAME>syn</NAME><SIZES>1</SIZES><PIECES>2</PIECES>
<SIZES_TABLE><SIZE><NAME>M</NAME><SUM_AREA>0.0272</SUM_AREA><SUM_PERIMETER>104</SUM_PERIMETER></SIZE><BASE_SIZE>M</BASE_SIZE></SIZES_TABLE>
<PIECE><NAME>RECT</NAME><QUANTITY>1</QUANTITY><SIZE><NAME>M</NAME><GEOM_INFO SIZE_X="20" SIZE_Y="10" AREA="0.02" PERIMETER="60" SEW_AREA="0.0144" SEW_PERIMETER="52"/></SIZE></PIECE>
<PIECE><NAME>TRI</NAME><QUANTITY>1</QUANTITY><SIZE><NAME>M</NAME><GEOM_INFO SIZE_X="12" SIZE_Y="7" AREA="0.0084" PERIMETER="38"/></SIZE></PIECE>
{}
<MARKER><VIEW FACTOR="0.06"><svg width="1cm" height="1cm" viewBox="0 0 8000 4000">
<polygon fill="#CCCC33" points="1,4000 1,1 8000,1 8000,4000"/>
<polygon fill="#FFBE46" points="{}"/>
<g style="fill:#000000; stroke:#000000"><path d="{}"/></g>
<g style="fill:#0000FF"><path d="M{},{} L{},{}"/></g>
<g style="fill:#FF6633"><path d="M{},{} L{},{}"/></g>
<polygon fill="#FFBE46" points="{}"/>
</svg></VIEW></MARKER></STYLE>"##,
            extra_style,
            rect,
            sew,
            x0 + 5 * inset, y0 + f(rh), x0 + 5 * inset, y0 + f(rh) - inset,
            x0 + 3 * inset, y0 + 2 * inset, x0 + 3 * inset, y0 + f(rh) - 2 * inset,
            tri
        )
    }

    #[test]
    fn synthetic_scale_is_derived_not_assumed() {
        for &scale in &[100.0, 50.0, 37.5, 254.0] {
            let a = analyze_pds(synth(scale, false, "").as_bytes()).unwrap();
            assert!((a.units_per_cm - scale).abs() / scale < 0.01, "scale {} got {}", scale, a.units_per_cm);
            assert_eq!(a.matches.len(), 2);
            assert_eq!(a.matches[0].piece_name.as_deref(), Some("RECT"));
            assert_eq!(a.matches[1].piece_name.as_deref(), Some("TRI"));
            assert!(a.matches.iter().all(|m| m.confidence == "high"));
            let j = &a.json;
            let pat = Pattern::from_json(j.get("pattern").unwrap()).unwrap();
            assert_eq!(pat.pieces.len(), 2);
            let r = pat.piece("RECT").unwrap();
            // y-up, local origin
            let (lo, hi) = r.bounds();
            assert!((lo.x - 1.0).abs() < 0.05 && (hi.x - 19.0).abs() < 0.05, "{:?} {:?}", lo, hi);
            // sew polygon = 18 x 8 inset by 1 cm => sa == 1
            assert!((r.sa - 1.0).abs() < 0.05, "sa {}", r.sa);
            assert!((r.area() - 144.0).abs() < 3.0, "sew area {}", r.area());
            assert_eq!(r.notches.len(), 1);
            assert!(r.nodes.iter().all(|n| n.sa.is_none()));
            // grain flipped to y-up
            assert!((r.grain.0.y - r.grain.1.y) != 0.0);
        }
    }

    #[test]
    fn marker_size_other_than_base_is_detected() {
        let big = "<SIZE><NAME>L</NAME><GEOM_INFO SIZE_X=\"24\" SIZE_Y=\"12\" AREA=\"0.03\" PERIMETER=\"72\"/></SIZE></PIECE>";
        let x = synth(100.0, false, "").replace("</SIZE></PIECE>", &format!("</SIZE>{}", big)).replace("<BASE_SIZE>M</BASE_SIZE>", "<BASE_SIZE>L</BASE_SIZE>");
        let a = analyze_pds(x.as_bytes()).unwrap();
        assert_eq!(a.marker_size, "M");
        assert!((a.units_per_cm - 100.0).abs() < 0.5);
        assert!(a.matches.iter().all(|m| m.confidence == "high"));
        assert!(a.json.get("warnings").unwrap().to_string().contains("marker shows size 'M'"));
        assert_eq!(a.json.get("pattern").unwrap().get("size").unwrap().as_str(), Some("M"));
    }

    #[test]
    fn synthetic_rotation_detected_and_matched() {
        let a = analyze_pds(synth(100.0, true, "").as_bytes()).unwrap();
        let m = &a.matches[0];
        assert_eq!(m.piece_name.as_deref(), Some("RECT"));
        assert!(m.rotated_90);
        assert!(m.confidence == "high");
        assert!(!a.matches[1].rotated_90);
    }

    #[test]
    fn synthetic_unmatched_and_missing_piece_warn() {
        // remove TRI piece => its outline is unmatched
        let x = synth(100.0, false, "").replace("<PIECE><NAME>TRI</NAME>", "<PIECEX><NAME>TRI</NAME>").replace("</SIZE></PIECE>\n<MARKER", "</SIZE></PIECEX>\n<MARKER");
        let j = analyze_pds(x.as_bytes()).unwrap().json;
        let w = j.get("warnings").unwrap().to_string();
        assert!(w.contains("matches no piece"), "{}", w);
        let outs = j.get("marker").unwrap().get("outlines").unwrap().as_arr().unwrap().clone();
        assert_eq!(outs[1].get("piece"), Some(&Json::Null));
        // still in pattern with a placeholder name
        let pat = Pattern::from_json(j.get("pattern").unwrap()).unwrap();
        assert!(pat.piece("OUTLINE_1").is_some());
    }

    #[test]
    fn synthetic_geom_mismatch_flagged_low_confidence() {
        // the XML claims RECT is 21.5 x 10 (7.5% off) -> still matched (cost<0.15) but flagged
        let x = synth(100.0, false, "").replace("SIZE_X=\"20\"", "SIZE_X=\"21.5\"").replace("PERIMETER=\"60\"", "PERIMETER=\"63\"");
        let a = analyze_pds(x.as_bytes()).unwrap();
        let m = &a.matches[0];
        assert_ne!(m.confidence, "high");
        let w = a.json.get("warnings").unwrap().to_string();
        assert!(w.contains("confidence match"), "{}", w);
    }

    #[test]
    fn warnings_always_state_preview_quality() {
        let j = import_pds(synth(100.0, false, "").as_bytes()).unwrap();
        let w = j.get("warnings").unwrap().to_string();
        assert!(w.contains("preview-quality") && w.contains("NOT the parametric"));
        assert_eq!(j.get("geometry_source").unwrap().as_str(), Some("marker_svg_preview"));
    }

    #[test]
    fn non_finite_numbers_rejected() {
        let x = synth(100.0, false, "").replace("SIZE_X=\"20\"", "SIZE_X=\"NaN\"").replace("AREA=\"0.0084\"", "AREA=\"inf\"");
        let a = analyze_pds(x.as_bytes()).unwrap();
        let w = a.json.get("warnings").unwrap().to_string();
        assert!(w.contains("non-finite"), "{}", w);
        // output has no NaN / inf text
        let s = a.json.to_string();
        assert!(!s.contains(":NaN") && !s.contains("Infinity") && !s.contains(":inf"), "{}", s);
        assert!(w.contains("AREA='inf'"), "{}", w);
        // marker coordinates that overflow are dropped
        let x = synth(100.0, false, "").replace("points=\"100,100 ", "points=\"1e99,100 ");
        let a = analyze_pds(x.as_bytes()).unwrap();
        assert!(a.json.get("warnings").unwrap().to_string().contains("dropped"));
    }

    #[test]
    fn no_marker_or_pieces_is_not_fatal() {
        let j = import_pds(b"<STYLE><NAME>a</NAME></STYLE>").unwrap();
        assert_eq!(j.get("pattern").unwrap().get("pieces").unwrap().as_arr().unwrap().len(), 0);
        assert!(j.get("warnings").unwrap().to_string().contains("no <MARKER>"));
        assert!(import_pds(b"<html></html>").is_err());
    }

    #[test]
    fn piece_cap() {
        let mut x = String::from("<STYLE><NAME>big</NAME>");
        for i in 0..(MAX_PIECES + 20) {
            x.push_str(&format!("<PIECE><NAME>P{}</NAME></PIECE>", i));
        }
        x.push_str("</STYLE>");
        let d = parse_pds(x.as_bytes()).unwrap();
        assert_eq!(d.pieces.len(), MAX_PIECES);
        assert!(d.warnings.iter().any(|w| w.contains("extra pieces")));
    }

    // ---------- real samples ----------
    #[test]
    fn pant_sample_matches_geom_info() {
        let Some(b) = sample(PANT) else { return };
        let a = analyze_pds(&b).unwrap();
        println!("\n=== PANT ===\n{}", table(&a));
        let j = &a.json;
        let st = j.get("style").unwrap();
        assert_eq!(st.get("base_size").unwrap().as_str(), Some("S"));
        assert_eq!(st.get("sizes").unwrap().as_arr().unwrap().len(), 5);
        assert_eq!(st.get("pieces_count").unwrap().as_f64(), Some(7.0));
        assert_eq!(st.get("units").unwrap().as_str(), Some("cm"));
        assert!((a.units_per_cm - 100.0).abs() < 0.5, "scale {}", a.units_per_cm);
        assert_eq!(a.matches.len(), 8, "belt appears as two folded halves");
        for m in &a.matches {
            assert!(m.piece.is_some(), "outline {} unmatched", m.outline);
            let pe = m.perimeter_err.unwrap();
            assert!(pe < 0.02, "outline {} ({:?}) perimeter err {:.3}%", m.outline, m.piece_name, pe * 100.0);
            assert!(m.dims_err.unwrap() < 0.02);
        }
        let names: Vec<_> = a.matches.iter().map(|m| m.piece_name.clone().unwrap()).collect();
        for want in ["WAIST- BELT", "FRONT", "BACK", "PKT-IN", "FACING", "DRAWSTRING", "FACING1"] {
            assert!(names.iter().any(|n| n == want), "missing {}", want);
        }
        assert_eq!(names.iter().filter(|n| *n == "WAIST- BELT").count(), 2);
        // sew perimeter / area agree for the ordinary (non-folded) pieces
        for m in a.matches.iter().filter(|m| m.piece_name.as_deref() == Some("FRONT") || m.piece_name.as_deref() == Some("BACK")) {
            assert!(m.sew_perimeter_err.unwrap() < 0.03, "sew perim {:?}", m.sew_perimeter_err);
            assert!(m.sew_area_err.unwrap() < 0.03);
        }
        // base-size sums are internally consistent
        let chk = st.get("base_sums_check").unwrap();
        assert!(chk.get("sum_area_rel_err").unwrap().as_f64().unwrap() < 0.001);
        assert!(chk.get("sum_perimeter_rel_err").unwrap().as_f64().unwrap() < 0.001);
        // pattern round-trips through the model, seam allowance ~1 cm-ish and sane
        let pat = Pattern::from_json(j.get("pattern").unwrap()).unwrap();
        assert_eq!(pat.pieces.len(), 8);
        let back = pat.piece("BACK").unwrap();
        assert!(back.sa > 0.5 && back.sa < 3.0, "sa {}", back.sa);
        let (lo, hi) = back.bounds();
        assert!(lo.x >= 0.0 && lo.x < 2.5 && lo.y >= 0.0 && lo.y < 2.5, "{:?}", lo);
        assert!((hi.x - lo.x) < 112.94 && (hi.x - lo.x) > 100.0);
        assert!(signed_area(&back.flatten(4).0) > 0.0, "ccw y-up");
        // notches present for PKT-IN (XML says 2)
        let pk = j.get("pieces").unwrap().as_arr().unwrap().iter().find(|p| p.get("name").unwrap().as_str() == Some("PKT-IN")).unwrap().clone();
        assert_eq!(pk.get("notch_count").unwrap().as_f64(), Some(2.0));
        assert_eq!(pk.get("marker_notch_count").unwrap().as_f64(), Some(2.0));
        // json re-parses
        assert!(Json::parse(&j.to_string()).is_ok());
    }

    #[test]
    fn shirt_corrupted_sample_matches_geom_info() {
        let Some(b) = sample(SHIRT) else { return };
        assert!(b.windows(3).any(|w| w == [0xEF, 0xBF, 0xBD]), "sample really is mangled");
        let a = analyze_pds(&b).unwrap();
        println!("\n=== SHIRT (corrupted upload) ===\n{}", table(&a));
        let st = a.json.get("style").unwrap();
        assert_eq!(st.get("base_size").unwrap().as_str(), Some("L"));
        assert_eq!(a.marker_size, "L");
        assert_eq!(st.get("pieces_count").unwrap().as_f64(), Some(7.0));
        assert!((a.units_per_cm - 100.0).abs() < 0.5, "scale {}", a.units_per_cm);
        assert_eq!(a.matches.len(), 12);
        for m in &a.matches {
            assert!(m.piece.is_some(), "outline {} unmatched", m.outline);
            assert!(m.dims_err.unwrap() < 0.02, "outline {} dims", m.outline);
            if m.closed_half {
                // fold length unknown: perimeter only indicative, area is exact (2 halves)
                assert!(m.area_err.unwrap() < 0.04, "outline {} area", m.outline);
            } else {
                let pe = m.perimeter_err.unwrap();
                assert!(pe < 0.02, "outline {} ({:?}) perimeter err {:.3}%", m.outline, m.piece_name, pe * 100.0);
            }
            assert_eq!(m.confidence, "high", "outline {}", m.outline);
        }
        // BND TOP and BND IN are identical in GEOM_INFO: must be flagged ambiguous
        let w = a.json.get("warnings").unwrap().to_string();
        assert!(w.contains("indistinguishable"), "{}", w);
        let cnt = |n: &str| a.matches.iter().filter(|m| m.piece_name.as_deref() == Some(n)).count();
        assert_eq!(cnt("FRT"), 1);
        assert_eq!(cnt("back"), 2);
        assert_eq!(cnt("Sleeve"), 1);
        assert_eq!(cnt("BND TOP") + cnt("BND IN"), 4);
        // all pattern pieces valid
        let pat = Pattern::from_json(a.json.get("pattern").unwrap()).unwrap();
        assert_eq!(pat.pieces.len(), 12);
    }

    #[test]
    fn corrupted_equals_intact_xml_result() {
        // wiping the binary part of the intact pant file with EF BF BD must not change the result
        let Some(b) = sample(PANT) else { return };
        let s = find_bytes(&b, b"<?xml", 0).expect("xml");
        let mut m = b.clone();
        let mut i = 0;
        while i < s {
            m[i] = [0xEF, 0xBF, 0xBD][i % 3];
            i += 1;
        }
        let e = rfind_bytes(&b, b"</STYLE>", 0).unwrap() + 8;
        for k in e..m.len() {
            m[k] = [0xEF, 0xBF, 0xBD][k % 3];
        }
        let a = import_pds(&b).unwrap().to_string();
        let c = import_pds(&m).unwrap().to_string();
        assert_eq!(a, c);
    }

    #[test]
    fn extracted_xml_file_also_works() {
        let Some(x) = sample("61dcbea7.xml") else { return };
        let a = analyze_pds(&x).unwrap();
        assert_eq!(a.matches.len(), 8);
        let pcs = import_pds_pieces(&x).unwrap();
        assert_eq!(pcs.len(), 7);
        assert_eq!(pcs[1].name, "FRONT");
        assert_eq!(pcs[1].quantity, 2);
        assert_eq!(pcs[1].nesting.opposite, "Up/Down");
        assert_eq!(pcs[1].nesting.rotation_deg, Some(180.0));
        assert_eq!(pcs[1].position, Some((185.5061, 332.9288)));
        assert!(pcs[0].is_closed_half());
        let s = pcs[2].size("S").unwrap();
        assert_eq!(s.size_x, Some(112.9337));
        assert_eq!(s.sew_perimeter, Some(281.6504));
        assert_eq!(pcs[0].sizes.len(), 5);
    }

    // ---------- robustness ----------
    #[test]
    fn truncated_inputs_never_panic() {
        for name in [PANT, SHIRT] {
            let Some(b) = sample(name) else { continue };
            let s = find_bytes(&b, b"<STYLE", 0).unwrap();
            let e = rfind_bytes(&b, b"</STYLE>", 0).unwrap() + 8;
            let mut cuts: Vec<usize> = (0..b.len()).step_by(1013).collect();
            cuts.extend((s.saturating_sub(5)..(s + 400).min(b.len())).step_by(7));
            cuts.extend((e.saturating_sub(300)..=e.min(b.len())).step_by(3));
            let (mut ok, mut err) = (0, 0);
            for c in cuts {
                match import_pds(&b[..c.min(b.len())]) {
                    Ok(j) => {
                        ok += 1;
                        assert!(Json::parse(&j.to_string()).is_ok());
                    }
                    Err(_) => err += 1,
                }
            }
            println!("{}: truncation ok={} err={}", name, ok, err);
            assert!(ok > 0 && err > 0);
        }
    }

    #[test]
    fn truncated_in_marker_gives_warning_and_partial_outlines() {
        let Some(b) = sample(PANT) else { return };
        let m = find_bytes(&b, b"<MARKER>", 0).unwrap();
        let cut = find_bytes(&b, b"<polygon fill=\"#FFBE46\"", m + 400).unwrap() + 30;
        let a = analyze_pds(&b[..cut]).unwrap();
        let w = a.json.get("warnings").unwrap().to_string();
        assert!(w.contains("truncated"));
        assert!(a.matches.len() < 8);
        // metadata survives
        assert_eq!(a.doc.pieces.len(), 7);
    }

    #[test]
    fn garbled_inputs_never_panic() {
        let mut seed = 0x9E3779B97F4A7C15u64;
        let mut rnd = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        let mut sources: Vec<Vec<u8>> = vec![synth(100.0, false, "").into_bytes()];
        for n in [PANT, SHIRT] {
            if let Some(b) = sample(n) {
                let s = find_bytes(&b, b"<STYLE", 0).unwrap();
                let e = rfind_bytes(&b, b"</STYLE>", 0).unwrap() + 8;
                sources.push(b[s..e].to_vec());
            }
        }
        let alphabet: &[u8] = b"<>/=\"' &;#-.,0123456789MLZ\x00\xff\xef\xbf\xbdabcXYZ";
        for src in &sources {
            for it in 0..150 {
                let mut m = src.clone();
                let k = 1 + (rnd() % 40) as usize;
                for _ in 0..k {
                    let p = (rnd() as usize) % m.len();
                    match rnd() % 4 {
                        0 => m[p] = alphabet[(rnd() as usize) % alphabet.len()],
                        1 => {
                            m.remove(p);
                        }
                        2 => m.insert(p, alphabet[(rnd() as usize) % alphabet.len()]),
                        _ => {
                            let q = (p + (rnd() % 64) as usize).min(m.len());
                            m.drain(p..q);
                        }
                    }
                    if m.is_empty() {
                        m.push(b'<');
                    }
                }
                if it % 10 == 0 {
                    let cut = (rnd() as usize) % (m.len() + 1);
                    m.truncate(cut);
                }
                if let Ok(j) = import_pds(&m) {
                    let s = j.to_string();
                    assert!(!s.contains("NaN") && !s.contains("Infinity") && !s.contains(":inf"));
                }
            }
        }
    }

    #[test]
    fn degenerate_geometry_never_panics() {
        // zero-area, collinear, 2-point, single point polygons and a path-only marker
        let mk = |poly: &str| {
            format!(
                "<STYLE><PIECE><NAME>A</NAME><SIZE><NAME>M</NAME><GEOM_INFO SIZE_X=\"0\" SIZE_Y=\"0\" PERIMETER=\"0\" AREA=\"0\"/></SIZE></PIECE><SIZES_TABLE><BASE_SIZE>M</BASE_SIZE></SIZES_TABLE><MARKER><VIEW><svg viewBox=\"0 0 0 0\"><polygon fill=\"#FFBE46\" points=\"{}\"/><g style=\"fill:#000000\"><path d=\"M1,1 L1,1 L1,1\"/></g></svg></VIEW></MARKER></STYLE>",
                poly
            )
        };
        for p in ["", "1,1", "1,1 2,2", "1,1 2,2 3,3", "1,1 1,1 1,1", "0,0 10,0 10,10 0,10", "0,0 10,0 10,10 0,10 5"] {
            let _ = import_pds(mk(p).as_bytes());
        }
        let _ = import_pds(b"<STYLE><MARKER><svg></svg></MARKER></STYLE>");
        let _ = import_pds(b"<STYLE><MARKER></MARKER></STYLE>");
        let _ = import_pds(&[b'<'; 100]);
        let _ = import_pds(b"<STYLE");
        let _ = import_pds(b"<STYLE>");
    }
}
