# Zero-dependency .xlsx reader (`src/xlsx_read.rs`)

Item #51: parse Excel specs with no external package (no `xlsx` npm, no openpyxl). Pure Rust, no
`unsafe`, no threads, no clock, no file IO: it works on a `&[u8]`, so it is wasm-safe.

## API

```rust
pub struct Cell  { pub text: String, pub num: Option<f64> }
pub struct Sheet { pub name: String, pub rows: Vec<Vec<Cell>> }   // rows padded to equal width
pub fn read_xlsx(bytes: &[u8]) -> Result<Vec<Sheet>, String>
pub fn sheet_to_tsv(&Sheet) -> String
```

* `text` is display text: shared/inline string, formula-string result, bool (`TRUE`/`FALSE`), error
  text, number as its **shortest round-trip** form (`36.599999999999994`; `35.299999999999997`
  becomes `35.3`), or `YYYY-MM-DD HH:MM:SS` for cells whose style is a date format.
* `num` is `Some(f64)` for numeric and date cells (a date holds the Excel serial), else `None`.
* Sheets come back in workbook order; names are XML-unescaped but not trimmed (the real file has
  a sheet called `" graded spec sheet "`, with spaces).

## What is implemented

1. ZIP: end-of-central-directory scan, central directory, local headers; STORED and DEFLATE;
   ZIP64 EOCD / extra-field sizes are read too, though untested (no ZIP64 sample).
2. Own RFC 1951 inflate (stored, fixed and dynamic Huffman). The repo had none to reuse
   (`pds_bin.rs` has no inflate; it is an XOR-obfuscated float stream).
3. `xl/workbook.xml` (names, `r:id`), `xl/_rels/workbook.xml.rels`, `xl/sharedStrings.xml` (rich
   text runs flattened), `xl/styles.xml` (`cellXfs` to date-format detection), `worksheets/*.xml`.

## Validation against the real file

`tests/golden.rs` reads `/home/claude/samples/CL1086464.xlsx` (override dir with `PDS_SAMPLE_DIR`):
finds the graded sheet, checks POM 20125 = 33, 35, 37, 39.5, 42, 44.5 and POM 21885 = 77..82,
and requires `sheet_to_tsv` to equal `samples/spec_graded.tsv` **byte for byte** (including the
two date cells and the long float strings).

## Robustness

Fuzz tests (`xlsx_read::tests`): every truncation prefix of a synthetic zip, 4000 random byte
corruptions, random short buffers, 60 truncations and 60 bit-flip corruptions of the real file.
None may panic. Defences: all reads bounds-checked; inflate output capped (4x the declared size,
min 1 MiB, max 1 GiB); cell coordinates beyond 200,000 rows or 1,024 columns are ignored; a
grid that would exceed 8M cells yields an empty sheet.

## Coverage limits (honest)

* Not parsed: formulas (only cached values), merged cells, hidden rows/sheets (hidden sheets are
  returned), comments, drawings/images, charts, `.xls`, `.xlsb`, encrypted files, shared formulas.
* Date detection is a heuristic on the number format (built-in ids 14-22, 45-47, or custom codes
  containing y/m/d/h/s). The 1904 date system (`date1904`) is NOT handled. Percent/currency/
  custom formats are not applied: numbers show raw, never as Excel would display them.
* Entry names are matched case-sensitively; relationship targets are resolved under `xl/` only.
* Only verified against one real workbook (Excel-written) plus synthetic zips. Files from other
  writers (LibreOffice, Google Sheets, openpyxl) are expected to work but are unverified.
* The inflate is not tuned for speed. The 2 MB sample reads in well under a second, but nothing
  was benchmarked on big files.
* CRC32 is not checked, so a bit-flipped stored entry is read as is.

## Wiring snippet (not applied; api.rs untouched)

```rust
// in api.rs dispatch(); needs a base64 decoder (pds_api.rs has a private b64_decode: make it pub(crate)).
"xlsx_to_tsv" => {
    let bytes = crate::pds_api::b64_decode(req_str(j, "data_b64")?)?;
    let sheets = crate::xlsx_read::read_xlsx(&bytes)?;
    Ok(Json::obj().set("sheets", Json::Arr(sheets.iter().map(|s|
        Json::obj().set("name", Json::str(&s.name))
                   .set("tsv", Json::str(&crate::xlsx_read::sheet_to_tsv(s)))).collect())))
}
```
The TSV text can then go to the existing spec importer (`spec.rs`) as the pasted-table input.
