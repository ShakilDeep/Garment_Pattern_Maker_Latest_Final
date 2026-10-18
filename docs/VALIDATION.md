# Pattern validation and regression harness (`src/validate.rs`, `tests/golden.rs`)

Items #40, #43, #45. Deterministic, never panics, wasm-safe (no threads/clock/IO).

## API

```rust
pub enum Severity { Error, Warn, Info }
pub struct ValIssue { severity, rule: String, detail: String, pieces: Vec<String>,
                      value: f64, expected: f64, tol: f64 }
pub struct ValOpts { seam_tol, seam_warn_band, notch_tol, cap_ease_min, cap_ease_max_frac,
                     cap_ease_max_floor, collar_tol, min_area }      // Default provided
pub fn validate_pattern(&Pattern) -> Vec<ValIssue>                   // default tolerances
pub fn validate_pattern_opts(&Pattern, &ValOpts) -> Vec<ValIssue>
pub fn validate_json(&Pattern) -> Json     // {issues:[..], counts:{error,warn,info}, ok}
pub fn golden_report(pant_pds: Option<&[u8]>, spec_xlsx: Option<&[u8]>) -> Json
```
`ok` is true when there are no `Error` issues. Defaults: seam tol 0.2 cm, notch tol 0.3 cm,
warn band 1.5 cm.

## Rules

| rule | what it checks | severity |
|---|---|---|
| `seam-balance` | `Piece::tag_len` of both sides of every `Seam` within `seam_tol`. Fold seams (same piece+tag) and cap/armhole seams are skipped. | Warn within 1.5 cm, else Error; always Warn for gather/partial-seam tags (`waist`, `opening`, `pocket`, `bag`, `outseam_top`) |
| `notch-align` | notches on both sides: same count, positions (arc length from seam start, `rev` honoured) within `notch_tol` | Warn |
| `cap-ease` | sum(cap seams) minus sum(armhole seams) inside [`cap_ease_min`, max(12% of armhole, 4.5 cm)] | Info in band, Warn out, Error far out |
| `collar-fit` | collar/stand vs neckline. Not a separate generic rule: it comes through `garment_checks` (shirt "Neck opening vs stand", tol 2 cm) | Warn |
| `geometry` | fewer than 3 nodes, non-finite coordinate, area <= `min_area`, self-intersecting sew or cut outline (`mesh::self_intersects`) | Error |
| `structure` | `garments::check_pattern` failures not already reported (e.g. seam naming a missing edge) | Error |

`garments::garment_checks` (calibrated for the drafted shirt/pant) is wrapped, not duplicated:
each `Check` becomes a `ValIssue` (Info when it passes, else Warn or Error by name class). When
it supplies a cap-ease check, it replaces the generic `cap-ease` entry.

## Coverage limits (honest)

* The generic rules rely on the pattern's own `Seam` records and edge tags. A pattern with no
  seams gets only the geometry rules.
* Collar fit is only verified through the shirt-specific `garment_checks`; arbitrary garments
  with differently named collar tags are not covered.
* Cap ease is found by tag name containing "cap" joined to a tag containing "armhole". The
  band is a heuristic, not a standard: woven shirt sleeves run roughly 2-5 cm, set-in jacket
  caps more, knits less or negative. Tune `ValOpts` per garment type.
* The notch rule sees only `Pattern` notches. Notches decoded from PDS files are not in the
  `Pattern` model and are not checked.
* The `intentional mismatch` downgrade is by tag name; a real error on a `waist` seam shows as a
  Warn. It was needed because the drafted pant legitimately has waist-to-belt differences of
  2.6-3.2 cm and a pocket opening vs partial side seam of 10 cm.
* Tested on the default drafted shirt and pant (zero errors) and on synthetic faulty patterns
  (unequal seam, collinear piece, NaN coordinates, inflated sleeve cap). Not tested against real
  production patterns with known defects.

## Regression harness (#43/#45)

`tests/golden.rs` (integration tests; each skips, not fails, when its sample file is absent):

* `pant_geometry_golden`: decodes `pant_1074664.PDS`, size S: belt 105.6 x 13.0 cm, perimeter
  237.2 cm; FRONT 108.8272 x 31.8795 cm (tol 0.01-0.1 cm).
* `xlsx_reads_graded_spec_sheet_exact_values`: POM 20125 and 21885 across XS..XXL, exact.
* `xlsx_tsv_matches_python_extract_byte_for_byte`.
* `golden_report_all_pass`.

`golden_report(pant, spec)` returns `{cases:[{name,measured,expected,tol,pass}], passed, failed, ok}`.
The host supplies file bytes (no IO inside the library). The reference consts exist twice (tests
and `validate.rs`); keep them in sync.

### Adding a new golden file (item #45)

1. Put the spec `.xlsx` and `.PDS` in the samples dir (default `/home/claude/samples`, or set
   `PDS_SAMPLE_DIR`).
2. Read it once and print the quantities to pin (`--nocapture`): for geometry, bbox width,
   height, perimeter of chosen pieces/sizes from `pds_bin::decode`; for a spec, the POM rows
   from `read_xlsx` (size grid is columns 4..=9 on this chart layout, check yours).
3. Paste those numbers as `const`s in `tests/golden.rs`, add `golden_eq!(name, measured,
   expected, tol)` assertions. Choose tol from the decode residual (0.01 cm for bbox, 0.1 cm
   for perimeter); specs are exact (tol 1e-9).
4. Mirror the consts and cases into `golden_report` in `src/validate.rs` so the app shows them.
5. When both a real spec and a PDS exist for the same style, add a cross-check: draft from the
   spec (`PantSpec::from_pom_checked` + `draft_pant_detailed`) and assert the drafted measured
   quantities against the PDS-decoded ones. This pairing is the real value of #45 and is NOT done
   yet (the two samples here are different styles: 1086464 spec vs 1074664 PDS).

Limitation: only one spec and one decoded PDS exist, from different styles, so the golden suite
pins decoder and reader stability; it does not prove the drafting matches production patterns.

## Wiring snippet (not applied; api.rs untouched)

```rust
"validate" => {
    let p = Pattern::from_json(j.get("pattern").ok_or("missing pattern")?)?;
    Ok(crate::validate::validate_json(&p))
}
"golden_report" => {
    let dec = |k: &str| j.get(k).and_then(|v| v.as_str()).map(crate::pds_api::b64_decode).transpose();
    let (pds, xlsx) = (dec("pds_b64")?, dec("xlsx_b64")?);
    Ok(crate::validate::golden_report(pds.as_deref(), xlsx.as_deref()))
}
```
(`b64_decode` is private in `pds_api.rs`: make it `pub(crate)`.)
