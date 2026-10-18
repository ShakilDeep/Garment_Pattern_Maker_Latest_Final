//! Pattern data model + JSON (de)serialization. Units: centimetres, y-up.
use crate::geom::*;
use crate::json::Json;

#[derive(Clone, Debug)]
pub struct Measurements {
    pub bust: f64,
    pub waist: f64,
    pub hip: f64,
    pub back_length: f64,   // nape to waist
    pub shoulder_width: f64, // across back, shoulder point to shoulder point
    pub neck: f64,
    pub bicep: f64,
    pub wrist: f64,
    pub sleeve_length: f64, // shoulder point to wrist
    pub waist_to_hip: f64,
    pub skirt_length: f64,   // waist to hem
    pub rise: f64,           // waist to crotch (body rise)
    pub inseam: f64,
    pub thigh: f64,
    pub knee: f64,
    pub ankle: f64,
    pub height: f64,
}

impl Default for Measurements {
    fn default() -> Self {
        Measurements {
            bust: 92.0, waist: 74.0, hip: 98.0, back_length: 41.0, shoulder_width: 38.0, neck: 37.0,
            bicep: 29.0, wrist: 16.0, sleeve_length: 60.0, waist_to_hip: 20.0, skirt_length: 60.0,
            rise: 27.0, inseam: 78.0, thigh: 57.0, knee: 38.0, ankle: 23.0, height: 168.0,
        }
    }
}

pub const MEASURE_KEYS: [&str; 17] = [
    "bust", "waist", "hip", "back_length", "shoulder_width", "neck", "bicep", "wrist", "sleeve_length",
    "waist_to_hip", "skirt_length", "rise", "inseam", "thigh", "knee", "ankle", "height",
];

impl Measurements {
    pub fn get(&self, k: &str) -> Option<f64> {
        Some(match k {
            "bust" => self.bust, "waist" => self.waist, "hip" => self.hip,
            "back_length" => self.back_length, "shoulder_width" => self.shoulder_width,
            "neck" => self.neck, "bicep" => self.bicep, "wrist" => self.wrist,
            "sleeve_length" => self.sleeve_length, "waist_to_hip" => self.waist_to_hip,
            "skirt_length" => self.skirt_length, "rise" => self.rise, "inseam" => self.inseam,
            "thigh" => self.thigh, "knee" => self.knee, "ankle" => self.ankle, "height" => self.height,
            _ => return None,
        })
    }
    pub fn set(&mut self, k: &str, v: f64) -> bool {
        let r = match k {
            "bust" => &mut self.bust, "waist" => &mut self.waist, "hip" => &mut self.hip,
            "back_length" => &mut self.back_length, "shoulder_width" => &mut self.shoulder_width,
            "neck" => &mut self.neck, "bicep" => &mut self.bicep, "wrist" => &mut self.wrist,
            "sleeve_length" => &mut self.sleeve_length, "waist_to_hip" => &mut self.waist_to_hip,
            "skirt_length" => &mut self.skirt_length, "rise" => &mut self.rise,
            "inseam" => &mut self.inseam, "thigh" => &mut self.thigh, "knee" => &mut self.knee,
            "ankle" => &mut self.ankle, "height" => &mut self.height,
            _ => return false,
        };
        *r = v;
        true
    }
    /// Missing keys keep defaults; unknown keys are returned as warnings.
    pub fn from_json(j: &Json) -> Result<(Measurements, Vec<String>), String> {
        let mut m = Measurements::default();
        let warn = m.apply_json(j)?;
        Ok((m, warn))
    }
    /// Overlay the numeric entries of a JSON object onto `self`.
    pub fn apply_json(&mut self, j: &Json) -> Result<Vec<String>, String> {
        let mut warn = Vec::new();
        match j {
            Json::Obj(o) => {
                for (k, v) in o {
                    let key = k.trim().to_lowercase().replace([' ', '-'], "_");
                    match v.as_f64() {
                        Some(n) if n.is_finite() && n > 0.0 && n < 500.0 => {
                            if !self.set(&key, n) {
                                warn.push(format!("unknown measurement '{}' ignored", k));
                            }
                        }
                        _ => warn.push(format!("invalid value for '{}' ignored", k)),
                    }
                }
            }
            _ => return Err("measurements must be an object".into()),
        }
        Ok(warn)
    }
    pub fn to_json(&self) -> Json {
        let mut o = Json::obj();
        for k in MEASURE_KEYS {
            o = o.set(k, Json::num(self.get(k).unwrap()));
        }
        o
    }
}

#[derive(Clone, Debug, Default)]
pub struct Node {
    pub p: V2,
    pub hin: V2,  // relative incoming handle
    pub hout: V2, // relative outgoing handle
    pub edge: String, // tag for edge starting at this node
    pub sa: Option<f64>, // seam allowance override for this edge (cm)
}

impl Node {
    pub fn corner(x: f64, y: f64, edge: &str) -> Node {
        Node { p: v2(x, y), edge: edge.into(), ..Default::default() }
    }
}

#[derive(Clone, Debug)]
pub struct Notch {
    pub node: usize, // edge index (edge starting at node)
    pub t: f64,      // 0..1 along edge arc length
    pub kind: String, // slit | v | t | castle | check | u
}

#[derive(Clone, Debug)]
pub struct Dart {
    pub apex: V2,
    pub a: V2,
    pub b: V2,
}

#[derive(Clone, Debug)]
pub struct Piece {
    pub name: String,
    pub zone: String, // upper | lower | sleeve | trouser
    pub nodes: Vec<Node>,
    pub grain: (V2, V2),
    pub notches: Vec<Notch>,
    pub darts: Vec<Dart>,
    pub internal: Vec<Vec<V2>>,
    pub drills: Vec<V2>,
    pub sa: f64,
    pub mirror: bool, // piece is cut twice mirrored (left/right)
    pub qty: u32,
    pub material: String,
}

#[derive(Clone, Debug)]
pub struct Seam {
    pub a_piece: String,
    pub a_tag: String, // edge tag (all consecutive edges with the tag form the seam)
    pub b_piece: String,
    pub b_tag: String,
    pub rev: bool, // second runs opposite to first
    // a_piece==b_piece && a_tag==b_tag means a fold/centre seam joining the two mirrored halves
}

#[derive(Clone, Debug)]
pub struct Pattern {
    pub style: String,
    pub size: String,
    pub garment: String,
    pub pieces: Vec<Piece>,
    pub seams: Vec<Seam>,
}

// ---- JSON helpers ----
fn jv(p: V2) -> Json { Json::nums(&[p.x, p.y]) }
fn pv(j: &Json) -> Result<V2, String> {
    let a = j.as_arr().ok_or("point must be [x,y]")?;
    if a.len() != 2 { return Err("point must have 2 numbers".into()); }
    let f = |i: usize| a[i].as_f64().filter(|v| v.is_finite() && v.abs() < 1e5).ok_or("bad number in point".to_string());
    Ok(v2(f(0)?, f(1)?))
}
fn gs(j: &Json, k: &str, d: &str) -> String { j.get(k).and_then(|v| v.as_str()).unwrap_or(d).to_string() }
fn gf(j: &Json, k: &str, d: f64) -> f64 { j.get(k).and_then(|v| v.as_f64()).unwrap_or(d) }

impl Node {
    pub fn to_json(&self) -> Json {
        let mut o = Json::obj().set("p", jv(self.p)).set("edge", Json::str(&self.edge));
        if self.hin != V2::default() { o = o.set("hin", jv(self.hin)); }
        if self.hout != V2::default() { o = o.set("hout", jv(self.hout)); }
        if let Some(s) = self.sa { o = o.set("sa", Json::num(s)); }
        o
    }
    pub fn from_json(j: &Json) -> Result<Node, String> {
        Ok(Node {
            p: pv(j.get("p").ok_or("node missing p")?)?,
            hin: j.get("hin").map(pv).transpose()?.unwrap_or_default(),
            hout: j.get("hout").map(pv).transpose()?.unwrap_or_default(),
            edge: gs(j, "edge", ""),
            sa: j.get("sa").and_then(|v| v.as_f64()),
        })
    }
}

impl Piece {
    pub fn to_json(&self) -> Json {
        Json::obj()
            .set("name", Json::str(&self.name))
            .set("zone", Json::str(&self.zone))
            .set("nodes", Json::Arr(self.nodes.iter().map(|n| n.to_json()).collect()))
            .set("grain", Json::Arr(vec![jv(self.grain.0), jv(self.grain.1)]))
            .set("notches", Json::Arr(self.notches.iter().map(|n| {
                Json::obj().set("node", Json::num(n.node as f64)).set("t", Json::num(n.t)).set("kind", Json::str(&n.kind))
            }).collect()))
            .set("darts", Json::Arr(self.darts.iter().map(|d| {
                Json::obj().set("apex", jv(d.apex)).set("a", jv(d.a)).set("b", jv(d.b))
            }).collect()))
            .set("internal", Json::Arr(self.internal.iter().map(|l| Json::Arr(l.iter().map(|p| jv(*p)).collect())).collect()))
            .set("drills", Json::Arr(self.drills.iter().map(|p| jv(*p)).collect()))
            .set("sa", Json::num(self.sa))
            .set("mirror", Json::Bool(self.mirror))
            .set("qty", Json::num(self.qty as f64))
            .set("material", Json::str(&self.material))
    }
    pub fn from_json(j: &Json) -> Result<Piece, String> {
        let nodes: Result<Vec<Node>, String> = j.get("nodes").and_then(|v| v.as_arr()).ok_or("piece missing nodes")?
            .iter().map(Node::from_json).collect();
        let nodes = nodes?;
        if nodes.len() < 3 { return Err("piece needs at least 3 nodes".into()); }
        let g = j.get("grain").and_then(|v| v.as_arr()).filter(|a| a.len() == 2);
        let grain = match g { Some(a) => (pv(&a[0])?, pv(&a[1])?), None => (v2(0., 0.), v2(0., -10.)) };
        let mut notches = Vec::new();
        if let Some(a) = j.get("notches").and_then(|v| v.as_arr()) {
            for n in a {
                notches.push(Notch { node: gf(n, "node", 0.0) as usize, t: gf(n, "t", 0.5).clamp(0.0, 1.0), kind: gs(n, "kind", "slit") });
            }
        }
        let mut darts = Vec::new();
        if let Some(a) = j.get("darts").and_then(|v| v.as_arr()) {
            for d in a {
                darts.push(Dart {
                    apex: pv(d.get("apex").ok_or("dart apex")?)?,
                    a: pv(d.get("a").ok_or("dart a")?)?,
                    b: pv(d.get("b").ok_or("dart b")?)?,
                });
            }
        }
        let mut internal = Vec::new();
        if let Some(a) = j.get("internal").and_then(|v| v.as_arr()) {
            for l in a {
                let pts: Result<Vec<V2>, String> = l.as_arr().ok_or("internal line")?.iter().map(pv).collect();
                internal.push(pts?);
            }
        }
        let mut drills = Vec::new();
        if let Some(a) = j.get("drills").and_then(|v| v.as_arr()) {
            for p in a { drills.push(pv(p)?); }
        }
        Ok(Piece {
            name: gs(j, "name", "Piece"),
            zone: gs(j, "zone", "upper"),
            nodes, grain, notches, darts, internal, drills,
            sa: gf(j, "sa", 1.0).clamp(0.0, 10.0),
            mirror: j.get("mirror").and_then(|v| v.as_bool()).unwrap_or(false),
            qty: gf(j, "qty", 1.0).clamp(1.0, 99.0) as u32,
            material: gs(j, "material", "SELF"),
        })
    }

    /// Outline flattened to a polyline. Returns (points, edge_index_of_each_segment_start).
    /// Segment k (pts[k]→pts[k+1], closing at the end) belongs to edge seg_edge[k].
    pub fn flatten(&self, per_curve: usize) -> (Vec<V2>, Vec<usize>) {
        let n = self.nodes.len();
        let mut pts = Vec::new();
        let mut seg = Vec::new();
        for i in 0..n {
            let a = &self.nodes[i];
            let b = &self.nodes[(i + 1) % n];
            let straight = a.hout == V2::default() && b.hin == V2::default();
            if straight {
                pts.push(a.p);
                seg.push(i);
            } else {
                let ps = flatten_cubic([a.p, a.p + a.hout, b.p + b.hin, b.p], per_curve);
                for q in &ps[..ps.len() - 1] {
                    pts.push(*q);
                    seg.push(i);
                }
            }
        }
        (pts, seg)
    }

    /// Control points (as flattened polyline, inclusive of both ends) for a single edge.
    pub fn edge_polyline(&self, i: usize, per_curve: usize) -> Vec<V2> {
        let n = self.nodes.len();
        let a = &self.nodes[i % n];
        let b = &self.nodes[(i + 1) % n];
        if a.hout == V2::default() && b.hin == V2::default() {
            vec![a.p, b.p]
        } else {
            flatten_cubic([a.p, a.p + a.hout, b.p + b.hin, b.p], per_curve)
        }
    }

    pub fn bounds(&self) -> (V2, V2) {
        let (pts, _) = self.flatten(16);
        let mut lo = pts[0];
        let mut hi = pts[0];
        for p in &pts {
            lo = v2(lo.x.min(p.x), lo.y.min(p.y));
            hi = v2(hi.x.max(p.x), hi.y.max(p.y));
        }
        (lo, hi)
    }

    pub fn area(&self) -> f64 {
        signed_area(&self.flatten(24).0).abs()
    }
}

impl Pattern {
    pub fn to_json(&self) -> Json {
        Json::obj()
            .set("style", Json::str(&self.style))
            .set("size", Json::str(&self.size))
            .set("garment", Json::str(&self.garment))
            .set("pieces", Json::Arr(self.pieces.iter().map(|p| p.to_json()).collect()))
            .set("seams", Json::Arr(self.seams.iter().map(|s| {
                Json::obj().set("a", Json::str(&s.a_piece)).set("at", Json::str(&s.a_tag))
                    .set("b", Json::str(&s.b_piece)).set("bt", Json::str(&s.b_tag)).set("rev", Json::Bool(s.rev))
            }).collect()))
    }
    pub fn from_json(j: &Json) -> Result<Pattern, String> {
        let pieces: Result<Vec<Piece>, String> = j.get("pieces").and_then(|v| v.as_arr()).ok_or("pattern missing pieces")?
            .iter().map(Piece::from_json).collect();
        let pieces = pieces?;
        let mut seams = Vec::new();
        if let Some(a) = j.get("seams").and_then(|v| v.as_arr()) {
            for s in a {
                seams.push(Seam {
                    a_piece: gs(s, "a", ""), a_tag: gs(s, "at", ""),
                    b_piece: gs(s, "b", ""), b_tag: gs(s, "bt", ""),
                    rev: s.get("rev").and_then(|v| v.as_bool()).unwrap_or(false),
                });
            }
        }
        Ok(Pattern { style: gs(j, "style", "Style"), size: gs(j, "size", "M"), garment: gs(j, "garment", "bodice"), pieces, seams })
    }
    pub fn piece(&self, name: &str) -> Option<&Piece> {
        self.pieces.iter().find(|p| p.name == name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn measurements_defaults_and_warnings() {
        let j = Json::parse(r#"{"Bust": 100, "waist": -5, "foo": 3}"#).unwrap();
        let (m, w) = Measurements::from_json(&j).unwrap();
        assert_eq!(m.bust, 100.0);
        assert_eq!(m.waist, Measurements::default().waist);
        assert_eq!(w.len(), 2);
    }
}

impl Piece {
    pub fn edge_len(&self, i: usize) -> f64 {
        poly_len(&self.edge_polyline(i, 32))
    }
    pub fn find_edge(&self, tag: &str) -> Option<usize> {
        self.nodes.iter().position(|n| n.edge == tag)
    }
    pub fn tag_len(&self, tag: &str) -> f64 {
        (0..self.nodes.len()).filter(|&i| self.nodes[i].edge == tag).map(|i| self.edge_len(i)).sum()
    }
}
