# PDS import (`src/pds_import.rs`)

Imports the **readable** parts of Optitex `.PDS` files. Native PDS is a proprietary binary container; what is
readable is the clear-text `<?xml ...?><STYLE>...</STYLE>` block embedded in it. The parser scans the raw bytes
for `<STYLE` ... `</STYLE>` (so it also works when the binary bytes were mangled, e.g. replaced by `EF BF BD`,
and on a bare extracted `.xml`), decodes lossily and runs a small tolerant XML scanner (no dependencies).

## API

```rust
pub fn import_pds(bytes: &[u8]) -> Result<Json, String>            // full result, see below
pub fn analyze_pds(bytes: &[u8]) -> Result<Analysis, String>       // same + typed match diagnostics
pub fn parse_pds(bytes: &[u8]) -> Result<PdsDocument, String>      // XML + marker only, no matching
pub fn import_pds_pieces(bytes: &[u8]) -> Result<Vec<PdsPiece>, String>
pub fn extract_xml_block(bytes: &[u8]) -> Result<(String, bool /*truncated*/), String>
```

`import_pds` returns `{style, pieces, marker, pattern, warnings, geometry_source:"marker_svg_preview"}`:

* `style`: name, version, date, units, filename, sizes, base_size, pieces_count (+ declared counts, size table,
  `base_sums_check` = SIZES_TABLE sums vs `sum(quantity * piece value)`).
* `pieces[]`: name, code, unique, material, quantity, half, position, `nesting{rotation,tilt,shrink,opposite}`,
  `sizes[{name,size_x,size_y,area_m2,perimeter,sew_area_m2,sew_perimeter}]`, `notch_count`, `t_notch_count`,
  plus `outlines` (marker outline indices), `match_confidence`, `worst_perimeter_err`, `marker_notch_count`.
* `marker`: width/height (viewBox, marker units), `units_per_cm`, `size` (size the marker shows), `scale_fit`,
  `outlines[{cut, sew, notches, grain, internal, seam_allowance_cm, origin_cm, piece, match{...}}]` in raw
  marker units (y down).
* `pattern`: a PatternForge `Pattern` JSON (`Pattern::from_json` round-trips it): one piece per marker outline,
  y-up cm, local origin at the cut bbox minimum, CCW, straight corner nodes. Nodes are the **sew** polygon (cut
  polygon if no sew line), `sa` = length-weighted median sew-to-cut distance, per-edge `sa` overrides (e.g. 0 on
  fold edges), notches mapped to (edge, t), grain flipped to y-up. Zone is `"imported"`, no seams.

## How outlines are matched (the important part)

Marker coordinates are integers in an undocumented unit (100 units/cm in both samples, but this is *derived*, not
assumed). For every candidate size (base size first) the importer:

1. votes for scale ratios from (outline, piece) pairs whose sorted bbox sides agree with GEOM_INFO SIZE_X/SIZE_Y,
2. scores the best candidates by the summed best-match cost, refines by trimmed least squares (bbox sides and
   perimeters), then assigns outlines to pieces greedily by cost with capacity (2 for folded pieces),
3. picks the size that explains the marker best (ties favour BASE_SIZE; a warning is raised if the marker shows
   another size than BASE_SIZE),
4. reports per outline: `dims_err`, `perimeter_err`, `area_err`, `sew_perimeter_err`, `sew_area_err`,
   `rotated_90`, `ambiguous_with`, `confidence` (high <=2%, medium <=5%, else low; non-high goes into `warnings`).

Semantics learned from the samples: `SIZE_X/Y` are the bbox of the outline as shown (rotated 90 deg is handled by
sorting sides); `GEOM_INFO` AREA/PERIMETER are cut values; `SUM_*` = sum(quantity * piece value); the marker
holds one outline per piece pair (quantity 2 with Up/Down opposite shows once). **`HALF=CLOSE` pieces** are drawn
as two folded halves, while AREA/PERIMETER are for the closed piece: expected half area = AREA/2 and expected
half perimeter = PERIMETER/2 + fold length. The fold length is not in the XML, so for folded pieces the
perimeter error is only indicative (min over fold = SIZE_X or SIZE_Y) and confidence uses dims + area.
Pieces with identical GEOM_INFO (e.g. `BND TOP` / `BND IN`) are flagged as indistinguishable; their assignment
is arbitrary (marker order).

## Limits (also emitted in `warnings`)

* Preview quality: **base/marker size only**, integer marker resolution, straight segments, no curves, no
  grading rules, no parametric data. Mirror placement is not detected. Not a substitute for the real geometry.
* The binary section is never read.
* Caps: input 256 MiB, XML 64 MiB, 400k elements, depth 64, 500 pieces, 200 sizes, 1000 outlines, 50k points per
  polygon, 2M marker points. Non-finite / out-of-range numbers are rejected with a warning. Truncated or garbled
  input gives partial results plus warnings (or `Err`), never a panic.

## Tests

`cargo test --release --offline pds_import -- --nocapture` prints a diagnostic table per sample (set
`PDS_SAMPLES_DIR`, default `/home/claude/samples`; sample tests skip if files are missing).
