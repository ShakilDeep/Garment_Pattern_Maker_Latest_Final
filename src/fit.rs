//! Closed-loop exact-fit solver.
//!
//! Given a finished-garment spec, repeatedly draft the pattern, measure every POM from the
//! geometry (see [`crate::pom`]) and adjust the drafter's *input* fields by the measured error
//! until every non-input POM lands on the spec within 0.01 cm (hard gate 0.02 cm), or report
//! non-convergence honestly with residuals.
//!
//! The solver is a damped multivariate Newton iteration: it forms a finite-difference Jacobian
//! of (measured POMs) w.r.t. (driven input fields), refines it with Broyden rank-1 updates, and
//! solves `J dx = -r` each step with a line search. The couplings the spec calls out
//! (rise vs inseam, seat vs thigh, thigh vs knee, bag vs pocket length) are handled by the full
//! Jacobian rather than by hand. Everything is deterministic.
//!
//! Inputs that the flat sew geometry does not contain (the elastic relaxed/stretched waist, the
//! hip *positions*, the drawcord) are `input_only`: they are passed straight through to the
//! report and never driven.

use crate::garments::{
    self, draft_pant_detailed, draft_shirt, GarmentOpts, PantSpec, ShirtSpec,
};
use crate::json::Json;
use crate::model::Pattern;
use crate::pom::{self, Axis};
use crate::spec::SpecSheet;
use std::collections::BTreeMap;

/// Hard convergence gate: every driven POM must be within this many cm.
pub const HARD_TOL: f64 = 0.02;
/// Solver aims a little tighter than the hard gate.
const SOLVE_TOL: f64 = 0.01;
/// Floor added to the spec tolerance when deciding a row's `ok` flag (measurement/solver noise).
const OK_EPS: f64 = 1e-3;
const MAX_ITERS: usize = 60;

// ---------------------------------------------------------------------------------------
// fabric factors
// ---------------------------------------------------------------------------------------

/// Shrink / stretch factors per axis, as (finished / cut) ratios.
///
/// Convention: after wash/relax a *cut* dimension `D` becomes `D * shrink * stretch` finished.
/// So `shrink_x = 0.97` means the fabric shrinks 3 % across; `stretch_y = 1.02` means it grows
/// 2 % lengthwise. To make the finished garment land on spec we *pre-compensate* the target by
/// dividing it by the factor (cut a bit bigger when it will shrink). Defaults are 1.0 (no-op).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct FabricFactors {
    pub shrink_x: f64,
    pub shrink_y: f64,
    pub stretch_x: f64,
    pub stretch_y: f64,
}

impl Default for FabricFactors {
    fn default() -> Self {
        FabricFactors { shrink_x: 1.0, shrink_y: 1.0, stretch_x: 1.0, stretch_y: 1.0 }
    }
}

impl FabricFactors {
    pub fn is_identity(&self) -> bool {
        (self.shrink_x - 1.0).abs() < 1e-12
            && (self.shrink_y - 1.0).abs() < 1e-12
            && (self.stretch_x - 1.0).abs() < 1e-12
            && (self.stretch_y - 1.0).abs() < 1e-12
    }
    pub fn from_json(j: &Json) -> FabricFactors {
        let g = |k: &str| j.get(k).and_then(|v| v.as_f64()).filter(|v| v.is_finite() && *v > 0.0);
        let d = FabricFactors::default();
        FabricFactors {
            shrink_x: g("shrink_x").unwrap_or(d.shrink_x),
            shrink_y: g("shrink_y").unwrap_or(d.shrink_y),
            stretch_x: g("stretch_x").unwrap_or(d.stretch_x),
            stretch_y: g("stretch_y").unwrap_or(d.stretch_y),
        }
    }
}

/// Pre-compensate a spec target so the finished dimension lands on it after shrink/stretch.
/// Width POMs use the X factors, length/curved POMs the Y factors.
pub fn apply_factors(spec_value: f64, axis: Axis, f: &FabricFactors) -> f64 {
    let k = match axis {
        Axis::X => f.shrink_x * f.stretch_x,
        Axis::Y => f.shrink_y * f.stretch_y,
    };
    if k.abs() < 1e-9 {
        spec_value
    } else {
        spec_value / k
    }
}

// ---------------------------------------------------------------------------------------
// results
// ---------------------------------------------------------------------------------------

/// One row of the fit report.
#[derive(Clone, Debug)]
pub struct FitRow {
    pub code: String,
    pub key: String,
    pub name: String,
    pub target: f64,
    pub measured: f64,
    pub error: f64,
    pub tol_plus: f64,
    pub tol_minus: f64,
    pub ok: bool,
    pub input_only: bool,
}

impl FitRow {
    pub fn to_json(&self) -> Json {
        Json::obj()
            .set("code", Json::str(&self.code))
            .set("key", Json::str(&self.key))
            .set("name", Json::str(&self.name))
            .set("target", Json::num(self.target))
            .set("measured", Json::num(self.measured))
            .set("error", Json::num(self.error))
            .set("tol_plus", Json::num(self.tol_plus))
            .set("tol_minus", Json::num(self.tol_minus))
            .set("ok", Json::Bool(self.ok))
            .set("input_only", Json::Bool(self.input_only))
    }
}

/// The outcome of a fit.
#[derive(Clone, Debug)]
pub struct FitResult {
    pub pattern: Pattern,
    pub rows: Vec<FitRow>,
    pub iterations: usize,
    /// Max |error| over the driven (non-input) POMs.
    pub max_abs_error: f64,
    pub converged: bool,
    pub warnings: Vec<String>,
}

impl FitResult {
    pub fn to_json(&self) -> Json {
        Json::obj()
            .set("pattern", self.pattern.to_json())
            .set("fit", Json::Arr(self.rows.iter().map(|r| r.to_json()).collect()))
            .set("iterations", Json::num(self.iterations as f64))
            .set("max_abs_error", Json::num(self.max_abs_error))
            .set("converged", Json::Bool(self.converged))
            .set("warnings", Json::Arr(self.warnings.iter().map(|w| Json::str(w)).collect()))
    }
}

// ---------------------------------------------------------------------------------------
// a driven variable: an input field mapped to a POM
// ---------------------------------------------------------------------------------------

struct Driven {
    code: &'static str,
    key: &'static str, // spec field, or "opts.pant_hem"
    name: &'static str,
    axis: Axis,
    lo: f64,
    hi: f64,
}

// ---------------------------------------------------------------------------------------
// dense linear solver (Gaussian elimination with partial pivoting), zero deps
// ---------------------------------------------------------------------------------------

/// Solve `A x = b` in place. Returns None if singular.
fn solve_linear(a: &mut [Vec<f64>], b: &mut [f64]) -> Option<Vec<f64>> {
    let n = b.len();
    for col in 0..n {
        // pivot
        let mut piv = col;
        let mut best = a[col][col].abs();
        for r in (col + 1)..n {
            if a[r][col].abs() > best {
                best = a[r][col].abs();
                piv = r;
            }
        }
        if best < 1e-12 {
            return None;
        }
        a.swap(col, piv);
        b.swap(col, piv);
        let d = a[col][col];
        for r in (col + 1)..n {
            let f = a[r][col] / d;
            if f != 0.0 {
                for c in col..n {
                    a[r][c] -= f * a[col][c];
                }
                b[r] -= f * b[col];
            }
        }
    }
    let mut x = vec![0.0; n];
    for i in (0..n).rev() {
        let mut s = b[i];
        for c in (i + 1)..n {
            s -= a[i][c] * x[c];
        }
        x[i] = s / a[i][i];
    }
    Some(x)
}

// ---------------------------------------------------------------------------------------
// the Newton core
// ---------------------------------------------------------------------------------------

/// `eval(x)` applies the input vector, drafts, measures, and returns the driven POM vector.
/// Returns (x, residual, iterations, converged, warnings).
fn newton<F>(
    mut x: Vec<f64>,
    targets: &[f64],
    bounds: &[(f64, f64)],
    eval: &F,
) -> Result<(Vec<f64>, Vec<f64>, usize, bool), String>
where
    F: Fn(&[f64]) -> Result<Vec<f64>, String>,
{
    let n = x.len();
    let clamp = |x: &mut [f64]| {
        for i in 0..n {
            if x[i] < bounds[i].0 {
                x[i] = bounds[i].0;
            }
            if x[i] > bounds[i].1 {
                x[i] = bounds[i].1;
            }
        }
    };
    clamp(&mut x);
    let resid = |m: &[f64]| -> Vec<f64> { (0..n).map(|i| m[i] - targets[i]).collect() };
    let maxabs = |r: &[f64]| r.iter().fold(0.0f64, |a, &v| a.max(v.abs()));

    let mut m = eval(&x)?;
    let mut r = resid(&m);
    if maxabs(&r) <= SOLVE_TOL {
        return Ok((x, r, 0, true));
    }

    // finite-difference Jacobian J[i][j] = d measured_i / d x_j
    let h = 0.25;
    let mut j = vec![vec![0.0; n]; n];
    let build_jac = |x: &[f64], m0: &[f64], j: &mut Vec<Vec<f64>>| -> Result<(), String> {
        for col in 0..n {
            let mut xp = x.to_vec();
            let step = if xp[col] + h <= bounds[col].1 { h } else { -h };
            xp[col] += step;
            let mp = eval(&xp)?;
            for row in 0..n {
                j[row][col] = (mp[row] - m0[row]) / step;
            }
        }
        Ok(())
    };
    build_jac(&x, &m, &mut j)?;

    let mut iters = 0usize;
    while iters < MAX_ITERS {
        iters += 1;
        // solve J dx = -r
        let mut a: Vec<Vec<f64>> = j.clone();
        let mut rhs: Vec<f64> = r.iter().map(|v| -v).collect();
        let dx = match solve_linear(&mut a, &mut rhs) {
            Some(d) => d,
            None => {
                // singular: refresh Jacobian and retry once
                build_jac(&x, &m, &mut j)?;
                let mut a2: Vec<Vec<f64>> = j.clone();
                let mut rhs2: Vec<f64> = r.iter().map(|v| -v).collect();
                match solve_linear(&mut a2, &mut rhs2) {
                    Some(d) => d,
                    None => return Ok((x, r, iters, false)),
                }
            }
        };

        // damped line search
        let cur = maxabs(&r);
        let mut accepted = false;
        let mut scale = 1.0;
        let mut x_new = x.clone();
        let mut m_new = m.clone();
        let mut r_new = r.clone();
        for _ in 0..10 {
            let mut xt = x.clone();
            for i in 0..n {
                xt[i] += scale * dx[i];
            }
            clamp(&mut xt);
            match eval(&xt) {
                Ok(mt) => {
                    let rt = resid(&mt);
                    if maxabs(&rt) < cur - 1e-12 {
                        x_new = xt;
                        m_new = mt;
                        r_new = rt;
                        accepted = true;
                        break;
                    }
                }
                Err(_) => {}
            }
            scale *= 0.5;
        }

        if !accepted {
            // refresh Jacobian from scratch and try a plain damped step once more
            build_jac(&x, &m, &mut j)?;
            let mut a2: Vec<Vec<f64>> = j.clone();
            let mut rhs2: Vec<f64> = r.iter().map(|v| -v).collect();
            if let Some(dx2) = solve_linear(&mut a2, &mut rhs2) {
                let mut s = 1.0;
                for _ in 0..10 {
                    let mut xt = x.clone();
                    for i in 0..n {
                        xt[i] += s * dx2[i];
                    }
                    clamp(&mut xt);
                    if let Ok(mt) = eval(&xt) {
                        let rt = resid(&mt);
                        if maxabs(&rt) < cur - 1e-12 {
                            x_new = xt;
                            m_new = mt;
                            r_new = rt;
                            accepted = true;
                            break;
                        }
                    }
                    s *= 0.5;
                }
            }
            if !accepted {
                return Ok((x, r, iters, false));
            }
        }

        // Broyden rank-1 update: J += ((df - J ds) ds^T) / (ds^T ds)
        let ds: Vec<f64> = (0..n).map(|i| x_new[i] - x[i]).collect();
        let df: Vec<f64> = (0..n).map(|i| m_new[i] - m[i]).collect();
        let dsds: f64 = ds.iter().map(|v| v * v).sum();
        if dsds > 1e-18 {
            let jds: Vec<f64> = (0..n).map(|i| (0..n).map(|k| j[i][k] * ds[k]).sum()).collect();
            for i in 0..n {
                let corr = (df[i] - jds[i]) / dsds;
                for k in 0..n {
                    j[i][k] += corr * ds[k];
                }
            }
        }

        x = x_new;
        m = m_new;
        r = r_new;
        if maxabs(&r) <= SOLVE_TOL {
            return Ok((x, r, iters, true));
        }
    }
    let ok = maxabs(&r) <= HARD_TOL;
    Ok((x, r, iters, ok))
}

// ---------------------------------------------------------------------------------------
// pant fit
// ---------------------------------------------------------------------------------------

fn pant_driven() -> Vec<Driven> {
    vec![
        Driven { code: "20305", key: "half_seat", name: "1/2 seat", axis: Axis::X, lo: 35.0, hi: 90.0 },
        Driven { code: "20865", key: "thigh", name: "thigh", axis: Axis::X, lo: 20.0, hi: 60.0 },
        Driven { code: "21505", key: "front_rise", name: "front rise", axis: Axis::Y, lo: 15.0, hi: 50.0 },
        Driven { code: "21545", key: "back_rise", name: "back rise", axis: Axis::Y, lo: 20.0, hi: 60.0 },
        Driven { code: "20905", key: "knee", name: "knee", axis: Axis::X, lo: 15.0, hi: 60.0 },
        Driven { code: "21125", key: "leg_opening", name: "1/2 leg opening", axis: Axis::X, lo: 12.0, hi: 60.0 },
        Driven { code: "30210", key: "opts.pant_hem", name: "hem height", axis: Axis::Y, lo: 0.05, hi: 8.0 },
        Driven { code: "21885", key: "inseam", name: "inseam", axis: Axis::Y, lo: 40.0, hi: 100.0 },
        Driven { code: "20265", key: "waistband_width", name: "waistband width", axis: Axis::Y, lo: 2.0, hi: 12.0 },
        Driven { code: "22145", key: "pocket_opening_waist", name: "pkt opening @ WB", axis: Axis::X, lo: 1.0, hi: 10.0 },
        Driven { code: "22165", key: "pocket_opening_length", name: "pkt opening down outseam", axis: Axis::Y, lo: 8.0, hi: 30.0 },
        Driven { code: "22565", key: "pocket_bag_depth", name: "pkt bag depth", axis: Axis::X, lo: 12.0, hi: 40.0 },
    ]
}

/// Fit a pant spec exactly. `factors` pre-compensates the targets for fabric shrink/stretch.
pub fn fit_pant(
    spec: &PantSpec,
    opts: &GarmentOpts,
    factors: Option<&FabricFactors>,
) -> Result<FitResult, String> {
    let ff = factors.copied().unwrap_or_default();
    // target POM values come from the spec itself (the spec IS the finished-garment target).
    let base = spec.to_map();
    let driven = pant_driven();

    // feasibility: the target spec must be draftable.
    spec.validate().map_err(|e| format!("infeasible pant spec: {}", e))?;

    // targets per driven POM, pre-compensated for fabric factors.
    let mut targets = Vec::with_capacity(driven.len());
    for d in &driven {
        let raw = if d.key == "opts.pant_hem" {
            // hem height target = the spec hem_height (fold), not opts default.
            *base.get("hem_height").unwrap_or(&opts.pant_hem)
        } else {
            *base.get(d.key).ok_or_else(|| format!("missing pant field {}", d.key))?
        };
        targets.push(apply_factors(raw, d.axis, &ff));
    }

    // initial guess: the spec's own field values (good starting point).
    let x0: Vec<f64> = driven
        .iter()
        .map(|d| {
            if d.key == "opts.pant_hem" {
                *base.get("hem_height").unwrap_or(&opts.pant_hem)
            } else {
                *base.get(d.key).unwrap()
            }
        })
        .collect();
    let bounds: Vec<(f64, f64)> = driven.iter().map(|d| (d.lo, d.hi)).collect();

    let base_spec = spec.clone();
    let base_opts = opts.clone();
    let eval = |x: &[f64]| -> Result<Vec<f64>, String> {
        let (mut s, mut o) = (base_spec.clone(), base_opts.clone());
        for (i, d) in driven.iter().enumerate() {
            if d.key == "opts.pant_hem" {
                o.pant_hem = x[i];
            } else {
                s.set(d.key, x[i]);
            }
        }
        let pat = draft_pant_detailed(&s, &o)?;
        let m = pom::measure_pant(&pat);
        let get = |code: &str| m.iter().find(|p| p.code == code).map(|p| p.value).unwrap_or(f64::NAN);
        Ok(driven.iter().map(|d| get(d.code)).collect())
    };

    let (x, resid, iters, converged) = newton(x0, &targets, &bounds, &eval)?;
    if std::env::var("FIT_DEBUG").is_ok() {
        for (i, d) in driven.iter().enumerate() {
            eprintln!("DBG {} {} x={:.4} target={:.4} resid={:+.5}", d.code, d.key, x[i], targets[i], resid[i]);
        }
    }

    // re-draft at the solution for the returned pattern + full measurement.
    let (mut s, mut o) = (spec.clone(), opts.clone());
    for (i, d) in driven.iter().enumerate() {
        if d.key == "opts.pant_hem" {
            o.pant_hem = x[i];
        } else {
            s.set(d.key, x[i]);
        }
    }
    let pat = draft_pant_detailed(&s, &o)?;
    let rows = build_rows(&pom::measure_pant(&pat), &driven, &targets, &resid, None, &base);
    finish(pat, rows, iters, converged, &resid, &driven)
}

// ---------------------------------------------------------------------------------------
// shirt fit
// ---------------------------------------------------------------------------------------

fn shirt_driven() -> Vec<Driven> {
    vec![
        Driven { code: "half_chest", key: "half_chest", name: "1/2 chest", axis: Axis::X, lo: 35.0, hi: 90.0 },
        Driven { code: "half_hem", key: "half_hem", name: "1/2 hem", axis: Axis::X, lo: 35.0, hi: 90.0 },
        Driven { code: "across_shoulder", key: "across_shoulder", name: "across shoulder", axis: Axis::X, lo: 30.0, hi: 70.0 },
        Driven { code: "body_length_hps", key: "body_length_hps", name: "body length HPS", axis: Axis::Y, lo: 45.0, hi: 110.0 },
        Driven { code: "back_length_cb", key: "back_length_cb", name: "back length CB", axis: Axis::Y, lo: 45.0, hi: 115.0 },
        Driven { code: "yoke_depth", key: "yoke_depth", name: "yoke depth", axis: Axis::Y, lo: 6.0, hi: 25.0 },
        Driven { code: "sleeve_length", key: "sleeve_length", name: "sleeve length", axis: Axis::Y, lo: 15.0, hi: 70.0 },
        Driven { code: "bicep", key: "bicep", name: "bicep", axis: Axis::X, lo: 12.0, hi: 40.0 },
        Driven { code: "sleeve_opening", key: "sleeve_opening", name: "sleeve opening", axis: Axis::X, lo: 8.0, hi: 35.0 },
        Driven { code: "neck_size", key: "neck_size", name: "neck size", axis: Axis::X, lo: 30.0, hi: 70.0 },
        Driven { code: "stand_height", key: "stand_height", name: "stand height", axis: Axis::Y, lo: 1.5, hi: 7.0 },
        Driven { code: "collar_point_length", key: "collar_point_length", name: "collar point", axis: Axis::Y, lo: 3.0, hi: 10.0 },
    ]
}

/// Fit a shirt spec exactly.
pub fn fit_shirt(
    spec: &ShirtSpec,
    opts: &GarmentOpts,
    factors: Option<&FabricFactors>,
) -> Result<FitResult, String> {
    let ff = factors.copied().unwrap_or_default();
    let base = spec.to_map();
    let driven = shirt_driven();
    spec.validate().map_err(|e| format!("infeasible shirt spec: {}", e))?;

    let mut targets = Vec::with_capacity(driven.len());
    for d in &driven {
        let raw = *base.get(d.key).ok_or_else(|| format!("missing shirt field {}", d.key))?;
        targets.push(apply_factors(raw, d.axis, &ff));
    }
    let x0: Vec<f64> = driven.iter().map(|d| *base.get(d.key).unwrap()).collect();
    let bounds: Vec<(f64, f64)> = driven.iter().map(|d| (d.lo, d.hi)).collect();

    let base_spec = spec.clone();
    let base_opts = opts.clone();
    let eval = |x: &[f64]| -> Result<Vec<f64>, String> {
        let mut s = base_spec.clone();
        for (i, d) in driven.iter().enumerate() {
            s.set(d.key, x[i]);
        }
        let pat = draft_shirt(&s, &base_opts)?;
        let m = pom::measure_shirt(&pat);
        let get = |code: &str| m.iter().find(|p| p.code == code).map(|p| p.value).unwrap_or(f64::NAN);
        Ok(driven.iter().map(|d| get(d.code)).collect())
    };

    let (x, resid, iters, converged) = newton(x0, &targets, &bounds, &eval)?;
    if std::env::var("FIT_DEBUG").is_ok() {
        for (i, d) in driven.iter().enumerate() {
            eprintln!("DBG {} {} x={:.4} target={:.4} resid={:+.5}", d.code, d.key, x[i], targets[i], resid[i]);
        }
    }

    let mut s = spec.clone();
    for (i, d) in driven.iter().enumerate() {
        s.set(d.key, x[i]);
    }
    let pat = draft_shirt(&s, opts)?;
    let rows = build_rows(&pom::measure_shirt(&pat), &driven, &targets, &resid, None, &base);
    finish(pat, rows, iters, converged, &resid, &driven)
}

// ---------------------------------------------------------------------------------------
// row building / result assembly
// ---------------------------------------------------------------------------------------

/// Build the FitRows. `tol` maps POM code -> (tol_plus, tol_minus); None = zero tolerance.
fn build_rows(
    measures: &[pom::PomMeasure],
    driven: &[Driven],
    targets: &[f64],
    _resid: &[f64],
    tol: Option<&BTreeMap<String, (f64, f64)>>,
    inputs: &BTreeMap<String, f64>,
) -> Vec<FitRow> {
    let driven_codes: BTreeMap<&str, usize> =
        driven.iter().enumerate().map(|(i, d)| (d.code, i)).collect();
    let tol_of = |code: &str| -> (f64, f64) {
        tol.and_then(|t| t.get(code)).copied().unwrap_or((0.0, 0.0))
    };
    let mut rows = Vec::new();
    for m in measures {
        if m.input_only {
            // pass-through: the spec value is reported as both target and measured (no driving).
            let (tp, tm) = tol_of(&m.code);
            let v = inputs
                .get(m.key.as_str())
                .copied()
                .or_else(|| if m.value.is_finite() { Some(m.value) } else { None })
                .unwrap_or(f64::NAN);
            rows.push(FitRow {
                code: m.code.clone(),
                key: m.key.clone(),
                name: m.name.clone(),
                target: v,
                measured: v,
                error: 0.0,
                tol_plus: tp,
                tol_minus: tm,
                ok: true,
                input_only: true,
            });
            continue;
        }
        if let Some(&i) = driven_codes.get(m.code.as_str()) {
            let (tp, tm) = tol_of(&m.code);
            let err = m.value - targets[i];
            let ok = err >= -(tm + OK_EPS) && err <= tp + OK_EPS;
            rows.push(FitRow {
                code: m.code.clone(),
                key: m.key.clone(),
                name: m.name.clone(),
                target: targets[i],
                measured: m.value,
                error: err,
                tol_plus: tp,
                tol_minus: tm,
                ok,
                input_only: false,
            });
        }
    }
    rows
}

fn finish(
    pattern: Pattern,
    rows: Vec<FitRow>,
    iterations: usize,
    converged: bool,
    resid: &[f64],
    driven: &[Driven],
) -> Result<FitResult, String> {
    let max_abs_error = resid.iter().fold(0.0f64, |a, &v| a.max(v.abs()));
    let mut warnings = Vec::new();
    if !converged {
        warnings.push(format!(
            "did not reach {} cm on every POM (max residual {:.4} cm)",
            HARD_TOL, max_abs_error
        ));
        for (i, d) in driven.iter().enumerate() {
            if resid[i].abs() > HARD_TOL {
                warnings.push(format!("  {} ({}): residual {:+.4} cm", d.code, d.name, resid[i]));
            }
        }
    }
    Ok(FitResult { pattern, rows, iterations, max_abs_error, converged, warnings })
}

// ---------------------------------------------------------------------------------------
// sheet-level fit (every size column) -- item G35
// ---------------------------------------------------------------------------------------

/// Column spec map for a size, built like `pds_api::draft_spec` (code, English, local, size keys).
fn column(sheet: &SpecSheet, size: &str) -> BTreeMap<String, f64> {
    let mut m = sheet.name_map(size);
    for (k, v) in sheet.canonical_map(size) {
        m.insert(k, v);
    }
    for (k, v) in sheet.size_map(size) {
        m.insert(k, v);
    }
    m
}

/// Tolerance map (POM code -> (+,-)) from the sheet's ± column.
fn tol_map(sheet: &SpecSheet) -> BTreeMap<String, (f64, f64)> {
    sheet
        .rows
        .iter()
        .map(|r| (r.code.clone(), (r.tol_plus.max(0.0), r.tol_minus.max(0.0))))
        .collect()
}

/// Fit EVERY size column of a sheet (exact spec values per size, not increments).
pub fn fit_pant_sheet(
    sheet: &SpecSheet,
    opts: &GarmentOpts,
    factors: Option<&FabricFactors>,
) -> Result<Vec<(String, FitResult)>, String> {
    fit_sheet(sheet, "pant", opts, factors)
}

pub fn fit_shirt_sheet(
    sheet: &SpecSheet,
    opts: &GarmentOpts,
    factors: Option<&FabricFactors>,
) -> Result<Vec<(String, FitResult)>, String> {
    fit_sheet(sheet, "shirt", opts, factors)
}

/// Fit every size of a sheet for the given kind ("pant"/"shirt").
pub fn fit_sheet(
    sheet: &SpecSheet,
    kind: &str,
    opts: &GarmentOpts,
    factors: Option<&FabricFactors>,
) -> Result<Vec<(String, FitResult)>, String> {
    if sheet.sizes.is_empty() {
        return Err("spec sheet has no sizes".into());
    }
    let is_shirt = matches!(garments::norm_key(kind).as_str(), "shirt");
    let tols = tol_map(sheet);
    let mut out = Vec::new();
    for size in &sheet.sizes {
        let col = column(sheet, size);
        let mut res = if is_shirt {
            let (spec, _w) = ShirtSpec::from_map_checked(&col);
            let mut r = fit_shirt(&spec, opts, factors)
                .map_err(|e| format!("size {}: {}", size, e))?;
            r.pattern.size = size.clone();
            // re-tag rows with the sheet tolerances
            r.rows = retol(r.rows, &tols);
            r
        } else {
            let (spec, _w) = PantSpec::from_pom_checked(&col);
            let mut r = fit_pant(&spec, opts, factors)
                .map_err(|e| format!("size {}: {}", size, e))?;
            r.pattern.size = size.clone();
            r.rows = retol(r.rows, &tols);
            r
        };
        res.pattern.style = sheet.style.clone();
        out.push((size.clone(), res));
    }
    Ok(out)
}

/// Re-apply the sheet tolerances onto already-built rows (recomputes `ok`).
fn retol(rows: Vec<FitRow>, tols: &BTreeMap<String, (f64, f64)>) -> Vec<FitRow> {
    rows.into_iter()
        .map(|mut r| {
            if let Some(&(tp, tm)) = tols.get(&r.code) {
                r.tol_plus = tp;
                r.tol_minus = tm;
                if !r.input_only {
                    r.ok = r.error >= -(tm + OK_EPS) && r.error <= tp + OK_EPS;
                }
            }
            r
        })
        .collect()
}

// ---------------------------------------------------------------------------------------
// grading checks -- items G36 / G37
// ---------------------------------------------------------------------------------------

/// Flag non-monotonic grading and gross per-POM jumps across the size range.
///
/// - *non-monotonic*: a POM whose consecutive increments change sign (grows then shrinks).
/// - *big jump*: an increment larger than 20 % of the adjacent value (a gross outlier). This
///   deliberately does NOT flag normal grade-step changes (e.g. a 1.0 cm step becoming 1.3 cm),
///   so it produces no false positives on a well-formed chart.
pub fn grading_report(sheet: &SpecSheet) -> Json {
    let mut poms = Vec::new();
    let mut any = false;
    for r in &sheet.rows {
        let incs: Vec<f64> = r
            .values
            .windows(2)
            .map(|w| {
                if w[0].is_finite() && w[1].is_finite() {
                    w[1] - w[0]
                } else {
                    f64::NAN
                }
            })
            .collect();
        let mut has_pos = false;
        let mut has_neg = false;
        for &d in &incs {
            if d.is_finite() {
                if d > 1e-6 {
                    has_pos = true;
                }
                if d < -1e-6 {
                    has_neg = true;
                }
            }
        }
        let non_monotonic = has_pos && has_neg;
        let mut big_jumps = Vec::new();
        for (i, &d) in incs.iter().enumerate() {
            if !d.is_finite() {
                continue;
            }
            let v_next = r.values[i + 1].abs();
            let v_prev = r.values[i].abs();
            let base = v_next.max(v_prev);
            if base > 1e-9 && d.abs() > 0.20 * base {
                big_jumps.push(i);
            }
        }
        let mut warns = Vec::new();
        if non_monotonic {
            warns.push(format!("POM {} ({}) grading is non-monotonic", r.code, r.name));
        }
        for &i in &big_jumps {
            warns.push(format!(
                "POM {} ({}): jump {} -> {} between sizes {} and {} exceeds 20%",
                r.code,
                r.name,
                sheet.sizes.get(i).cloned().unwrap_or_default(),
                sheet.sizes.get(i + 1).cloned().unwrap_or_default(),
                r.values[i],
                r.values[i + 1]
            ));
        }
        if non_monotonic || !big_jumps.is_empty() {
            any = true;
        }
        poms.push(
            Json::obj()
                .set("code", Json::str(&r.code))
                .set("name", Json::str(&r.name))
                .set("increments", Json::nums(&incs))
                .set("monotonic", Json::Bool(!non_monotonic))
                .set(
                    "big_jumps",
                    Json::Arr(big_jumps.iter().map(|&i| Json::num(i as f64)).collect()),
                )
                .set("warnings", Json::Arr(warns.iter().map(|w| Json::str(w)).collect())),
        );
    }
    Json::obj()
        .set("pom", Json::Arr(poms))
        .set("sizes", Json::Arr(sheet.sizes.iter().map(|s| Json::str(s)).collect()))
        .set("ok", Json::Bool(!any))
}

/// Linear extrapolation of a new size column (POM code -> value), marked extrapolated by the
/// caller. `from` is the size to start from, `steps` the number of sizes up (>0) or down (<0).
pub fn extrapolate_size(
    sheet: &SpecSheet,
    label: &str,
    from: &str,
    steps: i32,
) -> BTreeMap<String, f64> {
    let _ = label;
    sheet.extrapolate(label, from, steps)
}

// ---------------------------------------------------------------------------------------
// JSON api (same shape as pds_api::draft_spec, plus fit/grading) -- item A4 + fit_json
// ---------------------------------------------------------------------------------------

/// op fit_spec: fit a spec sheet. Mirrors `pds_api::draft_spec`'s output and adds the fit report,
/// `max_abs_error`, `converged`, and `grading`.
pub fn fit_json(
    kind: &str,
    sheet_json: &Json,
    size: Option<&str>,
    factors: Option<&Json>,
) -> Result<Json, String> {
    let sheet = SpecSheet::from_json(sheet_json)?;
    if sheet.sizes.is_empty() {
        return Err("spec has no sizes".into());
    }
    let ff = factors.map(FabricFactors::from_json);
    let opts = GarmentOpts::default();
    let want = size
        .map(|s| s.to_string())
        .unwrap_or_else(|| sheet.base_size.clone());
    if !sheet.sizes.iter().any(|z| z.eq_ignore_ascii_case(&want)) {
        return Err(format!("size '{}' is not in the spec ({})", want, sheet.sizes.join(", ")));
    }

    let all = fit_sheet(&sheet, kind, &opts, ff.as_ref())?;
    let bi = sheet
        .sizes
        .iter()
        .position(|z| z.eq_ignore_ascii_case(&want))
        .unwrap_or(0) as i64;

    let sizes: Vec<Json> = all
        .iter()
        .enumerate()
        .map(|(i, (label, res))| {
            let meas = Json::Obj(
                res.rows
                    .iter()
                    .map(|r| (r.code.clone(), Json::num(r.measured)))
                    .collect(),
            );
            Json::obj()
                .set("label", Json::str(label))
                .set("step", Json::num((i as i64 - bi) as f64))
                .set("measurements", meas)
                .set("pattern", res.pattern.to_json())
                .set("table", Json::Arr(
                    crate::grade::grade_table(&all[bi.max(0) as usize].1.pattern, &res.pattern).into_iter()
                        .map(|(n, d)| Json::obj().set("piece", Json::Str(n)).set("deltas",
                            Json::Arr(d.iter().map(|q| Json::nums(&[q.x, q.y])).collect()))).collect()))
                .set("fit", Json::Arr(res.rows.iter().map(|r| r.to_json()).collect()))
                .set("max_abs_error", Json::num(res.max_abs_error))
                .set("converged", Json::Bool(res.converged))
        })
        .collect();

    let cur = all
        .iter()
        .find(|(z, _)| z.eq_ignore_ascii_case(&want))
        .ok_or("size not fitted")?;

    let mut warnings: Vec<Json> = Vec::new();
    warnings.push(Json::str(
        "Pattern fitted parametrically so every non-input POM lands on the spec by our geometric \
         definitions (see docs/POM-DEFINITIONS.md). Elastic waist and hip positions are inputs, \
         passed through. Verify one size in Optitex's Measure tool before cutting.",
    ));
    if let Some(ff) = &ff {
        if !ff.is_identity() {
            warnings.push(Json::str(
                "Targets were pre-compensated for fabric shrink/stretch factors (cut dimensions \
                 differ from the finished spec).",
            ));
        }
    }
    for (_l, r) in &all {
        for w in &r.warnings {
            warnings.push(Json::str(w));
        }
    }

    Ok(Json::obj()
        .set("pattern", cur.1.pattern.to_json())
        .set("size", Json::str(&cur.0))
        .set("base_size", Json::str(&sheet.base_size))
        .set("sizes", Json::Arr(sizes))
        .set("fit", Json::Arr(cur.1.rows.iter().map(|r| r.to_json()).collect()))
        .set("checks", Json::Arr(cur.1.rows.iter().map(|r| Json::obj()
            .set("name", Json::str(&format!("{} {}", r.code, r.name)))
            .set("value", Json::num(r.measured)).set("expected", Json::num(r.target))
            .set("tol", Json::num(r.tol_plus.max(r.tol_minus).max(HARD_TOL)))
            .set("ok", Json::Bool(r.ok))).collect()))
        .set("max_abs_error", Json::num(cur.1.max_abs_error))
        .set("converged", Json::Bool(cur.1.converged))
        .set("grading", grading_report(&sheet))
        .set("warnings", Json::Arr(warnings)))
}

// ---------------------------------------------------------------------------------------
// tests
// ---------------------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use crate::garments::{GarmentOpts, PantSpec, ShirtSpec};

    fn real_sheet() -> SpecSheet {
        let txt = std::fs::read_to_string("/home/claude/samples/spec_graded.tsv")
            .expect("spec_graded.tsv");
        crate::spec::parse_spec_text(&txt).expect("parse")
    }

    #[test]
    fn fabric_factor_roundtrip() {
        let f = FabricFactors { shrink_x: 0.95, shrink_y: 0.98, stretch_x: 1.0, stretch_y: 1.0 };
        // cutting at the pre-compensated target, then shrinking, lands on spec.
        let spec = 50.0;
        let cut = apply_factors(spec, Axis::X, &f);
        assert!((cut * (f.shrink_x * f.stretch_x) - spec).abs() < 1e-9);
        assert!(cut > spec);
    }

    #[test]
    fn linear_solver_identity() {
        let mut a = vec![vec![2.0, 0.0], vec![0.0, 4.0]];
        let mut b = vec![6.0, 8.0];
        let x = solve_linear(&mut a, &mut b).unwrap();
        assert!((x[0] - 3.0).abs() < 1e-12 && (x[1] - 2.0).abs() < 1e-12);
    }

    #[test]
    fn fit_pant_default_converges() {
        let r = fit_pant(&PantSpec::default(), &GarmentOpts::default(), None).unwrap();
        assert!(r.converged, "max {}", r.max_abs_error);
        assert!(r.max_abs_error <= HARD_TOL, "max {}", r.max_abs_error);
    }

    #[test]
    fn fit_shirt_default_converges() {
        let r = fit_shirt(&ShirtSpec::default(), &GarmentOpts::default(), None).unwrap();
        assert!(r.converged, "max {}", r.max_abs_error);
        assert!(r.max_abs_error <= HARD_TOL, "max {}", r.max_abs_error);
    }

    #[test]
    fn fit_is_deterministic() {
        let a = fit_pant(&PantSpec::default(), &GarmentOpts::default(), None).unwrap();
        let b = fit_pant(&PantSpec::default(), &GarmentOpts::default(), None).unwrap();
        assert_eq!(a.iterations, b.iterations);
        for (ra, rb) in a.rows.iter().zip(b.rows.iter()) {
            assert!((ra.measured - rb.measured).abs() < 1e-12);
        }
    }

    #[test]
    fn infeasible_spec_errs() {
        let mut s = PantSpec::default();
        s.set("leg_opening", 5.0); // below the supported range, impossible
        let e = fit_pant(&s, &GarmentOpts::default(), None);
        assert!(e.is_err());
        assert!(e.unwrap_err().contains("leg_opening"));
    }

    #[test]
    fn real_sheet_every_size_within_tol() {
        let sheet = real_sheet();
        let results = fit_pant_sheet(&sheet, &GarmentOpts::default(), None).unwrap();
        assert_eq!(results.len(), 6);
        for (size, res) in &results {
            // baseline (unfitted) errors for comparison
            let col = column(&sheet, size);
            let (spec, _) = PantSpec::from_pom_checked(&col);
            let base_pat =
                draft_pant_detailed(&spec, &GarmentOpts::default()).unwrap();
            let base_m = pom::measure_pant(&base_pat);
            let mut base_max = 0.0f64;
            for r in &res.rows {
                if r.input_only {
                    continue;
                }
                if let Some(bm) = base_m.iter().find(|x| x.code == r.code) {
                    base_max = base_max.max((bm.value - r.target).abs());
                }
            }
            println!(
                "size {}: fitted max |err| = {:.4} cm (baseline {:.3} cm), {} iters, converged={}",
                size, res.max_abs_error, base_max, res.iterations, res.converged
            );
            for r in &res.rows {
                if r.input_only { continue; }
                let b = base_m.iter().find(|x| x.code == r.code).map(|x| x.value - r.target).unwrap_or(f64::NAN);
                println!("    {:<8} target {:>7.3}  baseline err {:>+8.3}  fitted err {:>+8.4}", r.code, r.target, b, r.error);
            }
            assert!(res.converged, "size {} not converged", size);
            for r in &res.rows {
                if r.input_only {
                    continue;
                }
                assert!(
                    r.error.abs() <= HARD_TOL,
                    "size {} POM {} error {:.4} > {}",
                    size,
                    r.code,
                    r.error,
                    HARD_TOL
                );
            }
            // check_pattern still passes on the fitted pattern
            garments::check_pattern(&res.pattern).unwrap();
        }
    }

    #[test]
    fn factors_precompensate_targets() {
        let f = FabricFactors { shrink_x: 0.96, shrink_y: 0.98, stretch_x: 1.0, stretch_y: 1.0 };
        let r = fit_pant(&PantSpec::default(), &GarmentOpts::default(), Some(&f)).unwrap();
        assert!(r.converged);
        let seat = r.rows.iter().find(|x| x.code == "20305").unwrap();
        assert!((seat.measured * 0.96 - 52.0).abs() < 0.03, "{}", seat.measured);
    }

    #[test]
    fn grading_report_no_false_positive_on_real_sheet() {
        let sheet = real_sheet();
        let g = grading_report(&sheet);
        let ok = g.get("ok").and_then(|v| v.as_bool()).unwrap();
        assert!(ok, "grading report: {}", g.to_string());
    }

    #[test]
    fn grading_report_flags_non_monotonic() {
        let mut sheet = real_sheet();
        // corrupt one POM to go down then up
        if let Some(r) = sheet.rows.iter_mut().find(|r| r.code == "20305") {
            r.values = vec![50.0, 48.0, 54.0, 56.5, 59.0, 61.5];
        }
        let g = grading_report(&sheet);
        assert!(!g.get("ok").and_then(|v| v.as_bool()).unwrap());
    }

    #[test]
    fn fit_json_shape() {
        let sheet = real_sheet();
        let j = fit_json("pant", &sheet.to_json(), Some("M"), None).unwrap();
        assert!(j.get("pattern").is_some());
        assert!(j.get("fit").is_some());
        assert!(j.get("grading").is_some());
        assert!(j.get("max_abs_error").is_some());
        assert_eq!(j.get("sizes").unwrap().as_arr().unwrap().len(), 6);
    }
}
