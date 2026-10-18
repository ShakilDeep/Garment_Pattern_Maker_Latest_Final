//! Pattern validation rules and the regression (golden-file) report.
//!
//! [`validate_pattern`] runs a battery of sewability / fit checks over a [`Pattern`] and returns
//! a list of [`ValIssue`]s (never panics, deterministic, wasm-safe).  The rules are:
//!
//! * **seam-balance** – the two sides of every seam must have equal sewn length within a
//!   tolerance (default 0.2 cm).  Fold/centre seams and sleeve-cap↔armhole seams are handled by
//!   their own rules rather than this one.
//! * **notch-align** – notches that sit on the two sides of a seam must line up (same count,
//!   matching arc-length positions within tolerance).
//! * **cap-ease** – the sleeve-cap length minus the armhole length must fall in a sensible,
//!   garment-aware band.
//! * **collar-fit** – the collar / stand sewn length must match the neckline within tolerance.
//! * **geometry** – no non-finite coordinates, no near-zero area, no self-intersecting sew or
//!   cut outline.
//!
//! Where the existing garment-specific checks ([`crate::garments::garment_checks`]) already
//! encode calibrated expectations for the drafted shirt / pant, this module *wraps and extends*
//! them rather than duplicating the arithmetic.
//!
//! [`golden_report`] drives the regression harness: it re-measures known samples and compares
//! them to embedded reference numbers, returning a machine-readable pass/fail summary for the
//! app.  See `docs/VALIDATION.md`.

use crate::garments::{check_pattern, garment_checks};
use crate::geom::signed_area;
use crate::json::Json;
use crate::model::{Pattern, Piece};

// ===========================================================================================
// Issue model
// ===========================================================================================

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Severity {
    Error,
    Warn,
    Info,
}

impl Severity {
    pub fn as_str(&self) -> &'static str {
        match self {
            Severity::Error => "error",
            Severity::Warn => "warn",
            Severity::Info => "info",
        }
    }
}

/// A single validation finding.  `value` is the measured quantity, `expected` the target, and
/// `tol` the tolerance applied (all in cm where geometric).  `pieces` names the pieces involved.
#[derive(Clone, Debug, PartialEq)]
pub struct ValIssue {
    pub severity: Severity,
    pub rule: String,
    pub detail: String,
    pub pieces: Vec<String>,
    pub value: f64,
    pub expected: f64,
    pub tol: f64,
}

impl ValIssue {
    fn new(sev: Severity, rule: &str, detail: String, pieces: Vec<String>, value: f64, expected: f64, tol: f64) -> ValIssue {
        ValIssue { severity: sev, rule: rule.into(), detail, pieces, value, expected, tol }
    }
    pub fn to_json(&self) -> Json {
        Json::obj()
            .set("severity", Json::str(self.severity.as_str()))
            .set("rule", Json::str(&self.rule))
            .set("detail", Json::str(&self.detail))
            .set("pieces", Json::Arr(self.pieces.iter().map(|p| Json::str(p)).collect()))
            .set("value", Json::num(self.value))
            .set("expected", Json::num(self.expected))
            .set("tol", Json::num(self.tol))
    }
}

// ===========================================================================================
// Configuration
// ===========================================================================================

/// Tolerances for the validation rules.  All lengths in centimetres.
#[derive(Clone, Debug)]
pub struct ValOpts {
    /// Max allowed difference between the two sides of a seam before it is a problem.
    pub seam_tol: f64,
    /// Above `seam_tol` but within this band is reported as a warning (ease); beyond it is an error.
    pub seam_warn_band: f64,
    /// Max allowed notch position mismatch across a seam.
    pub notch_tol: f64,
    /// Minimum acceptable sleeve-cap ease (cap − armhole).
    pub cap_ease_min: f64,
    /// Maximum acceptable sleeve-cap ease as a fraction of the armhole length, plus a floor.
    pub cap_ease_max_frac: f64,
    pub cap_ease_max_floor: f64,
    /// Max allowed collar/stand ↔ neckline difference.
    pub collar_tol: f64,
    /// Area (cm²) at or below which a piece is considered degenerate.
    pub min_area: f64,
}

impl Default for ValOpts {
    fn default() -> Self {
        ValOpts {
            seam_tol: 0.2,
            seam_warn_band: 1.5,
            notch_tol: 0.3,
            cap_ease_min: 0.0,
            cap_ease_max_frac: 0.12,
            cap_ease_max_floor: 4.5,
            collar_tol: 2.0,
            min_area: 1.0,
        }
    }
}

// ===========================================================================================
// Public entry points
// ===========================================================================================

/// Validate a pattern with default tolerances.
pub fn validate_pattern(p: &Pattern) -> Vec<ValIssue> {
    validate_pattern_opts(p, &ValOpts::default())
}

/// Validate a pattern with explicit tolerances.
pub fn validate_pattern_opts(p: &Pattern, o: &ValOpts) -> Vec<ValIssue> {
    let mut issues = Vec::new();
    rule_geometry(p, o, &mut issues);
    rule_seam_balance(p, o, &mut issues);
    rule_notch_align(p, o, &mut issues);
    rule_cap_ease(p, o, &mut issues);
    wrap_garment_checks(p, o, &mut issues);
    issues
}

/// Validation result as JSON: `{issues:[...], counts:{error,warn,info}, ok:bool}`.
pub fn validate_json(p: &Pattern) -> Json {
    let issues = validate_pattern(p);
    issues_to_json(&issues)
}

fn issues_to_json(issues: &[ValIssue]) -> Json {
    let (mut e, mut w, mut i) = (0, 0, 0);
    for it in issues {
        match it.severity {
            Severity::Error => e += 1,
            Severity::Warn => w += 1,
            Severity::Info => i += 1,
        }
    }
    Json::obj()
        .set("issues", Json::Arr(issues.iter().map(|x| x.to_json()).collect()))
        .set(
            "counts",
            Json::obj()
                .set("error", Json::num(e as f64))
                .set("warn", Json::num(w as f64))
                .set("info", Json::num(i as f64)),
        )
        .set("ok", Json::Bool(e == 0))
}

// ===========================================================================================
// Rule (e): degenerate geometry
// ===========================================================================================

fn rule_geometry(p: &Pattern, o: &ValOpts, out: &mut Vec<ValIssue>) {
    for pc in &p.pieces {
        if pc.nodes.len() < 3 {
            out.push(ValIssue::new(
                Severity::Error,
                "geometry",
                format!("piece '{}' has fewer than 3 nodes", pc.name),
                vec![pc.name.clone()],
                pc.nodes.len() as f64,
                3.0,
                0.0,
            ));
            continue;
        }
        let mut nonfinite = false;
        for n in &pc.nodes {
            for v in [n.p.x, n.p.y, n.hin.x, n.hin.y, n.hout.x, n.hout.y] {
                if !v.is_finite() {
                    nonfinite = true;
                }
            }
        }
        if nonfinite {
            out.push(ValIssue::new(
                Severity::Error,
                "geometry",
                format!("piece '{}' has a non-finite coordinate", pc.name),
                vec![pc.name.clone()],
                f64::NAN,
                0.0,
                0.0,
            ));
            continue;
        }
        let (sew, cut) = crate::export::cut_outline(pc);
        let area = signed_area(&sew).abs();
        if area <= o.min_area {
            out.push(ValIssue::new(
                Severity::Error,
                "geometry",
                format!("piece '{}' has near-zero area", pc.name),
                vec![pc.name.clone()],
                area,
                o.min_area,
                0.0,
            ));
        }
        if crate::mesh::self_intersects(&sew) {
            out.push(ValIssue::new(
                Severity::Error,
                "geometry",
                format!("piece '{}' sew outline self-intersects", pc.name),
                vec![pc.name.clone()],
                1.0,
                0.0,
                0.0,
            ));
        }
        if crate::mesh::self_intersects(&cut) {
            out.push(ValIssue::new(
                Severity::Error,
                "geometry",
                format!("piece '{}' cut outline self-intersects (check seam allowances)", pc.name),
                vec![pc.name.clone()],
                1.0,
                0.0,
                0.0,
            ));
        }
    }
    // Catch structural problems the per-piece loop may miss (e.g. a seam referencing a missing
    // edge) by surfacing the authoritative check as a single error.
    if let Err(e) = check_pattern(p) {
        // Only add if not already represented (avoid duplicate geometry spam).
        let already = out.iter().any(|i| e.contains(&i.pieces.first().cloned().unwrap_or_default()) && i.rule == "geometry");
        if !already {
            out.push(ValIssue::new(
                Severity::Error,
                "structure",
                e,
                Vec::new(),
                0.0,
                0.0,
                0.0,
            ));
        }
    }
}

// ===========================================================================================
// Rule (a): seam balance
// ===========================================================================================

fn is_cap_or_armhole(tag: &str) -> bool {
    let t = tag.to_ascii_lowercase();
    t.contains("cap") || t.contains("armhole")
}

/// Seam tags that conventionally join unequal lengths (waistband gather/ease, pocket openings,
/// pocket bags, partial side-seam joins).
fn is_intentional_mismatch(tag: &str) -> bool {
    let t = tag.to_ascii_lowercase();
    ["waist", "opening", "pocket", "bag", "outseam_top"].iter().any(|k| t.contains(k))
}

fn rule_seam_balance(p: &Pattern, o: &ValOpts, out: &mut Vec<ValIssue>) {
    for s in &p.seams {
        // Fold / centre seam joining the two mirrored halves: both sides are identical.
        if s.a_piece == s.b_piece && s.a_tag == s.b_tag {
            continue;
        }
        // Cap/armhole seams carry intentional ease, handled by rule_cap_ease.
        if is_cap_or_armhole(&s.a_tag) || is_cap_or_armhole(&s.b_tag) {
            continue;
        }
        let (pa, pb) = match (p.piece(&s.a_piece), p.piece(&s.b_piece)) {
            (Some(a), Some(b)) => (a, b),
            _ => continue, // missing-piece references are reported by the structure check
        };
        if pa.find_edge(&s.a_tag).is_none() || pb.find_edge(&s.b_tag).is_none() {
            continue;
        }
        let la = pa.tag_len(&s.a_tag);
        let lb = pb.tag_len(&s.b_tag);
        let diff = (la - lb).abs();
        if diff <= o.seam_tol {
            continue;
        }
        // Gathered waists and partial seams (pocket opening onto part of a side seam) are
        // legitimately unequal in the calibrated drafts: report, but never as an error.
        // A side seam whose back piece is split into outseam + outseam_top (pocket section) is only
        // partly joined by this record.
        let split_side = (s.a_tag == "outseam" || s.b_tag == "outseam")
            && (pa.find_edge("outseam_top").is_some() || pb.find_edge("outseam_top").is_some());
        let intentional = split_side || is_intentional_mismatch(&s.a_tag) || is_intentional_mismatch(&s.b_tag);
        let sev = if diff <= o.seam_warn_band || intentional { Severity::Warn } else { Severity::Error };
        out.push(ValIssue::new(
            sev,
            "seam-balance",
            format!(
                "seam {}:{} ({:.3} cm) vs {}:{} ({:.3} cm) differ by {:.3} cm{}",
                s.a_piece, s.a_tag, la, s.b_piece, s.b_tag, lb, diff,
                if intentional { " (gather / partial seam: verify intent)" } else { "" }
            ),
            vec![s.a_piece.clone(), s.b_piece.clone()],
            la,
            lb,
            o.seam_tol,
        ));
    }
}

// ===========================================================================================
// Rule (b): notch alignment across a seam
// ===========================================================================================

/// Arc-length positions (from the seam start) of all notches that sit on the edges making up
/// `tag` of `pc`.  Edges are concatenated in ascending edge index.
fn notch_positions_on_seam(pc: &Piece, tag: &str) -> (Vec<f64>, f64) {
    let seam_edges: Vec<usize> = (0..pc.nodes.len()).filter(|&i| pc.nodes[i].edge == tag).collect();
    // cumulative offset of each seam edge from the seam start
    let mut cum = Vec::with_capacity(seam_edges.len());
    let mut acc = 0.0;
    for &e in &seam_edges {
        cum.push(acc);
        acc += pc.edge_len(e);
    }
    let total = acc;
    let mut pos = Vec::new();
    for n in &pc.notches {
        if let Some(k) = seam_edges.iter().position(|&e| e == n.node) {
            let elen = pc.edge_len(seam_edges[k]);
            pos.push(cum[k] + n.t.clamp(0.0, 1.0) * elen);
        }
    }
    pos.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    (pos, total)
}

fn rule_notch_align(p: &Pattern, o: &ValOpts, out: &mut Vec<ValIssue>) {
    for s in &p.seams {
        if s.a_piece == s.b_piece && s.a_tag == s.b_tag {
            continue; // fold seam
        }
        let (pa, pb) = match (p.piece(&s.a_piece), p.piece(&s.b_piece)) {
            (Some(a), Some(b)) => (a, b),
            _ => continue,
        };
        let (na, _ta) = notch_positions_on_seam(pa, &s.a_tag);
        let (mut nb, tb) = notch_positions_on_seam(pb, &s.b_tag);
        if na.is_empty() && nb.is_empty() {
            continue;
        }
        // When the second side runs opposite, measure its notches from its own end.
        if s.rev {
            for v in nb.iter_mut() {
                *v = tb - *v;
            }
            nb.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        }
        if na.len() != nb.len() {
            out.push(ValIssue::new(
                Severity::Warn,
                "notch-align",
                format!(
                    "seam {}:{} has {} notch(es) but {}:{} has {}",
                    s.a_piece, s.a_tag, na.len(), s.b_piece, s.b_tag, nb.len()
                ),
                vec![s.a_piece.clone(), s.b_piece.clone()],
                na.len() as f64,
                nb.len() as f64,
                0.0,
            ));
            continue;
        }
        for (i, (a, b)) in na.iter().zip(nb.iter()).enumerate() {
            let diff = (a - b).abs();
            if diff > o.notch_tol {
                out.push(ValIssue::new(
                    Severity::Warn,
                    "notch-align",
                    format!(
                        "seam {}:{} notch #{} at {:.2} cm vs {:.2} cm (Δ {:.2} cm)",
                        s.a_piece, s.a_tag, i + 1, a, b, diff
                    ),
                    vec![s.a_piece.clone(), s.b_piece.clone()],
                    *a,
                    *b,
                    o.notch_tol,
                ));
            }
        }
    }
}

// ===========================================================================================
// Rule (c): sleeve-cap ease (generic, seam-driven)
// ===========================================================================================

fn rule_cap_ease(p: &Pattern, o: &ValOpts, out: &mut Vec<ValIssue>) {
    // Sum lengths over seams that join a "cap*" tag to an "armhole*" tag.
    let mut cap_total = 0.0;
    let mut arm_total = 0.0;
    let mut cap_pieces: Vec<String> = Vec::new();
    let mut found = false;
    for s in &p.seams {
        let a = s.a_tag.to_ascii_lowercase();
        let b = s.b_tag.to_ascii_lowercase();
        let (cap_side, arm_side) = if a.contains("cap") && b.contains("armhole") {
            (Some((&s.a_piece, &s.a_tag)), Some((&s.b_piece, &s.b_tag)))
        } else if b.contains("cap") && a.contains("armhole") {
            (Some((&s.b_piece, &s.b_tag)), Some((&s.a_piece, &s.a_tag)))
        } else {
            (None, None)
        };
        if let (Some((cp, ct)), Some((ap, at))) = (cap_side, arm_side) {
            if let (Some(cpi), Some(api)) = (p.piece(cp), p.piece(ap)) {
                cap_total += cpi.tag_len(ct);
                arm_total += api.tag_len(at);
                found = true;
                if !cap_pieces.contains(cp) {
                    cap_pieces.push(cp.clone());
                }
                if !cap_pieces.contains(ap) {
                    cap_pieces.push(ap.clone());
                }
            }
        }
    }
    if !found || arm_total <= 0.0 {
        return;
    }
    let ease = cap_total - arm_total;
    let max_ease = (arm_total * o.cap_ease_max_frac).max(o.cap_ease_max_floor);
    if ease < o.cap_ease_min || ease > max_ease {
        let sev = if ease < -o.cap_ease_max_floor || ease > max_ease * 2.0 {
            Severity::Error
        } else {
            Severity::Warn
        };
        out.push(ValIssue::new(
            sev,
            "cap-ease",
            format!(
                "sleeve cap ease {:.2} cm (cap {:.2} − armhole {:.2}) outside band [{:.2}, {:.2}]",
                ease, cap_total, arm_total, o.cap_ease_min, max_ease
            ),
            cap_pieces,
            ease,
            (o.cap_ease_min + max_ease) / 2.0,
            (max_ease - o.cap_ease_min) / 2.0,
        ));
    } else {
        out.push(ValIssue::new(
            Severity::Info,
            "cap-ease",
            format!("sleeve cap ease {:.2} cm within band [{:.2}, {:.2}]", ease, o.cap_ease_min, max_ease),
            cap_pieces,
            ease,
            (o.cap_ease_min + max_ease) / 2.0,
            (max_ease - o.cap_ease_min) / 2.0,
        ));
    }
}

// ===========================================================================================
// Rules (c)+(d) extension: wrap the calibrated garment_checks
// ===========================================================================================

fn classify_check(name: &str) -> (&'static str, Severity) {
    let n = name.to_ascii_lowercase();
    if n.contains("pocket") || n.contains("pkt") {
        // pocket seam pairings are inferred from the sample geometry, not from a seam table: warn only
        ("seam-balance", Severity::Warn)
    } else if n.contains("cap") || n.contains("ease") {
        ("cap-ease", Severity::Warn)
    } else if n.contains("neck") || n.contains("stand") || n.contains("collar") {
        ("collar-fit", Severity::Warn)
    } else {
        ("seam-balance", Severity::Error)
    }
}

fn wrap_garment_checks(p: &Pattern, _o: &ValOpts, out: &mut Vec<ValIssue>) {
    for c in garment_checks(p) {
        let ok = (c.value - c.expected).abs() <= c.tol;
        let (rule, fail_sev) = classify_check(&c.name);
        // Skip generic cap-ease duplication: rule_cap_ease already emitted a cap entry, but the
        // garment-specific one is the calibrated authority, so keep it and drop ours by matching.
        if rule == "cap-ease" {
            out.retain(|i| i.rule != "cap-ease");
        }
        let sev = if ok { Severity::Info } else { fail_sev };
        out.push(ValIssue::new(
            sev,
            rule,
            format!(
                "{}: {:.3} vs expected {:.3} (tol {:.3})",
                c.name, c.value, c.expected, c.tol
            ),
            Vec::new(),
            c.value,
            c.expected,
            c.tol,
        ));
    }
}

// ===========================================================================================
// Golden-file regression harness (#43 / #45)
// ===========================================================================================

/// One golden comparison: a measured quantity against a stored reference within a tolerance.
struct GoldenCase {
    name: &'static str,
    measured: f64,
    expected: f64,
    tol: f64,
}

impl GoldenCase {
    fn pass(&self) -> bool {
        self.measured.is_finite() && (self.measured - self.expected).abs() <= self.tol
    }
    fn to_json(&self) -> Json {
        Json::obj()
            .set("name", Json::str(self.name))
            .set("measured", Json::num(self.measured))
            .set("expected", Json::num(self.expected))
            .set("tol", Json::num(self.tol))
            .set("pass", Json::Bool(self.pass()))
    }
}

// ---- Embedded reference numbers (the "golden" values) -------------------------------------
// Pant geometry, base size S, decoded from samples/pant_1074664.PDS and cross-checked against
// the embedded Optitex GEOM_INFO numbers (see src/pds_bin.rs tests).
const PANT_BELT_S_W: f64 = 105.6;
const PANT_BELT_S_H: f64 = 13.0;
const PANT_BELT_S_PER: f64 = 237.2;
const PANT_FRONT_S_W: f64 = 108.8272;
const PANT_FRONT_S_H: f64 = 31.8795;
// Graded spec sheet, POM 20125 (1/2 waist at top edge) across XS..XXL and inseam 21885.
const SPEC_POM_20125: [f64; 6] = [33.0, 35.0, 37.0, 39.5, 42.0, 44.5];
const SPEC_POM_21885: [f64; 6] = [77.0, 78.0, 79.0, 80.0, 81.0, 82.0];

fn bbox(poly: &[(f64, f64)]) -> (f64, f64, f64) {
    let (mut x0, mut x1, mut y0, mut y1) = (f64::MAX, f64::MIN, f64::MAX, f64::MIN);
    for &(x, y) in poly {
        x0 = x0.min(x);
        x1 = x1.max(x);
        y0 = y0.min(y);
        y1 = y1.max(y);
    }
    let per: f64 = (0..poly.len())
        .map(|i| {
            let a = poly[i];
            let b = poly[(i + 1) % poly.len()];
            ((b.0 - a.0).powi(2) + (b.1 - a.1).powi(2)).sqrt()
        })
        .sum();
    (x1 - x0, y1 - y0, per)
}

/// Run the regression harness over whatever samples are supplied and return a JSON summary:
/// `{cases:[{name,measured,expected,tol,pass}], passed, failed, ok}`.
///
/// Pass `None` for a sample that is not available; its cases are simply omitted.  This is pure
/// (no file IO) so it is wasm-safe and the host supplies the bytes.
pub fn golden_report(pant_pds: Option<&[u8]>, spec_xlsx: Option<&[u8]>) -> Json {
    let mut cases: Vec<GoldenCase> = Vec::new();

    if let Some(bytes) = pant_pds {
        if let Ok(doc) = crate::pds_bin::decode(bytes) {
            let find = |name: &str, size: &str| {
                doc.pieces.iter().find(|p| p.name == name && p.size == size)
            };
            if let Some(belt) = find("WAIST- BELT", "S") {
                let (w, h, per) = bbox(&belt.cut);
                cases.push(GoldenCase { name: "pant/belt-S/width", measured: w, expected: PANT_BELT_S_W, tol: 0.05 });
                cases.push(GoldenCase { name: "pant/belt-S/height", measured: h, expected: PANT_BELT_S_H, tol: 0.05 });
                cases.push(GoldenCase { name: "pant/belt-S/perimeter", measured: per, expected: PANT_BELT_S_PER, tol: 0.1 });
            }
            if let Some(front) = find("FRONT", "S") {
                let (w, h, _per) = bbox(&front.cut);
                cases.push(GoldenCase { name: "pant/front-S/width", measured: w, expected: PANT_FRONT_S_W, tol: 0.01 });
                cases.push(GoldenCase { name: "pant/front-S/height", measured: h, expected: PANT_FRONT_S_H, tol: 0.01 });
            }
        } else {
            cases.push(GoldenCase { name: "pant/decode", measured: 0.0, expected: 1.0, tol: 0.0 });
        }
    }

    if let Some(bytes) = spec_xlsx {
        match crate::xlsx_read::read_xlsx(bytes) {
            Ok(sheets) => {
                if let Some(sheet) = sheets.iter().find(|s| s.name.to_ascii_lowercase().contains("graded")) {
                    let row20125 = find_pom_row(sheet, "20125");
                    let row21885 = find_pom_row(sheet, "21885");
                    for (i, &exp) in SPEC_POM_20125.iter().enumerate() {
                        let m = row20125.as_ref().and_then(|r| r.get(i).copied()).unwrap_or(f64::NAN);
                        cases.push(GoldenCase {
                            name: pom_case_name("20125", i),
                            measured: m,
                            expected: exp,
                            tol: 1e-9,
                        });
                    }
                    for (i, &exp) in SPEC_POM_21885.iter().enumerate() {
                        let m = row21885.as_ref().and_then(|r| r.get(i).copied()).unwrap_or(f64::NAN);
                        cases.push(GoldenCase {
                            name: pom_case_name("21885", i),
                            measured: m,
                            expected: exp,
                            tol: 1e-9,
                        });
                    }
                } else {
                    cases.push(GoldenCase { name: "spec/graded-sheet-present", measured: 0.0, expected: 1.0, tol: 0.0 });
                }
            }
            Err(_) => {
                cases.push(GoldenCase { name: "spec/read", measured: 0.0, expected: 1.0, tol: 0.0 });
            }
        }
    }

    let passed = cases.iter().filter(|c| c.pass()).count();
    let failed = cases.len() - passed;
    Json::obj()
        .set("cases", Json::Arr(cases.iter().map(|c| c.to_json()).collect()))
        .set("passed", Json::num(passed as f64))
        .set("failed", Json::num(failed as f64))
        .set("ok", Json::Bool(failed == 0))
}

fn pom_case_name(pom: &str, col: usize) -> &'static str {
    // Return a stable &'static name without allocation churn in the struct.
    // (We only have a handful of combinations.)
    match (pom, col) {
        ("20125", 0) => "spec/20125/XS",
        ("20125", 1) => "spec/20125/S",
        ("20125", 2) => "spec/20125/M",
        ("20125", 3) => "spec/20125/L",
        ("20125", 4) => "spec/20125/XL",
        ("20125", 5) => "spec/20125/XXL",
        ("21885", 0) => "spec/21885/XS",
        ("21885", 1) => "spec/21885/S",
        ("21885", 2) => "spec/21885/M",
        ("21885", 3) => "spec/21885/L",
        ("21885", 4) => "spec/21885/XL",
        ("21885", 5) => "spec/21885/XXL",
        _ => "spec/pom",
    }
}

/// Find the measurement row whose first column is the given POM code, returning the six graded
/// size values.  On this chart the size grid occupies columns 4..=9 (XS..XXL) after the POM,
/// English name, spacer and Turkish-name columns.
fn find_pom_row(sheet: &crate::xlsx_read::Sheet, pom: &str) -> Option<Vec<f64>> {
    const SIZE_COLS: std::ops::Range<usize> = 4..10;
    for row in &sheet.rows {
        if row.first().map(|c| c.text.trim() == pom).unwrap_or(false) {
            return Some(
                SIZE_COLS
                    .map(|c| row.get(c).and_then(|cell| cell.num).unwrap_or(f64::NAN))
                    .collect(),
            );
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geom::v2;
    use crate::model::{Node, Seam};

    fn square_piece(name: &str, size: f64, tags: [&str; 4]) -> Piece {
        Piece {
            name: name.into(),
            zone: "upper".into(),
            nodes: vec![
                Node::corner(0.0, 0.0, tags[0]),
                Node::corner(size, 0.0, tags[1]),
                Node::corner(size, size, tags[2]),
                Node::corner(0.0, size, tags[3]),
            ],
            grain: (v2(0.0, 0.0), v2(0.0, -10.0)),
            notches: Vec::new(),
            darts: Vec::new(),
            internal: Vec::new(),
            drills: Vec::new(),
            sa: 1.0,
            mirror: false,
            qty: 1,
            material: "SELF".into(),
        }
    }

    #[test]
    fn clean_pattern_has_no_errors() {
        let a = square_piece("A", 10.0, ["bottom", "right", "top", "left"]);
        let mut b = square_piece("B", 10.0, ["bottom", "left", "top", "right"]);
        b.nodes[0].p = v2(0.0, 0.0);
        let p = Pattern {
            style: "t".into(),
            size: "M".into(),
            garment: "custom".into(),
            pieces: vec![a, b],
            seams: vec![Seam {
                a_piece: "A".into(),
                a_tag: "right".into(),
                b_piece: "B".into(),
                b_tag: "right".into(),
                rev: false,
            }],
        };
        let issues = validate_pattern(&p);
        let errs: Vec<_> = issues.iter().filter(|i| i.severity == Severity::Error).collect();
        assert!(errs.is_empty(), "unexpected errors: {:?}", errs);
    }

    #[test]
    fn unequal_seam_flagged() {
        let a = square_piece("A", 10.0, ["bottom", "right", "top", "left"]);
        let b = square_piece("B", 20.0, ["bottom", "right", "top", "left"]);
        let p = Pattern {
            style: "t".into(),
            size: "M".into(),
            garment: "custom".into(),
            pieces: vec![a, b],
            seams: vec![Seam {
                a_piece: "A".into(),
                a_tag: "right".into(),
                b_piece: "B".into(),
                b_tag: "right".into(),
                rev: false,
            }],
        };
        let issues = validate_pattern(&p);
        assert!(
            issues.iter().any(|i| i.rule == "seam-balance" && i.severity == Severity::Error),
            "expected a seam-balance error, got {:?}",
            issues
        );
    }

    #[test]
    fn degenerate_geometry_flagged() {
        // three collinear points -> near-zero area
        let mut pc = square_piece("Flat", 10.0, ["a", "b", "c", "d"]);
        pc.nodes = vec![
            Node::corner(0.0, 0.0, "a"),
            Node::corner(10.0, 0.0, "b"),
            Node::corner(20.0, 0.0, "c"),
        ];
        let p = Pattern {
            style: "t".into(),
            size: "M".into(),
            garment: "custom".into(),
            pieces: vec![pc],
            seams: Vec::new(),
        };
        let issues = validate_pattern(&p);
        assert!(issues.iter().any(|i| i.rule == "geometry" && i.severity == Severity::Error));
    }

    #[test]
    fn drafted_garments_have_no_validation_errors() {
        use crate::garments::{draft_pant_detailed, draft_shirt, GarmentOpts, PantSpec, ShirtSpec};
        let o = GarmentOpts::default();
        let shirt = draft_shirt(&ShirtSpec::default(), &o).unwrap();
        let pant = draft_pant_detailed(&PantSpec::default(), &o).unwrap();
        for p in [&shirt, &pant] {
            let issues = validate_pattern(p);
            let errs: Vec<_> = issues.iter().filter(|i| i.severity == Severity::Error).collect();
            assert!(errs.is_empty(), "{}: {:?}", p.garment, errs);
            let j = validate_json(p);
            assert_eq!(j.get("ok").and_then(|v| v.as_bool()), Some(true));
        }
        // the shirt must report a cap-ease finding
        assert!(validate_pattern(&shirt).iter().any(|i| i.rule == "cap-ease"));
    }

    #[test]
    fn cap_ease_out_of_band_and_notch_mismatch_flagged() {
        use crate::garments::{draft_shirt, GarmentOpts, ShirtSpec};
        let mut shirt = draft_shirt(&ShirtSpec::default(), &GarmentOpts::default()).unwrap();
        // inflate the sleeve cap: scale every sleeve node x by 1.5
        if let Some(sl) = shirt.pieces.iter_mut().find(|p| p.name == "Sleeve") {
            for n in sl.nodes.iter_mut() {
                n.p.x *= 1.5;
                n.hin.x *= 1.5;
                n.hout.x *= 1.5;
            }
        }
        let issues = validate_pattern(&shirt);
        assert!(issues.iter().any(|i| i.rule == "cap-ease" && i.severity != Severity::Info), "{:?}", issues);
    }

    #[test]
    fn never_panics_on_nonfinite() {
        let mut pc = square_piece("N", 10.0, ["a", "b", "c", "d"]);
        pc.nodes[1].p.x = f64::NAN;
        pc.nodes[2].hout.y = f64::INFINITY;
        let p = Pattern { style: "t".into(), size: "M".into(), garment: "custom".into(), pieces: vec![pc], seams: vec![Seam { a_piece: "N".into(), a_tag: "zz".into(), b_piece: "Q".into(), b_tag: "a".into(), rev: true }] };
        let issues = validate_pattern(&p);
        assert!(issues.iter().any(|i| i.rule == "geometry" && i.severity == Severity::Error));
        let _ = validate_json(&p).to_string();
    }

    #[test]
    fn json_shape() {
        let a = square_piece("A", 10.0, ["bottom", "right", "top", "left"]);
        let p = Pattern {
            style: "t".into(),
            size: "M".into(),
            garment: "custom".into(),
            pieces: vec![a],
            seams: Vec::new(),
        };
        let j = validate_json(&p);
        assert!(j.get("issues").is_some());
        assert!(j.get("counts").is_some());
        assert!(j.get("ok").is_some());
    }
}
