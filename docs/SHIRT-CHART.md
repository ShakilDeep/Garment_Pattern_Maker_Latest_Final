# Shirt measurement chart (`garment_measurement_chart.xlsx`)

Style 1078983-RPT, MAN SHIRT, base size L, sizes S–3XL (long sleeve).

## How rows map to the drafter
- Rows are matched by code, then by name (`spec::canon_by_name`). Unrecognised rows can be mapped by hand in the Measurements panel.
- Derived values (`ShirtSpec::from_map_checked`):
  - Neck width (full) → front neck width = v/2, back neck width = v/2 + sample back−front difference.
  - Collar length (half) → neck size = 2·v + (sample neck − 2·21.55).
  - Cuff edge-to-edge (full) → sleeve opening = v/2.
  - Sleeve cap height → underarm height = sleeve length − cap height. Without it, a sleeve of 40 cm or more keeps the sample cap height (16.5 cm), so the underarm seam grows with the length.

## Not drafted
Cuff, sleeve placket, collar outer edge. X10 (curved corner height 5) is not mapped to hem curve (valid range 0–4).

## Needs checking in Optitex
The neck, collar and cap-height mappings are calibrated or derived, not independently verified.

Regression tests: `tests/shirt_chart.rs`, `web/e2e/test_chart.py`.
