//! POM (point-of-measure) measurement engine.
//!
//! Given a drafted [`Pattern`] (from `garments::draft_pant_detailed` / `draft_shirt`) this
//! module measures every point of measure of the garment *from the sew line of the geometry*,
//! each with ONE explicit, documented definition.  The definitions are catalogued in
//! `docs/POM-DEFINITIONS.md`; the `definition` field of every [`PomDef`] / [`PomMeasure`]
//! repeats the one-line rule so the number is always traceable to a construction.
//!
//! Units are centimetres throughout (the model's native unit, y-up).
//!
//! Scope of "measurable": a POM is measurable (and therefore driven by the fit solver) only
//! when the drafted flat pattern contains the geometry it names.  The elastic-waist relaxed /
//! stretched waist values, the hip *positions* and the drawcord length are construction inputs
//! (`PassThrough` / `Position`): they are reported with `input_only = true` and never driven.
//! See the "CONFIRM IN OPTITEX" section of the doc for the interpretations that a human should
//! verify against Optitex's Measure tool for one size.

use crate::geom::*;
use crate::model::{Pattern, Piece};

/// Which outline a POM is taken on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Line {
    /// The finished sew line (default for every POM here).
    Sew,
    /// The cut line (sew line + seam/hem allowance).
    Cut,
}

/// The kind of measurement a POM is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PomKind {
    /// A horizontal width across a piece (or front+back) at a stated height.
    Width,
    /// A straight (or near-straight) length.
    Length,
    /// A length measured *along a curved seam* (arc length of the sew line).
    CurvedLength,
    /// A construction *position* (a locator, e.g. how far below the top edge a line sits).
    /// Not a dimension of the flat pattern on its own; passed through.
    Position,
    /// A value that is passed straight through from the spec (e.g. an elastic or a cut-only
    /// trim whose finished value is not contained in the flat sew geometry).
    PassThrough,
}

impl PomKind {
    pub fn as_str(self) -> &'static str {
        match self {
            PomKind::Width => "Width",
            PomKind::Length => "Length",
            PomKind::CurvedLength => "CurvedLength",
            PomKind::Position => "Position",
            PomKind::PassThrough => "PassThrough",
        }
    }
}

/// The axis a width/length grows along, used by the fabric-factor pre-compensation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Axis {
    /// Across the body (width-wise).
    X,
    /// Up the body (length-wise).
    Y,
}

/// A static definition of one point of measure.
#[derive(Clone, Copy, Debug)]
pub struct PomDef {
    /// Industry POM code (e.g. "20305").
    pub code: &'static str,
    /// The drafter input field this POM is keyed to (a `PantSpec`/`ShirtSpec` field name, or
    /// `"opts.pant_hem"` for the pant hem fold).  Empty for a pure position.
    pub key: &'static str,
    /// Human-readable name.
    pub name: &'static str,
    /// The kind of measurement.
    pub kind: PomKind,
    /// Which line it is measured on.
    pub on: Line,
    /// The exact one-line definition encoded here.
    pub definition: &'static str,
    /// Axis for fabric-factor pre-compensation (meaningful for Width/Length/CurvedLength).
    pub axis: Axis,
    /// Whether this POM is a pure input (passed through, never solved for).
    pub input_only: bool,
}

/// A measured point of measure.
#[derive(Clone, Debug)]
pub struct PomMeasure {
    pub code: String,
    pub key: String,
    pub name: String,
    /// Measured value in cm (`NaN` for a pure position that the flat pattern does not contain).
    pub value: f64,
    pub kind: PomKind,
    pub definition: String,
    pub input_only: bool,
}

// ---------------------------------------------------------------------------------------
// geometry helpers (all on the sew line, i.e. the piece outline as drafted)
// ---------------------------------------------------------------------------------------

/// Flatten a piece outline to a fine polyline on the sew line.
fn outline(pc: &Piece) -> Vec<V2> {
    pc.flatten(96).0
}

/// Horizontal extent (max-x minus min-x) of a piece where a horizontal line at height `y`
/// crosses its sew outline.  Returns 0 when the line misses the piece.
pub fn horiz_width_at(pc: &Piece, y: f64) -> f64 {
    let pts = outline(pc);
    let n = pts.len();
    let mut xs: Vec<f64> = Vec::new();
    for i in 0..n {
        let a = pts[i];
        let b = pts[(i + 1) % n];
        if (a.y - y) * (b.y - y) <= 0.0 && (a.y - b.y).abs() > 1e-9 {
            let t = (y - a.y) / (b.y - a.y);
            xs.push(a.x + (b.x - a.x) * t);
        }
    }
    if xs.len() < 2 {
        return 0.0;
    }
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    xs[xs.len() - 1] - xs[0]
}

/// Largest x at which a horizontal line at height `y` crosses the sew outline (distance from
/// the x=0 axis, i.e. from CF/CB for fold pieces).
pub fn max_x_at(pc: &Piece, y: f64) -> f64 {
    let pts = outline(pc);
    let n = pts.len();
    let mut best = f64::MIN;
    for i in 0..n {
        let (a, b) = (pts[i], pts[(i + 1) % n]);
        if (a.y - y) * (b.y - y) <= 0.0 && (a.y - b.y).abs() > 1e-9 {
            let t = (y - a.y) / (b.y - a.y);
            best = best.max(a.x + (b.x - a.x) * t);
        }
    }
    if best == f64::MIN { 0.0 } else { best }
}

/// Width of the grown-on placket extension left of CF on the FRT piece (0 if none).
fn placket_ext(pc: &Piece) -> f64 {
    -pc.nodes.iter().map(|n| n.p.x).fold(0.0, f64::min)
}

/// The crotch point of a trouser piece: the start node of the `crotch` edge (where the inseam
/// meets the crotch seam).  `None` if the piece has no crotch edge.
pub fn crotch_point(pc: &Piece) -> Option<V2> {
    pc.nodes.iter().find(|n| n.edge == "crotch").map(|n| n.p)
}

/// Height of the top edge of a piece (max y of its nodes).
pub fn top_edge_y(pc: &Piece) -> f64 {
    pc.nodes.iter().map(|n| n.p.y).fold(f64::MIN, f64::max)
}

/// Seam-allowance stored on the first node of a tagged edge (cut-line distance), if any.
fn edge_sa(pc: &Piece, tag: &str) -> Option<f64> {
    pc.nodes.iter().find(|n| n.edge == tag).and_then(|n| n.sa)
}

fn piece<'a>(p: &'a Pattern, name: &str) -> Option<&'a Piece> {
    p.piece(name)
}

// 12" below the crotch point (the knee line of the chart "KNEE WIDTH 12\"").
const KNEE_DROP: f64 = 30.48;
// base-size hip positions below the top edge (POM 20305-B at CF, 20305-A at the side seam).
// used as the fixed measuring height for the ½ seat width (see docs: seat line convention).
const SEAT_DROP_CF: f64 = 16.0;
const SEAT_DROP_SIDE: f64 = 17.0;
// The sample's drafted pocket mouth runs 5.04 cm horizontally along the waist where the chart
// (22145) says 3.0 cm: the chart value is taken from a different reference than the raw
// horizontal run. We calibrate on the sample: 22145 = horizontal run - 2.04. (CONFIRM IN OPTITEX)
const POCKET_WB_OFFSET: f64 = 2.04;
// the waistband half-length drawn past the stretched half-waist (garments::BELT_OVERLAP).
const BELT_OVERLAP: f64 = 2.5;
// fixed interior length of the drawcord channel (garments::DRAWCORD_INSIDE).
const DRAWCORD_INSIDE: f64 = 105.0;

// ---------------------------------------------------------------------------------------
// pant POM catalogue
// ---------------------------------------------------------------------------------------

/// The full ordered catalogue of pant POMs (matches `garments::PANT_POMS`).
pub fn pant_defs() -> Vec<PomDef> {
    use Axis::*;
    use PomKind::*;
    vec![
        PomDef { code: "20125", key: "half_waist", name: "1/2 waist at top edge (relaxed)", kind: PassThrough, on: Line::Sew, axis: X, input_only: true,
            definition: "Elastic relaxed value. The flat sew top edge equals the STRETCHED waist; the relaxed value is governed by the elastic and passed through. (Flat top edge = FRONT 'waist' + BACK 'waist'.)" },
        PomDef { code: "20245", key: "half_waist_stretched", name: "1/2 waist stretched (min)", kind: PassThrough, on: Line::Sew, axis: X, input_only: true,
            definition: "Elastic stretched minimum = waistband flat half-length minus overlap (belt 'top' - 2.5 cm). Passed through from the spec." },
        PomDef { code: "20305-A", key: "hip_pos_side", name: "hip position at side seam (excl. WB)", kind: Position, on: Line::Sew, axis: Y, input_only: true,
            definition: "Locator: how far below the back top edge the seat is measured. Position input, passed through." },
        PomDef { code: "20305-B", key: "hip_pos_cf", name: "hip position at centre front (excl. WB)", kind: Position, on: Line::Sew, axis: Y, input_only: true,
            definition: "Locator: how far below the front top edge the seat is measured. Position input, passed through." },
        PomDef { code: "20305", key: "half_seat", name: "1/2 seat", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "Horizontal sew width of FRONT at (front top edge - 16 cm) plus BACK at (back top edge - 17 cm)." },
        PomDef { code: "20865", key: "thigh", name: "thigh (1 cm below crotch)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "(horiz width of FRONT 1 cm below its crotch point + same for BACK) / 2." },
        PomDef { code: "21505", key: "front_rise", name: "front rise to top edge (curved)", kind: CurvedLength, on: Line::Sew, axis: Y, input_only: false,
            definition: "Arc length of the FRONT 'crotch' sew curve (crotch point -> waist seam) + waistband width." },
        PomDef { code: "21545", key: "back_rise", name: "back rise to top edge (curved)", kind: CurvedLength, on: Line::Sew, axis: Y, input_only: false,
            definition: "Arc length of the BACK 'crotch' sew curve (crotch point -> waist seam) + waistband width." },
        PomDef { code: "20905", key: "knee", name: "knee width (12\" below crotch)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "(horiz width of FRONT 30.48 cm below its crotch point + same for BACK) / 2." },
        PomDef { code: "21125", key: "leg_opening", name: "1/2 leg opening (straight)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "(FRONT hem straight width + BACK hem straight width) / 2 (the 'hem' edges, measured straight)." },
        PomDef { code: "30210", key: "opts.pant_hem", name: "bottom hem height (fold)", kind: Length, on: Line::Cut, axis: Y, input_only: false,
            definition: "The hem fold-back allowance on the FRONT/BACK 'hem' edge (cut line - sew line)." },
        PomDef { code: "21885", key: "inseam", name: "inseam (along seam)", kind: CurvedLength, on: Line::Sew, axis: Y, input_only: false,
            definition: "(FRONT 'inseam' arc length + BACK 'inseam' arc length) / 2." },
        PomDef { code: "20265", key: "waistband_width", name: "waistband width (finished)", kind: Width, on: Line::Sew, axis: Y, input_only: false,
            definition: "Half the waistband (belt) piece height (it is drawn folded, 2x the finished width)." },
        PomDef { code: "22145", key: "pocket_opening_waist", name: "front pocket opening along WB", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "Horizontal run of the FRONT pocket mouth along the waist (outseam corner x - pocket corner x) minus a 2.04 cm sample calibration (sample run 5.04 <-> chart 3.0)." },
        PomDef { code: "22165", key: "pocket_opening_length", name: "front pocket opening down outseam", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Vertical drop of the FRONT pocket mouth down the outseam (pocket corner y - outseam corner y)." },
        PomDef { code: "22565", key: "pocket_bag_depth", name: "pocket bag depth", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Height (y extent) of the PKT-IN pocket-bag piece." },
        PomDef { code: "30845", key: "drawcord_length", name: "1/2 drawcord length (fold to end)", kind: PassThrough, on: Line::Sew, axis: X, input_only: true,
            definition: "Cut-only trim: (DRAWSTRING length - 105 cm interior) / 2. Passed through from the spec." },
    ]
}

/// Measure every pant POM from a drafted pant [`Pattern`].
pub fn measure_pant(p: &Pattern) -> Vec<PomMeasure> {
    let defs = pant_defs();
    let f = piece(p, "FRONT");
    let b = piece(p, "BACK");
    let belt = piece(p, "WAIST- BELT");
    let pkt = piece(p, "PKT-IN");
    let cord = piece(p, "DRAWSTRING");

    // waistband width (needed by the rises).
    let wb = belt
        .map(|belt| (belt.bounds().1.y - belt.bounds().0.y) / 2.0)
        .unwrap_or(f64::NAN);

    let value = |d: &PomDef| -> f64 {
        match d.code {
            "20125" => match (f, b) {
                (Some(f), Some(b)) => f.tag_len("waist") + b.tag_len("waist"),
                _ => f64::NAN,
            },
            "20245" => belt.map(|belt| belt.tag_len("top") - BELT_OVERLAP).unwrap_or(f64::NAN),
            "20305-A" | "20305-B" => f64::NAN, // pure position: not contained in the flat sew geometry
            "20305" => match (f, b) {
                (Some(f), Some(b)) => {
                    horiz_width_at(f, top_edge_y(f) - SEAT_DROP_CF)
                        + horiz_width_at(b, top_edge_y(b) - SEAT_DROP_SIDE)
                }
                _ => f64::NAN,
            },
            "20865" => match (f, b) {
                (Some(f), Some(b)) => {
                    let (Some(cf), Some(cb)) = (crotch_point(f), crotch_point(b)) else { return f64::NAN };
                    (horiz_width_at(f, cf.y - 1.0) + horiz_width_at(b, cb.y - 1.0)) / 2.0
                }
                _ => f64::NAN,
            },
            "21505" => match f {
                Some(f) => f.tag_len("crotch") + wb,
                None => f64::NAN,
            },
            "21545" => match b {
                Some(b) => b.tag_len("crotch") + wb,
                None => f64::NAN,
            },
            "20905" => match (f, b) {
                (Some(f), Some(b)) => {
                    let (Some(cf), Some(cb)) = (crotch_point(f), crotch_point(b)) else { return f64::NAN };
                    (horiz_width_at(f, cf.y - KNEE_DROP) + horiz_width_at(b, cb.y - KNEE_DROP)) / 2.0
                }
                _ => f64::NAN,
            },
            "21125" => match (f, b) {
                (Some(f), Some(b)) => (f.tag_len("hem") + b.tag_len("hem")) / 2.0,
                _ => f64::NAN,
            },
            "30210" => f.and_then(|f| edge_sa(f, "hem")).unwrap_or(f64::NAN),
            "21885" => match (f, b) {
                (Some(f), Some(b)) => (f.tag_len("inseam") + b.tag_len("inseam")) / 2.0,
                _ => f64::NAN,
            },
            "20265" => wb,
            "22145" => match f {
                Some(f) => {
                    let a4 = f.nodes.iter().find(|n| n.edge == "outseam").map(|n| n.p);
                    let a3 = f.nodes.iter().find(|n| n.edge == "pocket").map(|n| n.p);
                    match (a3, a4) {
                        (Some(a3), Some(a4)) => a4.x - a3.x - POCKET_WB_OFFSET,
                        _ => f64::NAN,
                    }
                }
                None => f64::NAN,
            },
            "22165" => match f {
                Some(f) => {
                    let a4 = f.nodes.iter().find(|n| n.edge == "outseam").map(|n| n.p);
                    let a3 = f.nodes.iter().find(|n| n.edge == "pocket").map(|n| n.p);
                    match (a3, a4) {
                        (Some(a3), Some(a4)) => (a3.y - a4.y).abs(),
                        _ => f64::NAN,
                    }
                }
                None => f64::NAN,
            },
            "22565" => pkt.map(|pkt| pkt.bounds().1.y - pkt.bounds().0.y).unwrap_or(f64::NAN),
            "30845" => cord
                .map(|c| {
                    let (lo, hi) = c.bounds();
                    (hi.x - lo.x - DRAWCORD_INSIDE) / 2.0
                })
                .unwrap_or(f64::NAN),
            _ => f64::NAN,
        }
    };

    defs.iter()
        .map(|d| PomMeasure {
            code: d.code.to_string(),
            key: d.key.to_string(),
            name: d.name.to_string(),
            value: value(d),
            kind: d.kind,
            definition: d.definition.to_string(),
            input_only: d.input_only,
        })
        .collect()
}

// ---------------------------------------------------------------------------------------
// shirt POM catalogue
// ---------------------------------------------------------------------------------------

/// The ordered catalogue of shirt POMs (keyed to `ShirtSpec` field names).
pub fn shirt_defs() -> Vec<PomDef> {
    use Axis::*;
    use PomKind::*;
    vec![
        PomDef { code: "half_chest", key: "half_chest", name: "1/2 chest at underarm", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "FRONT (CF to side) + BACK (CB to side) horizontal sew widths at the underarm line (body_length_hps - armhole_drop); the grown-on placket is excluded." },
        PomDef { code: "half_hem", key: "half_hem", name: "1/2 hem (sweep)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "FRONT 'hem' sew length (CF to side, placket extension excluded) + BACK 'hem' sew length (flat half sweep)." },
        PomDef { code: "across_shoulder", key: "across_shoulder", name: "across shoulder", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "Twice the largest x of the yoke (shoulder tip to shoulder tip)." },
        PomDef { code: "body_length_hps", key: "body_length_hps", name: "body length HPS", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Node-height extent of the FRONT piece: HPS (highest node) down to the CF hem corner (lowest node)." },
        PomDef { code: "back_length_cb", key: "back_length_cb", name: "back length CB", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "BACK piece height + yoke 'cb' length (neck seam at CB down to hem)." },
        PomDef { code: "yoke_depth", key: "yoke_depth", name: "yoke depth at CB", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Length of the yoke 'cb' edge." },
        PomDef { code: "armhole", key: "armhole_drop", name: "armhole girth (derived, informational)", kind: CurvedLength, on: Line::Sew, axis: Y, input_only: true,
            definition: "Derived, not a spec target (the spec drives armhole_drop). FRONT 'armhole' + BACK 'armhole' + yoke 'armhole' arc lengths (full armhole)." },
        PomDef { code: "sleeve_length", key: "sleeve_length", name: "sleeve length", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Height (y extent) of the sleeve piece (cap crest to hem)." },
        PomDef { code: "bicep", key: "bicep", name: "bicep (flat half)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "Half the sleeve width at the bicep line (sleeve_underarm_height above the hem)." },
        PomDef { code: "sleeve_opening", key: "sleeve_opening", name: "sleeve opening (flat half)", kind: Width, on: Line::Sew, axis: X, input_only: false,
            definition: "Half the sleeve 'hem' width." },
        PomDef { code: "neck_size", key: "neck_size", name: "neck / collar size", kind: CurvedLength, on: Line::Sew, axis: X, input_only: false,
            definition: "Twice the collar stand neck seam (BND IN 'neck_front' + 'neck_back'), full neck." },
        PomDef { code: "stand_height", key: "stand_height", name: "collar stand height at CB", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Length of the collar stand (BND IN) 'cb' edge." },
        PomDef { code: "collar_point_length", key: "collar_point_length", name: "collar point length", kind: Length, on: Line::Sew, axis: Y, input_only: false,
            definition: "Length of the collar (CLR) 'point' edge." },
    ]
}

/// Measure every shirt POM from a drafted shirt [`Pattern`].
pub fn measure_shirt(p: &Pattern) -> Vec<PomMeasure> {
    let defs = shirt_defs();
    let frt = piece(p, "FRT");
    let back = piece(p, "back");
    let yoke = piece(p, "back YK");
    let sl = piece(p, "Sleeve");
    let band = piece(p, "BND IN");
    let clr = piece(p, "CLR");

    // underarm line: the END node of the FRT 'side' edge (hem corner -> underarm point).
    let ua_y = frt.and_then(|f| {
        let n = f.nodes.len();
        f.nodes.iter().position(|n| n.edge == "side").map(|i| f.nodes[(i + 1) % n].p.y)
    });

    let value = |d: &PomDef| -> f64 {
        match d.code {
            "half_chest" => match (frt, back, ua_y) {
                (Some(frt), Some(back), Some(y)) => max_x_at(frt, y) + max_x_at(back, y),
                _ => f64::NAN,
            },
            "half_hem" => match (frt, back) {
                (Some(frt), Some(back)) => frt.tag_len("hem") - placket_ext(frt) + back.tag_len("hem"),
                _ => f64::NAN,
            },
            "across_shoulder" => yoke
                .map(|y| 2.0 * y.nodes.iter().map(|n| n.p.x).fold(f64::MIN, f64::max))
                .unwrap_or(f64::NAN),
            "body_length_hps" => frt
                .map(|f| {
                    f.nodes.iter().map(|n| n.p.y).fold(f64::MIN, f64::max)
                        - f.nodes.iter().map(|n| n.p.y).fold(f64::MAX, f64::min)
                })
                .unwrap_or(f64::NAN),
            "back_length_cb" => match (back, yoke) {
                (Some(back), Some(yoke)) => (back.bounds().1.y - back.bounds().0.y) + yoke.tag_len("cb"),
                _ => f64::NAN,
            },
            "yoke_depth" => yoke.map(|y| y.tag_len("cb")).unwrap_or(f64::NAN),
            "armhole" => match (frt, back, yoke) {
                (Some(frt), Some(back), Some(yoke)) => {
                    frt.tag_len("armhole") + back.tag_len("armhole") + yoke.tag_len("armhole")
                }
                _ => f64::NAN,
            },
            "sleeve_length" => sl.map(|s| s.bounds().1.y - s.bounds().0.y).unwrap_or(f64::NAN),
            "bicep" => match sl {
                Some(s) => {
                    // bicep line is sleeve_underarm_height above the hem; the underarm (ub) node
                    // carries the 'underarm_l'/'underarm_r' edges. Measure width at that y.
                    let y = s
                        .nodes
                        .iter()
                        .find(|n| n.edge == "underarm_r")
                        .map(|n| n.p.y)
                        .unwrap_or(f64::NAN);
                    horiz_width_at(s, y) / 2.0
                }
                None => f64::NAN,
            },
            "sleeve_opening" => sl.map(|s| s.tag_len("hem") / 2.0).unwrap_or(f64::NAN),
            "neck_size" => band
                .map(|b| 2.0 * (b.tag_len("neck_front") + b.tag_len("neck_back")))
                .unwrap_or(f64::NAN),
            "stand_height" => band.map(|b| b.tag_len("cb")).unwrap_or(f64::NAN),
            "collar_point_length" => clr.map(|c| c.tag_len("point")).unwrap_or(f64::NAN),
            _ => f64::NAN,
        }
    };

    defs.iter()
        .map(|d| PomMeasure {
            code: d.code.to_string(),
            key: d.key.to_string(),
            name: d.name.to_string(),
            value: value(d),
            kind: d.kind,
            definition: d.definition.to_string(),
            input_only: d.input_only,
        })
        .collect()
}

/// Convenience: measure by garment kind string ("pant"/"shirt").
pub fn measure(kind: &str, p: &Pattern) -> Vec<PomMeasure> {
    match crate::garments::norm_key(kind).as_str() {
        "shirt" => measure_shirt(p),
        _ => measure_pant(p),
    }
}

// ---------------------------------------------------------------------------------------
// tests: definitions on hand-built shapes
// ---------------------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Node;

    fn rect(w: f64, h: f64) -> Piece {
        // CCW rectangle 0,0 -> w,0 -> w,h -> 0,h with tagged edges
        let nodes = vec![
            Node { p: v2(0.0, 0.0), edge: "bottom".into(), ..Default::default() },
            Node { p: v2(w, 0.0), edge: "right".into(), ..Default::default() },
            Node { p: v2(w, h), edge: "top".into(), ..Default::default() },
            Node { p: v2(0.0, h), edge: "left".into(), ..Default::default() },
        ];
        Piece {
            name: "R".into(), zone: "test".into(), nodes,
            grain: (v2(0.0, 0.0), v2(0.0, -10.0)), notches: vec![], darts: vec![],
            internal: vec![], drills: vec![], sa: 1.0, mirror: false, qty: 1, material: "A".into(),
        }
    }

    #[test]
    fn width_of_rectangle() {
        let r = rect(50.0, 20.0);
        // horizontal width anywhere inside the 50x20 rectangle is 50
        assert!((horiz_width_at(&r, 10.0) - 50.0).abs() < 1e-9);
        // "1/2 waist" style: (front top 50 + back top 0)/2 = 25 (illustrative)
        let half = (r.tag_len("top") + 0.0) / 2.0;
        assert!((half - 25.0).abs() < 1e-9);
    }

    #[test]
    fn edge_length_along_known_edge() {
        // an L-shaped three-point open run has length = sum of the two legs
        let r = rect(30.0, 40.0);
        assert!((r.tag_len("bottom") - 30.0).abs() < 1e-9);
        assert!((r.tag_len("left") - 40.0).abs() < 1e-9);
    }

    #[test]
    fn top_edge_and_width_combine_for_half_sum() {
        // two rectangles acting as front (30 wide) and back (26 wide): half sum = 28
        let f = rect(30.0, 100.0);
        let b = rect(26.0, 100.0);
        let half = (horiz_width_at(&f, 50.0) + horiz_width_at(&b, 50.0)) / 2.0;
        assert!((half - 28.0).abs() < 1e-9);
    }

    #[test]
    fn pant_defs_cover_all_poms() {
        // every PANT_POMS code has exactly one def, in order
        let defs = pant_defs();
        let codes: Vec<&str> = defs.iter().map(|d| d.code).collect();
        let want: Vec<&str> = crate::garments::PANT_POMS.iter().map(|(c, _)| *c).collect();
        assert_eq!(codes, want);
    }

    #[test]
    fn measure_pant_default_is_sane() {
        use crate::garments::{draft_pant_detailed, GarmentOpts, PantSpec};
        let p = draft_pant_detailed(&PantSpec::default(), &GarmentOpts::default()).unwrap();
        let m = measure_pant(&p);
        let get = |c: &str| m.iter().find(|x| x.code == c).unwrap().value;
        // seat ~ 53, thigh ~ 33.6, inseam ~ 81, wb 5.2, hem fold 1.5
        assert!((get("20305") - 52.98).abs() < 1.0, "seat {}", get("20305"));
        assert!((get("20865") - 33.6).abs() < 1.0, "thigh {}", get("20865"));
        assert!((get("20265") - 5.2).abs() < 0.01, "wb {}", get("20265"));
        assert!((get("30210") - 1.5).abs() < 0.01, "hem {}", get("30210"));
    }
}
