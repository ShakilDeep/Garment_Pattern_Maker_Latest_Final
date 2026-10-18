//! Single JSON entry point shared by the WASM module, the CLI and tests.
//! Request:  {"op": "...", ...}      Response: {"ok":true, ...} | {"ok":false,"error":"..."}
use crate::draft::{checks, draft, DraftOpts};
use crate::edit;
use crate::export;
use crate::geom::*;
use crate::grade::{default_rules, grade, grade_table};
use crate::json::Json;
use crate::mesh;
use crate::model::*;
use crate::sim::{simulate, Column, SimParams};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub fn call(req: &str) -> String {
    match Json::parse(req).map_err(|e| format!("bad request JSON: {}", e)).and_then(|j| dispatch(&j)) {
        Ok(j) => j.set("ok", Json::Bool(true)).to_string(),
        Err(e) => Json::obj().set("ok", Json::Bool(false)).set("error", Json::Str(e)).to_string(),
    }
}

fn num(j: &Json, k: &str, d: f64) -> f64 { j.get(k).and_then(|v| v.as_f64()).filter(|v| v.is_finite()).unwrap_or(d) }

fn req_str<'a>(j: &'a Json, k: &str) -> Result<&'a str, String> {
    j.get(k).and_then(|v| v.as_str()).ok_or_else(|| format!("missing string field '{}'", k))
}

fn measurements_of(j: &Json) -> Result<Measurements, String> {
    match j.get("measurements") {
        Some(m) => {
            let (m, _) = Measurements::from_json(m)?;
            Ok(m)
        }
        None => Ok(Measurements::default()),
    }
}

fn opts_of(j: &Json) -> DraftOpts {
    let mut o = DraftOpts::default();
    if let Some(x) = j.get("opts") {
        o.bust_ease = num(x, "bust_ease", o.bust_ease).clamp(0.0, 40.0);
        o.waist_ease = num(x, "waist_ease", o.waist_ease).clamp(0.0, 40.0);
        o.hip_ease = num(x, "hip_ease", o.hip_ease).clamp(0.0, 40.0);
        o.cap_ease = num(x, "cap_ease", o.cap_ease).clamp(0.0, 10.0);
        o.sleeve_ease = num(x, "sleeve_ease", o.sleeve_ease).clamp(0.0, 30.0);
        o.sa = num(x, "sa", o.sa).clamp(0.0, 5.0);
        o.hem_sa = num(x, "hem_sa", o.hem_sa).clamp(0.0, 10.0);
    }
    o
}

fn pt(p: V2) -> Json { Json::nums(&[p.x, p.y]) }
fn poly(p: &[V2]) -> Json { Json::Arr(p.iter().map(|q| pt(*q)).collect()) }

fn dispatch(j: &Json) -> Result<Json, String> {
    let op = req_str(j, "op")?;
    match op {
        "version" => Ok(Json::obj().set("version", Json::str(VERSION))),
        "defaults" => Ok(Json::obj()
            .set("measurements", Measurements::default().to_json())
            .set("keys", Json::Arr(MEASURE_KEYS.iter().map(|k| Json::str(k)).collect()))
            .set("garments", Json::Arr(["bodice", "skirt", "trousers"].iter().map(|k| Json::str(k)).collect()))
            .set("rules", Json::Arr(default_rules().iter().map(|(k, v)| Json::obj().set("key", Json::str(k)).set("step", Json::num(*v))).collect()))),
        "parse_measurements" => {
            let text = req_str(j, "text")?;
            let inches = j.get("units").and_then(|v| v.as_str()) == Some("in");
            let base = match j.get("base") { Some(b) => Measurements::from_json(b)?.0, None => Measurements::default() };
            let (m, warnings) = parse_measurements_text(text, inches, &base)?;
            Ok(Json::obj().set("measurements", m.to_json()).set("warnings", Json::Arr(warnings.into_iter().map(Json::Str).collect())))
        }
        "draft" => {
            let g = req_str(j, "garment")?;
            let m = measurements_of(j)?;
            let o = opts_of(j);
            let p = draft(g, &m, &o)?;
            let cs = checks(&p, &m, &o);
            Ok(Json::obj()
                .set("pattern", p.to_json())
                .set("measurements", m.to_json())
                .set("checks", Json::Arr(cs.iter().map(|c| Json::obj().set("name", Json::str(&c.name)).set("value", Json::num(c.value))
                    .set("expected", Json::num(c.expected)).set("tol", Json::num(c.tol)).set("ok", Json::Bool(c.ok()))).collect())))
        }
        "grade" => {
            let g = req_str(j, "garment")?;
            let m = measurements_of(j)?;
            let o = opts_of(j);
            let steps: Vec<i32> = match j.get("steps").and_then(|v| v.as_arr()) {
                Some(a) => a.iter().filter_map(|v| v.as_f64()).map(|v| v as i32).filter(|v| v.abs() <= 6).collect(),
                None => vec![-1, 0, 1],
            };
            if steps.is_empty() || steps.len() > 9 { return Err("steps must contain 1–9 size steps in -6..6".into()); }
            let mut rules = default_rules();
            if let Some(r) = j.get("rules").and_then(|v| v.as_arr()) {
                for x in r {
                    if let (Some(k), Some(v)) = (x.get("key").and_then(|v| v.as_str()), x.get("step").and_then(|v| v.as_f64())) {
                        if let Some(e) = rules.iter_mut().find(|(kk, _)| kk == k) { e.1 = v.clamp(-20.0, 20.0); }
                    }
                }
            }
            let sizes = grade(g, &m, &o, &rules, &steps)?;
            let base = draft(g, &m, &o)?;
            let arr: Vec<Json> = sizes.iter().map(|s| {
                let table: Vec<Json> = grade_table(&base, &s.pattern).into_iter()
                    .map(|(n, d)| Json::obj().set("piece", Json::Str(n)).set("deltas", poly(&d))).collect();
                Json::obj().set("label", Json::str(&s.label)).set("step", Json::num(s.step as f64))
                    .set("measurements", s.measurements.to_json()).set("pattern", s.pattern.to_json()).set("table", Json::Arr(table))
            }).collect();
            Ok(Json::obj().set("sizes", Json::Arr(arr)))
        }
        "geometry" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let pieces: Vec<Json> = p.pieces.iter().map(|pc| {
                let (sew, cut) = export::cut_outline(pc);
                let (lo, hi) = pc.bounds();
                let mut notches = Vec::new();
                for n in &pc.notches {
                    if n.node < pc.nodes.len() {
                        let e = pc.edge_polyline(n.node, 32);
                        let (q, t) = point_at(&e, n.t * poly_len(&e));
                        notches.push(Json::obj().set("p", pt(q)).set("tan", pt(t)).set("kind", Json::str(&n.kind)));
                    }
                }
                Json::obj().set("name", Json::str(&pc.name)).set("sew", poly(&sew)).set("cut", poly(&cut))
                    .set("min", pt(lo)).set("max", pt(hi)).set("area", Json::num(pc.area()))
                    .set("notches", Json::Arr(notches))
                    .set("edges", Json::Arr((0..pc.nodes.len()).map(|i| Json::obj().set("tag", Json::str(&pc.nodes[i].edge)).set("len", Json::num(pc.edge_len(i))).set("pts", poly(&pc.edge_polyline(i, 24)))).collect()))
            }).collect();
            Ok(Json::obj().set("pieces", Json::Arr(pieces)))
        }
        "edit" => {
            let mut p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let a = j.get("action").ok_or("missing action")?;
            apply_edit(&mut p, a)?;
            Ok(Json::obj().set("pattern", p.to_json()))
        }
        "export_dxf" => {
            let style = j.get("style").and_then(|v| v.as_str()).unwrap_or("STYLE").to_string();
            let mut owned: Vec<(String, Pattern)> = Vec::new();
            if let Some(a) = j.get("sizes").and_then(|v| v.as_arr()) {
                for s in a {
                    owned.push((s.get("label").and_then(|v| v.as_str()).unwrap_or("M").to_string(),
                        Pattern::from_json(s.get("pattern").ok_or("size missing pattern")?)?));
                }
            } else {
                let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
                owned.push((p.size.clone(), p));
            }
            if owned.is_empty() { return Err("nothing to export".into()); }
            let refs: Vec<(String, &Pattern)> = owned.iter().map(|(l, p)| (l.clone(), p)).collect();
            let mode = j.get("mode").and_then(|v| v.as_str()).unwrap_or("polyline");
            let mut eo = export::ExportOpts::polyline();
            if let Some(t) = j.get("chord_tol").and_then(|v| v.as_f64()) { eo.chord_tol = t; }
            if mode == "spline" || mode == "graded_spline" { eo.curves = export::CurveMode::Spline; }
            let text = if mode.starts_with("graded") {
                let base = j.get("base").and_then(|v| v.as_str()).unwrap_or(&refs[0].0).to_string();
                export::dxf_graded_opts(&refs, &base, &style, &eo)
            } else { export::dxf_aama_opts(&refs, &style, &eo) };
            Ok(Json::obj().set("dxf", Json::Str(text)).set("filename", Json::Str(format!("{}.dxf", style.replace(' ', "_")))))
        }
        "export_svg" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let cut = j.get("cut").and_then(|v| v.as_bool()).unwrap_or(true);
            Ok(Json::obj().set("svg", Json::Str(export::to_svg(&p, cut))))
        }
        "export_pds" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            export::export_pds(&p).map(|_| Json::obj())
        }
        "import_pds" => crate::pds_api::import_pds(j),
        "parse_spec" => crate::pds_api::parse_spec(j),
        "nest" => crate::pds_api::nest(j),
        "draft_spec" => crate::pds_api::draft_spec(j),
        "validate" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            Ok(crate::validate::validate_json(&p))
        }
        "golden_report" => {
            let dec = |k: &str| j.get(k).and_then(|v| v.as_str()).map(crate::pds_api::b64_decode).transpose();
            let (pds, xlsx) = (dec("pds_b64")?, dec("xlsx_b64")?);
            Ok(crate::validate::golden_report(pds.as_deref(), xlsx.as_deref()))
        }
        "xlsx_to_tsv" => {
            let b64 = j.get("data_b64").and_then(|v| v.as_str()).ok_or("missing data_b64")?;
            let bytes = crate::pds_api::b64_decode(b64)?;
            let sheets = crate::xlsx_read::read_xlsx(&bytes)?;
            Ok(Json::obj().set("sheets", Json::Arr(sheets.iter().map(|s|
                Json::obj().set("name", Json::str(&s.name))
                           .set("tsv", Json::str(&crate::xlsx_read::sheet_to_tsv(s)))).collect())))
        }
        "fit_spec" => {
            let kind = j.get("garment").and_then(|v| v.as_str()).ok_or("missing garment")?;
            let sheet = j.get("spec").ok_or("missing spec")?;
            let size = j.get("size").and_then(|v| v.as_str());
            crate::fit::fit_json(kind, sheet, size, j.get("factors"))
        }
        "measure" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let kind = j.get("garment").and_then(|v| v.as_str()).map(|s| s.to_string()).unwrap_or_else(|| {
                if p.pieces.iter().any(|q| q.name.eq_ignore_ascii_case("FRT") || q.name.eq_ignore_ascii_case("CLR") || q.name.eq_ignore_ascii_case("Sleeve")) { "shirt".into() } else { "pant".into() }
            });
            let rows: Vec<Json> = crate::pom::measure(&kind, &p).iter().map(|m| Json::obj()
                .set("code", Json::str(&m.code)).set("name", Json::str(&m.name)).set("value", Json::num(m.value))
                .set("kind", Json::str(m.kind.as_str())).set("definition", Json::str(&m.definition))
                .set("input_only", Json::Bool(m.input_only))).collect();
            Ok(Json::obj().set("garment", Json::str(&kind)).set("rows", Json::Arr(rows)))
        }
        "map_targets" => {
            let g = j.get("garment").and_then(|v| v.as_str()).unwrap_or("pant");
            Ok(Json::obj().set("targets", Json::Arr(crate::spec::map_targets(g).into_iter()
                .map(|(k, l)| Json::obj().set("key", Json::str(k)).set("label", Json::str(&l))).collect())))
        }
        "mesh_info" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let mut out = Vec::new();
            for pc in &p.pieces {
                let m = mesh::build_mesh(pc, 3.2)?;
                out.push(Json::obj().set("name", Json::str(&pc.name)).set("vertices", Json::num(m.pos.len() as f64)).set("triangles", Json::num(m.tris.len() as f64)));
            }
            Ok(Json::obj().set("meshes", Json::Arr(out)))
        }
        "drape" => {
            let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
            let m = measurements_of(j)?;
            let mut prm = SimParams::default();
            if let Some(x) = j.get("params") {
                prm.steps = num(x, "steps", prm.steps as f64).clamp(10.0, 600.0) as usize;
                prm.frames = num(x, "frames", prm.frames as f64).clamp(1.0, 24.0) as usize;
                prm.hmax = num(x, "hmax", prm.hmax).clamp(2.0, 6.0);
            }
            let r = simulate(&p, &m, &prm)?;
            let col = |c: &Column| Json::obj().set("cx", Json::num(c.cx)).set("cz", Json::num(c.cz))
                .set("ys", Json::nums(&c.ys)).set("a", Json::nums(&c.a)).set("b", Json::nums(&c.b));
            let meshes: Vec<Json> = r.meshes.iter().map(|sm| {
                let tris: Vec<f64> = sm.tris.iter().flat_map(|t| t.iter().map(|&i| i as f64)).collect();
                let frames: Vec<Json> = sm.frames.iter().map(|f| Json::Arr(f.iter().map(|v| Json::Num((v * 100.0).round() / 100.0)).collect())).collect();
                Json::obj().set("name", Json::str(&sm.name)).set("zone", Json::str(&sm.zone)).set("side", Json::num(sm.side as f64))
                    .set("tris", Json::nums(&tris)).set("frames", Json::Arr(frames))
            }).collect();
            let s = &r.stats;
            Ok(Json::obj().set("meshes", Json::Arr(meshes))
                .set("body", Json::obj().set("torso", col(&r.body.torso)).set("skirt_core", col(&r.body.skirt_core))
                    .set("legs", Json::Arr(r.body.legs.iter().map(col).collect())).set("arms", Json::Arr(r.body.arms.iter().map(col).collect())))
                .set("stats", Json::obj().set("particles", Json::num(s.particles as f64)).set("max_penetration", Json::num(s.max_penetration))
                    .set("stitch_mean_final", Json::num(s.stitch_mean_final)).set("stitch_max_final", Json::num(s.stitch_max_final))
                    .set("max_stretch_ratio", Json::num(s.max_stretch_ratio)).set("stretch_p95", Json::num(s.stretch_p95)).set("max_drift", Json::num(s.max_drift)).set("max_sag", Json::num(s.max_sag)).set("finite", Json::Bool(s.finite))))
        }
        other => Err(format!("unknown op '{}'", other)),
    }
}

fn apply_edit(p: &mut Pattern, a: &Json) -> Result<(), String> {
    let ty = req_str(a, "type")?;
    let piece = req_str(a, "piece").unwrap_or("");
    let idx = |k: &str| -> Result<usize, String> {
        let v = a.get(k).and_then(|v| v.as_f64()).ok_or_else(|| format!("missing '{}'", k))?;
        if v < 0.0 || v.fract() != 0.0 || v > 1e6 { return Err(format!("invalid '{}'", k)); }
        Ok(v as usize)
    };
    let f = |k: &str| -> Result<f64, String> { a.get(k).and_then(|v| v.as_f64()).ok_or_else(|| format!("missing '{}'", k)) };
    match ty {
        "move_node" => edit::move_node(p, piece, idx("index")?, f("x")?, f("y")?),
        "move_handle" => edit::move_handle(p, piece, idx("index")?, a.get("out").and_then(|v| v.as_bool()).unwrap_or(true), f("x")?, f("y")?),
        "set_corner" => edit::set_corner(p, piece, idx("index")?),
        "set_smooth" => edit::set_smooth(p, piece, idx("index")?),
        "split_edge" => edit::split_edge(p, piece, idx("edge")?, f("t")?),
        "delete_node" => edit::delete_node(p, piece, idx("index")?),
        "set_sa" => edit::set_seam_allowance(p, piece, a.get("edge").and_then(|v| v.as_f64()).map(|v| v as usize), f("sa")?),
        "set_dart" => edit::set_dart_width(p, piece, idx("dart")?, f("width")?),
        "add_notch" => edit::add_notch(p, piece, idx("edge")?, f("t")?, a.get("kind").and_then(|v| v.as_str()).unwrap_or("slit")),
        "remove_notch" => edit::remove_notch(p, piece, idx("index")?),
        "translate" => edit::translate_piece(p, piece, f("dx")?, f("dy")?),
        t => Err(format!("unknown edit type '{}'", t)),
    }
}

/// Accepts JSON, or lines like `bust,92`, `bust: 92`, `bust 92`, `Bust (cm), 92`; header lines are skipped.
/// Only the keys present are applied on top of `base`.
pub fn parse_measurements_text(text: &str, inches: bool, base: &Measurements) -> Result<(Measurements, Vec<String>), String> {
    let t = text.trim();
    if t.is_empty() { return Err("no measurement data".into()); }
    let mut warn = Vec::new();
    let mut o: Vec<(String, Json)> = Vec::new();
    if t.starts_with('{') {
        if let Json::Obj(items) = Json::parse(t)? {
            for (k, v) in items {
                match v.as_f64() {
                    Some(n) => o.push((k, Json::Num(if inches { n * 2.54 } else { n }))),
                    None => warn.push(format!("invalid value for '{}' ignored", k)),
                }
            }
        } else {
            return Err("measurements must be an object".into());
        }
    } else {
        for (ln, line) in t.lines().enumerate() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') { continue; }
            let norm: String = line.replace(['\t', ';', ':', '='], ",");
            let parts: Vec<&str> = if norm.contains(',') { norm.split(',').map(|s| s.trim()).filter(|s| !s.is_empty()).collect() } else {
                let mut it = norm.rsplitn(2, ' ');
                let v = it.next().unwrap_or("");
                let k = it.next().unwrap_or("");
                vec![k.trim(), v.trim()]
            };
            if parts.len() < 2 { warn.push(format!("line {}: could not read '{}'", ln + 1, line)); continue; }
            let key: String = parts[0].split('(').next().unwrap_or("").trim().to_string();
            match parts[1].parse::<f64>() {
                Ok(v) => o.push((key, Json::Num(if inches { v * 2.54 } else { v }))),
                Err(_) => { if ln > 0 { warn.push(format!("line {}: '{}' is not a number", ln + 1, parts[1])); } }
            }
        }
    }
    if o.is_empty() { return Err("no numeric measurements found".into()); }
    let mut m = base.clone();
    let before = m.clone();
    warn.extend(m.apply_json(&Json::Obj(o))?);
    let changed = MEASURE_KEYS.iter().filter(|k| (m.get(k).unwrap() - before.get(k).unwrap()).abs() > 1e-9).count();
    if changed == 0 { warn.push("no recognised measurement names found (expected e.g. bust, waist, hip, back_length)".into()); }
    Ok((m, warn))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ok(r: &str) -> Json {
        let j = Json::parse(r).unwrap();
        assert_eq!(j.get("ok").and_then(|v| v.as_bool()), Some(true), "{}", &r[..r.len().min(300)]);
        j
    }

    #[test]
    fn csv_measurements_with_units_and_junk() {
        let (m, w) = parse_measurements_text("Measurement,Value\nBust (cm), 100\nwaist: 80\nhip 104\nbogus,5\nneck,abc", false, &Measurements::default()).unwrap();
        assert_eq!((m.bust, m.waist, m.hip), (100.0, 80.0, 104.0));
        assert!(w.iter().any(|x| x.contains("bogus")));
        let (mi, _) = parse_measurements_text("bust,40", true, &Measurements::default()).unwrap();
        assert!((mi.bust - 101.6).abs() < 1e-9);
        assert!(parse_measurements_text("hello world", false, &Measurements::default()).is_err());
        // only keys present are applied over the base
        let mut base = Measurements::default();
        base.hip = 111.0;
        let (m2, _) = parse_measurements_text("{\"bust\": 90}", false, &base).unwrap();
        assert_eq!((m2.bust, m2.hip), (90.0, 111.0));
    }

    #[test]
    fn full_pipeline_through_json() {
        let d = ok(&call(r#"{"op":"draft","garment":"bodice"}"#));
        let pattern = d.get("pattern").unwrap().clone();
        let req = Json::obj().set("op", Json::str("export_dxf")).set("pattern", pattern.clone()).set("style", Json::str("T1"));
        let dxf = ok(&call(&req.to_string()));
        assert!(dxf.get("dxf").unwrap().as_str().unwrap().contains("Piece Name: Sleeve"));
        let g = ok(&call(&Json::obj().set("op", Json::str("geometry")).set("pattern", pattern.clone()).to_string()));
        assert_eq!(g.get("pieces").unwrap().as_arr().unwrap().len(), 3);
        let dr = ok(&call(&Json::obj().set("op", Json::str("drape")).set("pattern", pattern).to_string()));
        assert_eq!(dr.get("stats").unwrap().get("finite").unwrap().as_bool(), Some(true));
    }

    #[test]
    fn errors_are_reported_not_panicked() {
        for r in ["", "{", r#"{"op":"nope"}"#, r#"{"op":"draft"}"#, r#"{"op":"draft","garment":"cape"}"#,
                  r#"{"op":"edit","pattern":{"pieces":[]},"action":{"type":"move_node"}}"#,
                  r#"{"op":"export_pds","pattern":{"pieces":[{"name":"a","nodes":[{"p":[0,0]},{"p":[1,0]},{"p":[0,1]}]}]}}"#,
                  r#"{"op":"draft","garment":"bodice","measurements":{"bust":"x"}}"#,
                  r#"{"op":"geometry","pattern":{"pieces":[{"nodes":[{"p":[1e99,0]},{"p":[1,0]},{"p":[0,1]}]}]}}"#] {
            let j = Json::parse(&call(r)).unwrap();
            if r.contains("bust\":\"x") { continue; } // invalid values are warnings, not errors
            assert_eq!(j.get("ok").and_then(|v| v.as_bool()), Some(false), "{}", r);
        }
    }

    #[test]
    fn grade_op_returns_sizes_and_tables() {
        let g = ok(&call(r#"{"op":"grade","garment":"skirt","steps":[-1,0,1]}"#));
        let sizes = g.get("sizes").unwrap().as_arr().unwrap();
        assert_eq!(sizes.len(), 3);
        assert_eq!(sizes[1].get("label").unwrap().as_str(), Some("M"));
        let d0 = sizes[1].get("table").unwrap().as_arr().unwrap();
        assert!(!d0.is_empty());
        assert!(!call(r#"{"op":"grade","garment":"skirt","steps":[]}"#).contains("\"ok\":true"));
    }

    #[test]
    fn edit_roundtrip_changes_geometry() {
        let d = ok(&call(r#"{"op":"draft","garment":"skirt"}"#));
        let p = d.get("pattern").unwrap().clone();
        let req = Json::obj().set("op", Json::str("edit")).set("pattern", p)
            .set("action", Json::obj().set("type", Json::str("move_node")).set("piece", Json::str("Front Skirt")).set("index", Json::num(3.0)).set("x", Json::num(40.0)).set("y", Json::num(-60.0)));
        let e = ok(&call(&req.to_string()));
        let np = Pattern::from_json(e.get("pattern").unwrap()).unwrap();
        assert_eq!(np.piece("Front Skirt").unwrap().nodes[3].p, v2(40.0, -60.0));
    }
}
