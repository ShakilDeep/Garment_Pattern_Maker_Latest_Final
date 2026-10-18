//! Glue between the JSON API and the PDS / spec / marker modules.
use crate::geom::*;
use crate::json::Json;
use crate::model::*;
use crate::{marker, pds_bin, pds_import, spec};

pub(crate) fn b64_decode(s: &str) -> Result<Vec<u8>, String> {
    let mut out = Vec::with_capacity(s.len() * 3 / 4);
    let (mut acc, mut bits) = (0u32, 0u32);
    for c in s.bytes() {
        let v = match c {
            b'A'..=b'Z' => c - b'A',
            b'a'..=b'z' => c - b'a' + 26,
            b'0'..=b'9' => c - b'0' + 52,
            b'+' | b'-' => 62,
            b'/' | b'_' => 63,
            b'=' | b'\r' | b'\n' | b' ' => continue,
            _ => return Err("invalid base64 data".into()),
        } as u32;
        acc = (acc << 6) | v;
        bits += 6;
        if bits >= 8 {
            bits -= 8;
            out.push(((acc >> bits) & 0xff) as u8);
        }
    }
    Ok(out)
}

fn dist_to_poly(p: V2, poly: &[V2]) -> f64 {
    let mut best = f64::MAX;
    for i in 0..poly.len() {
        let (a, b) = (poly[i], poly[(i + 1) % poly.len()]);
        let ab = v2(b.x - a.x, b.y - a.y);
        let l2 = ab.x * ab.x + ab.y * ab.y;
        let t = if l2 < 1e-12 { 0.0 } else { (((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / l2).clamp(0.0, 1.0) };
        let (dx, dy) = (p.x - (a.x + t * ab.x), p.y - (a.y + t * ab.y));
        best = best.min((dx * dx + dy * dy).sqrt());
    }
    best
}

/// Build a Piece from a decoded sew polygon (+ optional cut polygon for the seam allowance).
fn piece_from_polys(name: &str, sew: &[(f64, f64)], cut: &[(f64, f64)], qty: u32) -> Option<Piece> {
    if sew.len() < 3 { return None; }
    let mut pts: Vec<V2> = sew.iter().map(|&(x, y)| v2(x, y)).collect();
    if signed_area(&pts) < 0.0 { pts.reverse(); }
    let mut sa = 1.0;
    if cut.len() >= 3 {
        let cutp: Vec<V2> = cut.iter().map(|&(x, y)| v2(x, y)).collect();
        let mut d: Vec<f64> = pts.iter().map(|p| dist_to_poly(*p, &cutp)).collect();
        d.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        sa = d[d.len() / 2];
        if !sa.is_finite() || sa > 5.0 { sa = 1.0; }
    }
    let (mut x0, mut x1, mut y0, mut y1) = (f64::MAX, f64::MIN, f64::MAX, f64::MIN);
    for p in &pts { x0 = x0.min(p.x); x1 = x1.max(p.x); y0 = y0.min(p.y); y1 = y1.max(p.y); }
    let nodes: Vec<Node> = pts.iter().enumerate().map(|(i, p)| Node::corner(p.x - x0, p.y - y0, &format!("e{}", i))).collect();
    let cx = (x1 - x0) * 0.5;
    Some(Piece {
        name: name.to_string(), zone: "imported".into(), nodes,
        grain: (v2(cx, (y1 - y0) * 0.2), v2(cx, (y1 - y0) * 0.8)),
        notches: vec![], darts: vec![], internal: vec![], drills: vec![], sa,
        mirror: false, qty: qty.max(1), material: "A".into(),
    })
}

fn pattern_for_size(doc: &pds_bin::PdsBinDoc, size: &str) -> Pattern {
    let mut pieces = Vec::new();
    for g in doc.pieces.iter().filter(|g| g.size == size) {
        if let Some(p) = piece_from_polys(&g.name, &g.sew, &g.cut, g.quantity) { pieces.push(p); }
    }
    Pattern { style: doc.style.clone(), size: size.to_string(), garment: "imported".into(), pieces, seams: vec![] }
}

/// op import_pds {data_b64, size?}
pub fn import_pds(j: &Json) -> Result<Json, String> {
    let data = b64_decode(j.get("data_b64").and_then(|v| v.as_str()).ok_or("missing data_b64")?)?;
    let want = j.get("size").and_then(|v| v.as_str()).map(|s| s.to_string());
    let doc = pds_bin::decode(&data)?;
    if doc.decoded_geometry && !doc.sizes.is_empty() {
        let size = want.filter(|s| doc.sizes.contains(s)).unwrap_or_else(|| doc.base_size.clone());
        let pat = pattern_for_size(&doc, &size);
        let all: Vec<Json> = doc.sizes.iter().map(|s| Json::obj().set("size", Json::str(s)).set("pattern", pattern_for_size(&doc, s).to_json())).collect();
        let mut warns: Vec<Json> = doc.warnings.iter().map(|w| Json::str(w)).collect();
        warns.push(Json::str("Geometry decoded from the PDS binary and validated against the file's XML (perimeter/area within ~0.3%). Curves between vertices are not tessellated; notches/grain/internal lines are not imported."));
        return Ok(Json::obj()
            .set("source", Json::str("pds_binary"))
            .set("style", Json::str(&doc.style)).set("version", Json::str(&doc.version))
            .set("sizes", Json::Arr(doc.sizes.iter().map(|s| Json::str(s)).collect()))
            .set("base_size", Json::str(&doc.base_size)).set("size", Json::str(&size))
            .set("pattern", pat.to_json()).set("patterns", Json::Arr(all)).set("warnings", Json::Arr(warns)));
    }
    // fall back: XML summary + marker preview outlines
    let mut r = pds_import::import_pds(&data)?;
    let mut warns: Vec<Json> = doc.warnings.iter().map(|w| Json::str(w)).collect();
    warns.insert(0, Json::str("Binary geometry could not be validated for this file (e.g. upload corrupted the binary part); showing the base-size marker preview outlines instead."));
    if let Some(Json::Arr(w)) = r.get("warnings") { warns.extend(w.iter().cloned()); }
    r = r.set("warnings", Json::Arr(warns)).set("source", Json::str("marker_preview"));
    if let Some(sz) = r.get("style").and_then(|s| s.get("sizes")).cloned() { r = r.set("sizes", sz); }
    Ok(r)
}

/// op parse_spec {text} -> {spec, warnings}
pub fn parse_spec(j: &Json) -> Result<Json, String> {
    let text = j.get("text").and_then(|v| v.as_str()).ok_or("missing text")?;
    let s = spec::parse_spec_text(text)?;
    let mut warns: Vec<Json> = s.warnings.iter().map(|w| Json::str(w)).collect();
    warns.extend(s.check().iter().map(|w| Json::str(w)));
    Ok(Json::obj().set("spec", s.to_json()).set("grade", s.spec_to_grade_table()).set("warnings", Json::Arr(warns)))
}

/// op nest {...}
pub fn nest(j: &Json) -> Result<Json, String> { marker::nest_request(j) }

/// op draft_spec {garment:"shirt"|"pant", spec:<SpecSheet json>, size?, opts?:{sa}} ->
/// {pattern, checks, sizes:[{label,step,measurements,pattern,table}], used:{...}, warnings}
pub fn draft_spec(j: &Json) -> Result<Json, String> {
    use crate::garments::{self, GarmentOpts};
    use std::collections::BTreeMap;
    let kind = j.get("garment").and_then(|v| v.as_str()).ok_or("missing garment")?;
    let sp = spec::SpecSheet::from_json(j.get("spec").ok_or("missing spec")?)?;
    if sp.sizes.is_empty() { return Err("spec has no sizes".into()); }
    let size = j.get("size").and_then(|v| v.as_str()).map(|s| s.to_string()).unwrap_or_else(|| sp.base_size.clone());
    let mut go = GarmentOpts::default();
    if let Some(sa) = j.get("opts").and_then(|o| o.get("sa")).and_then(|v| v.as_f64()) { go.sa = sa.clamp(0.0, 5.0); }
    let column = |z: &str| -> BTreeMap<String, f64> {
        let mut m = sp.name_map(z);
        for (k, v) in sp.canonical_map(z) { m.insert(k, v); }
        for (k, v) in sp.size_map(z) { m.insert(k, v); }
        m
    };
    if !sp.sizes.iter().any(|z| z.eq_ignore_ascii_case(&size)) { return Err(format!("size '{}' is not in the spec ({})", size, sp.sizes.join(", "))); }
    let per: Vec<(String, BTreeMap<String, f64>)> = sp.sizes.iter().map(|z| (z.clone(), column(z))).collect();
    let all = garments::grade_garment_opts(kind, &column(&size), &per, &go)?;
    let cur = all.iter().find(|(z, _)| z.eq_ignore_ascii_case(&size)).ok_or("size not drafted")?.1.clone();
    let bi = sp.sizes.iter().position(|z| z.eq_ignore_ascii_case(&size)).unwrap_or(0) as i64;
    let sizes: Vec<Json> = all.iter().enumerate().map(|(i, (z, p))| {
        Json::obj().set("label", Json::str(z)).set("step", Json::num((i as i64 - bi) as f64))
            .set("measurements", Json::obj()).set("pattern", p.to_json()).set("table", Json::Arr(vec![]))
    }).collect();
    let cs = garments::garment_checks(&cur);
    let checks: Vec<Json> = cs.iter().map(|c| Json::obj().set("name", Json::str(&c.name)).set("value", Json::num(c.value))
        .set("expected", Json::num(c.expected)).set("tol", Json::num(c.tol)).set("ok", Json::Bool(c.ok()))).collect();
    Ok(Json::obj().set("pattern", cur.to_json()).set("checks", Json::Arr(checks)).set("sizes", Json::Arr(sizes))
        .set("size", Json::str(&size)).set("base_size", Json::str(&sp.base_size))
        .set("warnings", Json::Arr(vec![Json::str("Pattern re-created parametrically from the spec values (not the factory's hand-drawn curves). Verified against the sample PDS within ~3% on sew dimensions; check before cutting.")])))
}
