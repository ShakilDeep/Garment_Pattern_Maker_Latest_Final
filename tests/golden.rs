//! Regression / golden-file harness (#43, #45).
//!
//! These tests re-measure the real sample files and assert that derived quantities stay within
//! tolerance of stored reference numbers.  The reference numbers live as `const`s both here and
//! in `patternforge::validate` (used by `golden_report`).  Tests that need a sample file are
//! skipped (not failed) when that file is absent, so the suite is portable.
//!
//! ## Adding a new golden file (item #45)
//!
//! When a real spec + PDS pair arrives:
//!   1. Drop the files in the sample directory (default `/home/claude/samples`, override with the
//!      `PDS_SAMPLE_DIR` env var).
//!   2. Decode / read it once with the library, print the measured quantities you want to pin
//!      (bbox width/height/perimeter for geometry; POM rows for a spec), e.g. by adding a
//!      throwaway `eprintln!` in a copy of one of the tests below and running with `--nocapture`.
//!   3. Paste those measured numbers in as new `const`s and add `golden_eq!` assertions with a
//!      tolerance that reflects the decode residual (geometry here is good to ~0.01-0.1 cm).
//!   4. Mirror the consts into `src/validate.rs` so `golden_report` covers the new sample too.
//!
//! The point of embedding the numbers is that a future change to the decoder or reader that
//! moves any measured quantity is caught immediately, with the exact drift reported.

use std::path::PathBuf;

use patternforge::pds_bin;
use patternforge::validate::golden_report;
use patternforge::xlsx_read::{read_xlsx, sheet_to_tsv, Sheet};

fn sample_dir() -> PathBuf {
    PathBuf::from(std::env::var("PDS_SAMPLE_DIR").unwrap_or_else(|_| "/home/claude/samples".into()))
}

fn sample(name: &str) -> Option<Vec<u8>> {
    let mut p = sample_dir();
    p.push(name);
    match std::fs::read(&p) {
        Ok(b) => Some(b),
        Err(_) => {
            eprintln!("SKIP: sample {:?} not available", p);
            None
        }
    }
}

// ---- reference numbers --------------------------------------------------------------------
// Pant base size S, decoded from pant_1074664.PDS (cross-checked against Optitex GEOM_INFO).
const PANT_BELT_S_W: f64 = 105.6;
const PANT_BELT_S_H: f64 = 13.0;
const PANT_BELT_S_PER: f64 = 237.2;
const PANT_FRONT_S_W: f64 = 108.8272;
const PANT_FRONT_S_H: f64 = 31.8795;
// Graded spec sheet POM rows (values produced by the Python extract, verified byte-for-byte).
const SPEC_POM_20125: [f64; 6] = [33.0, 35.0, 37.0, 39.5, 42.0, 44.5];
const SPEC_POM_21885: [f64; 6] = [77.0, 78.0, 79.0, 80.0, 81.0, 82.0];

macro_rules! golden_eq {
    ($name:expr, $measured:expr, $expected:expr, $tol:expr) => {{
        let m: f64 = $measured;
        let e: f64 = $expected;
        let t: f64 = $tol;
        assert!(
            (m - e).abs() <= t,
            "golden '{}' drifted: measured {} vs reference {} (tol {}, Δ {})",
            $name,
            m,
            e,
            t,
            (m - e).abs()
        );
    }};
}

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

fn graded_sheet(sheets: &[Sheet]) -> Option<&Sheet> {
    sheets.iter().find(|s| s.name.to_ascii_lowercase().contains("graded"))
}

fn pom_row(sheet: &Sheet, pom: &str) -> Option<Vec<f64>> {
    // Size grid occupies columns 4..=9 (XS..XXL) on this chart.
    for row in &sheet.rows {
        if row.first().map(|c| c.text.trim() == pom).unwrap_or(false) {
            return Some(
                (4..10)
                    .map(|c| row.get(c).and_then(|cell| cell.num).unwrap_or(f64::NAN))
                    .collect(),
            );
        }
    }
    None
}

#[test]
fn xlsx_reads_graded_spec_sheet_exact_values() {
    let bytes = match sample("CL1086464.xlsx") {
        Some(b) => b,
        None => return,
    };
    let sheets = read_xlsx(&bytes).expect("xlsx should parse");
    // Sheet names in workbook order are recovered.
    let names: Vec<&str> = sheets.iter().map(|s| s.name.as_str()).collect();
    assert!(names.iter().any(|n| n.to_ascii_lowercase().contains("graded")), "names = {:?}", names);

    let sheet = graded_sheet(&sheets).expect("graded spec sheet present");

    let r20125 = pom_row(sheet, "20125").expect("POM 20125 row");
    assert_eq!(&r20125[..], &SPEC_POM_20125, "POM 20125 size values");

    let r21885 = pom_row(sheet, "21885").expect("POM 21885 row");
    assert_eq!(&r21885[..], &SPEC_POM_21885, "POM 21885 (inseam) size values");
}

#[test]
fn xlsx_tsv_matches_python_extract_byte_for_byte() {
    let bytes = match sample("CL1086464.xlsx") {
        Some(b) => b,
        None => return,
    };
    let reference = match sample("spec_graded.tsv") {
        Some(b) => String::from_utf8_lossy(&b).into_owned(),
        None => return,
    };
    let sheets = read_xlsx(&bytes).expect("xlsx should parse");
    let sheet = graded_sheet(&sheets).expect("graded spec sheet present");
    let tsv = sheet_to_tsv(sheet);
    assert_eq!(tsv, reference, "TSV of the graded sheet must match the Python extract exactly");
}

#[test]
fn pant_geometry_golden() {
    let bytes = match sample("pant_1074664.PDS") {
        Some(b) => b,
        None => return,
    };
    let doc = pds_bin::decode(&bytes).expect("pant should decode");
    assert!(doc.decoded_geometry, "{:#?}", doc.warnings);
    let find = |name: &str, size: &str| {
        doc.pieces.iter().find(|p| p.name == name && p.size == size).unwrap_or_else(|| panic!("missing {} {}", name, size))
    };
    let (w, h, per) = bbox(&find("WAIST- BELT", "S").cut);
    golden_eq!("pant/belt-S/width", w, PANT_BELT_S_W, 0.05);
    golden_eq!("pant/belt-S/height", h, PANT_BELT_S_H, 0.05);
    golden_eq!("pant/belt-S/perimeter", per, PANT_BELT_S_PER, 0.1);
    let (fw, fh, _) = bbox(&find("FRONT", "S").cut);
    golden_eq!("pant/front-S/width", fw, PANT_FRONT_S_W, 0.01);
    golden_eq!("pant/front-S/height", fh, PANT_FRONT_S_H, 0.01);
}

#[test]
fn golden_report_all_pass() {
    let pant = sample("pant_1074664.PDS");
    let spec = sample("CL1086464.xlsx");
    if pant.is_none() && spec.is_none() {
        return;
    }
    let report = golden_report(pant.as_deref(), spec.as_deref());
    let failed = report.get("failed").and_then(|v| v.as_f64()).unwrap_or(-1.0);
    let passed = report.get("passed").and_then(|v| v.as_f64()).unwrap_or(0.0);
    assert!(passed > 0.0, "expected some golden cases to run: {}", report.to_string());
    assert_eq!(failed, 0.0, "golden report has failures: {}", report.to_string());
    assert_eq!(report.get("ok").and_then(|v| v.as_bool()), Some(true));
}
