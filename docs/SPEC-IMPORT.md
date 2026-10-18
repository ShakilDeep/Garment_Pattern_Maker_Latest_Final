# Spec sheet (POM) import and grading

Module: `src/spec.rs` (`patternforge::spec`). Pure Rust, no dependencies, text in / JSON out.
The web UI converts `.xlsx` to text with SheetJS (`sheet_to_csv` with `FS:"\t"`, or plain paste from
Excel) and passes the **text** to `parse_spec_text`.

## Accepted input

* Delimiter is auto-detected (tab, `;`, `|`, `,`; whichever is on most lines, tab favoured).
* RFC4180 quoting (`"a, b"`, `""`). A quote only opens a quoted cell at the *start* of a cell, so
  Excel-pasted cells such as `KNEE WIDTH 12"` are fine. An unterminated quote is treated literally.
* BOM, CRLF, NBSP, blank cells, merged-cell gaps (empty columns) are tolerated.
* **Header block**: any `LABEL : value` pairs above the table, label and value in separate cells
  (value = next non-empty cell) or in one cell (`STYLE# : 1086464`). Recognised labels:
  `STYLE#/STYLE NO`, `STYLE DESCRIPTION/DESCRIPTION`, `BRAND`, `SEASON`, `BASE PATTERN / FIT`/`FIT`,
  `SIZE / RANGE`, `BASE SIZE/SAMPLE SIZE`. Unknown labels (manufacturer, wash, ...) are ignored.
* **Table header row** = first row containing a `POM` cell (also `POM CODE`, `CODE`, `POINT OF MEASURE`)
  followed by size labels (`XXS..5XL`, `2XL`, `OS`, numeric 0-70). Without a `POM` cell, a row with
  at least two alpha size labels is used and codes are derived from names.
  Column roles: name column = first non-empty header cell after POM; *local name* = first non-empty cell
  between the name column and the first size (the sheet's unlabeled Turkish column); tolerance column(s)
  = header cells containing `tol` (one column applies to + and -; two columns are split by `+`/`-`/`plus`/`minus`).
* **Numbers**: `35`, `36.599999999999994` (rounded to 0.01 cm), decimal comma `0,5`, fractions `1/2`,
  `3 1/2`, `3½`, `-1/4`, `12 cm`, thousands `1,234.5` / `1.234,5`. `-`, `--`, `N/A`, `/` are blank.
  Dates (`17.03.2026`) and `NaN/inf` are rejected, never parsed as numbers.
* The first table wins; a second `POM` header row ends the table (warning).
* Garbage, empty text, > 4 MB, header without rows -> `Err(String)`. Never panics (covered by a fuzz-style test).
  Non-fatal oddities (unreadable cell, duplicate code, row without code) go to `SpecSheet.warnings`.

## Data model

```rust
pub struct PomRow { code, name, name_local: String, values: Vec<f64> /* NaN = blank */, tol_plus, tol_minus: f64 /* NaN = missing */ }
pub struct SpecSheet { style, description, brand, fit, season: String, sizes: Vec<String>, base_size: String, rows: Vec<PomRow>, warnings: Vec<String> }
```

Values are cm and are usually **half-garment** widths (see `is_half_measure`); multiply by 2 for the
circumference before feeding a full-circumference engine such as `Measurements`. Base size: the declared
`BASE SIZE`/`SAMPLE SIZE` if present, else `M` if present, else the lower middle size (single size `S` -> `S`).
Callers can overwrite `base_size`.

## API

| item | purpose |
|---|---|
| `parse_spec_text(&str) -> Result<SpecSheet,String>` | import |
| `parse_number(&str) -> Option<f64>` | number/fraction/decimal-comma reader |
| `SpecSheet::to_json / from_json` | NaN <-> `null`; `from_json` validates lengths |
| `size_map(size)` | `{POM code: value}` (case-insensitive size) |
| `name_map(size)` | `{snake_case name: value}` (`1/2`/`½` -> `half`, collisions `_2`) |
| `canonical_map(size)` | `{canonical key: value}` |
| `grade_increments()` | `[(code, deltas between consecutive sizes)]` |
| `extrapolate(label, from, steps)` | `{code: value}`; inside the range uses real increments, beyond it the last (up) / first (down) increment |
| `add_extrapolated_size(label, from, steps)` | appends the column to the sheet |
| `check()` | sanity warnings (below) |
| `spec_to_grade_table()` | UI grade-table JSON (below) |
| `canonical_pom(code, name)` | code/name -> canonical key |

### `check()` warnings

missing/negative tolerance; blank cells in a row; value < 0 or > 250 cm; value 0 (except hem height);
value outside the plausible range for its canonical key (with an `(inches?)` hint when value x 2.54 fits);
tolerance > 20 % of value; non-monotonic grading; value decreasing with size; jump > 20 % between sizes;
waist stretched < waist relaxed; seat < relaxed waist; back rise < front rise; base size not in sizes.
The real Colin's sheet produces none.

### `spec_to_grade_table()` shape

Mirrors the `grade` op response consumed by `GradingView.tsx` (`GradedSize`: `label, step, measurements, table[{piece, deltas}]`):

```json
{"spec":true,"base":"M",
 "sizes":[{"label":"L","step":1,
           "measurements":{"20125":39.5, ...},
           "table":[{"piece":"1/2 WAIST AT TOP EDGE","code":"20125","deltas":[[2.5,0]]}, ...]}, ...],
 "tolerances":{"20125":{"plus":1,"minus":1}, ...}}
```

`step` = index offset from the base size, `deltas` = one 1-D "node" `[value - base_value, 0]` per POM,
so the existing table renders unchanged (there is no `pattern` field: spec grading has no geometry).

## Canonical POM keys

Bottoms (matched by **code**, then by name; Colin's chart `CL.UR.S06-F20`):

| code | key | | code | key |
|---|---|---|---|---|
| 20125 | `half_waist_relaxed` | | 20905 | `half_knee` |
| 20245 | `half_waist_stretched` | | 21125 | `half_leg_opening` |
| 20305 | `half_seat` | | 30210 | `hem_height` |
| 20305-A | `hip_pos_side_seam` | | 21885 | `inseam` |
| 20305-B | `hip_pos_center_front` | | 20265 | `waistband_width` |
| 20865 | `half_thigh` | | 22145 | `pocket_opening_waist` |
| 21505 | `front_rise` | | 22165 | `pocket_opening_side` |
| 21545 | `back_rise` | | 22565 / 30845 | `pocket_bag_depth` / `drawcord_half` |

Code matching ignores spaces/dashes/case (`20305 a` = `20305-A`).

Tops (by **name keywords** only, English plus a few Turkish words): `half_chest`, `across_chest`,
`across_back`, `across_shoulder`, `shoulder_drop`, `armhole`, `half_bicep`, `sleeve_length`,
`half_sleeve_opening`, `cuff_height`, `collar_length`, `collar_height`, `collar_stand_height`,
`collar_point_length`, `collar_spread`, `neck_width`, `neck_drop`, `back_neck_drop`,
`neck_circumference`, `body_length`, `front_length`, `hem_sweep`, `hem_height`, `half_waist`,
`placket_width`, `placket_length`, `pocket_width`, `pocket_length`, `yoke_depth`, `strap_width`, `outseam`, `rise`.

### Unmapped codes / limitations

* **`shirt_1078375_techpack.pdf` contains no measurement table.** Its 6 pages are cover, options,
  technical details (stitching/labels), fabrics and two BOM pages (`pdftotext -layout` shows no POM, no
  sizes, no tolerances; the sibling `.PDS`/Optitex XML has none either). So **no top POM codes are known**
  and tops are mapped by name only. When a real shirt spec arrives, add its codes to the `by_code`
  match in `canonical_pom` (one line each) and extend `tops` tests.
* `CL1086464_techpack.pdf` only refers to a "measurement chart" (placement of the woven label); the
  chart itself is the xlsx, all 17 of its codes are mapped.
* Unmapped rows are kept in `rows`/`size_map`/`name_map`; they just have no canonical key.
* A sheet that records a FULL circumference under a "half" key is not detected; `check()`'s
  plausibility ranges (e.g. half seat 25..100 cm) catch the gross cases.

## Tests

`cargo test --release --offline spec` runs 12 tests. Fixtures (TSV paste, CSV, single-size TSV) are
embedded in the test module, generated once from `CL1086464.xlsx`. They cover: 17 rows x 6 sizes with
exact values (`20125 -> 33,35,37,39.5,42,44.5`, `21545 -> 40,41,42,43.3,44.6,45.9`), float noise
(`36.599999999999994 -> 36.6`), decimal-comma tolerance, TSV/CSV/`;`/CRLF/BOM parity, quotes, fractions,
garbage input, a pseudo-fuzz run, JSON round trip, grade-table shape and every `check()` rule.
