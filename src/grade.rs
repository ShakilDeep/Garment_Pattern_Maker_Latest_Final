//! Parametric grading: re-draft the block per size from measurement increments,
//! and derive per-node (dx, dy) grade rules relative to the base size.
use crate::draft::{draft, DraftOpts};
use crate::geom::*;
use crate::model::*;

/// Default growth per size step (cm) — editable by the caller.
pub fn default_rules() -> Vec<(String, f64)> {
    [
        ("bust", 4.0), ("waist", 4.0), ("hip", 4.0), ("back_length", 0.6), ("shoulder_width", 0.8),
        ("neck", 0.8), ("bicep", 1.6), ("wrist", 0.5), ("sleeve_length", 0.6), ("waist_to_hip", 0.3),
        ("skirt_length", 0.0), ("rise", 0.5), ("inseam", 0.3), ("thigh", 2.4), ("knee", 1.6),
        ("ankle", 0.6), ("height", 2.5),
    ].iter().map(|(k, v)| (k.to_string(), *v)).collect()
}

pub fn size_label(step: i32) -> String {
    const L: [&str; 8] = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL"];
    let i = 3 + step;
    if (0..8).contains(&i) { L[i as usize].to_string() } else if step > 0 { format!("M+{}", step) } else { format!("M{}", step) }
}

pub fn graded_measurements(base: &Measurements, rules: &[(String, f64)], step: i32) -> Measurements {
    let mut m = base.clone();
    for (k, d) in rules {
        if let Some(v) = m.get(k) { m.set(k, v + d * step as f64); }
    }
    m
}

pub struct GradedSize {
    pub step: i32,
    pub label: String,
    pub measurements: Measurements,
    pub pattern: Pattern,
}

pub fn grade(garment: &str, base: &Measurements, opts: &DraftOpts, rules: &[(String, f64)], steps: &[i32]) -> Result<Vec<GradedSize>, String> {
    let mut out = Vec::new();
    for &s in steps {
        let m = graded_measurements(base, rules, s);
        let mut p = draft(garment, &m, opts)?;
        p.size = size_label(s);
        out.push(GradedSize { step: s, label: size_label(s), measurements: m, pattern: p });
    }
    Ok(out)
}

/// Per-node deltas of `sized` relative to `base` for each piece with matching structure.
pub fn grade_table(base: &Pattern, sized: &Pattern) -> Vec<(String, Vec<V2>)> {
    let mut t = Vec::new();
    for bp in &base.pieces {
        if let Some(sp) = sized.piece(&bp.name) {
            if sp.nodes.len() == bp.nodes.len() {
                t.push((bp.name.clone(), bp.nodes.iter().zip(&sp.nodes).map(|(a, b)| b.p - a.p).collect()));
            }
        }
    }
    t
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn grading_grows_monotonically() {
        let base = Measurements::default();
        let g = grade("bodice", &base, &DraftOpts::default(), &default_rules(), &[-1, 0, 1, 2]).unwrap();
        let widths: Vec<f64> = g.iter().map(|s| s.pattern.piece("Back Bodice").unwrap().bounds().1.x).collect();
        assert!(widths.windows(2).all(|w| w[1] > w[0]), "{:?}", widths);
        assert_eq!(g[1].label, "M");
        // base size (step 0) must equal a direct draft
        let direct = draft("bodice", &base, &DraftOpts::default()).unwrap();
        assert_eq!(direct.pieces[0].area(), g[1].pattern.pieces[0].area());
    }
    #[test]
    fn grade_table_is_zero_for_base() {
        let p = draft("skirt", &Measurements::default(), &DraftOpts::default()).unwrap();
        let t = grade_table(&p, &p);
        assert!(t.iter().all(|(_, d)| d.iter().all(|v| v.len() == 0.0)));
    }
}
