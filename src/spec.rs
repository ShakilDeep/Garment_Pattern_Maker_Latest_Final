//! Garment SPEC SHEET (POM = point of measure) import, grading and sanity checks.
//!
//! Input is *text* (TSV, CSV, `;`-CSV, `|`-separated, or pasted straight from Excel); the web UI
//! converts xlsx to text with SheetJS and passes it here. See `docs/SPEC-IMPORT.md`.
//!
//! Layout understood:
//! * header block of `LABEL : value` pairs (style#, description, brand, season, fit, size range ...)
//! * a table header row `POM | MEASUREMENT POINTS | <local name> | XS | S | M ... | tolerance`
//! * data rows; values in cm, usually HALF-garment measures, cells may use decimal commas or
//!   fractions (`0,5`, `1/2`, `3 1/2`, `3½`); float noise is rounded to 0.01 cm.
//!
//! Strings are never sliced by byte offsets other than at ASCII delimiters, so Turkish / any
//! Unicode text is safe.
use crate::json::Json;
use std::collections::BTreeMap;

const MAX_INPUT: usize = 4_000_000;
const MAX_ROWS: usize = 2000;
const MAX_SIZES: usize = 40;

/// One point of measure. Missing values (blank cells) are `NaN`; use [`PomRow::value`] for `Option`.
/// Missing tolerance is `NaN` too (a real tolerance of 0 is kept as 0).
#[derive(Clone, Debug)]
pub struct PomRow {
    pub code: String,
    pub name: String,
    pub name_local: String,
    pub values: Vec<f64>,
    pub tol_plus: f64,
    pub tol_minus: f64,
    /// Manual choice of the drafter field this row drives (overrides the automatic code/name mapping).
    pub map_to: Option<&'static str>,
}

impl PomRow {
    /// Value for size column `i`, `None` if blank/NaN/out of range.
    pub fn value(&self, i: usize) -> Option<f64> {
        self.values.get(i).copied().filter(|v| v.is_finite())
    }
    pub fn has_tolerance(&self) -> bool {
        self.tol_plus.is_finite() && self.tol_minus.is_finite()
    }
}

impl PartialEq for PomRow {
    fn eq(&self, o: &Self) -> bool {
        fn feq(a: f64, b: f64) -> bool {
            (a.is_nan() && b.is_nan()) || a == b
        }
        self.code == o.code
            && self.name == o.name
            && self.name_local == o.name_local
            && self.values.len() == o.values.len()
            && self.values.iter().zip(&o.values).all(|(a, b)| feq(*a, *b))
            && feq(self.tol_plus, o.tol_plus)
            && feq(self.tol_minus, o.tol_minus)
            && self.map_to == o.map_to
    }
}

#[derive(Clone, Debug, PartialEq, Default)]
pub struct SpecSheet {
    pub style: String,
    pub description: String,
    pub brand: String,
    pub fit: String,
    pub season: String,
    pub sizes: Vec<String>,
    pub base_size: String,
    pub rows: Vec<PomRow>,
    pub warnings: Vec<String>,
}

// ---------------------------------------------------------------------------------------------
// text helpers

/// Upper-case and fold Turkish letters to ASCII (İ Ş Ğ Ü Ö Ç, dotless ı) for keyword matching.
fn fold_upper(s: &str) -> String {
    let mut o = String::with_capacity(s.len());
    for c in s.chars() {
        for u in c.to_uppercase() {
            o.push(match u {
                'İ' => 'I',
                'Ş' => 'S',
                'Ğ' => 'G',
                'Ü' => 'U',
                'Ö' => 'O',
                'Ç' => 'C',
                x => x,
            });
        }
    }
    o
}

/// Folded upper-case, non-alphanumerics -> single spaces. `"BASE PATTERN / FIT :"` -> `"BASE PATTERN FIT"`.
fn keyify(s: &str) -> String {
    let f = fold_upper(s);
    let mut o = String::with_capacity(f.len());
    let mut last_space = true;
    for c in f.chars() {
        if c.is_alphanumeric() {
            o.push(c);
            last_space = false;
        } else if !last_space {
            o.push(' ');
            last_space = true;
        }
    }
    while o.ends_with(' ') {
        o.pop();
    }
    o
}

fn clean_cell(s: &str) -> String {
    let t: String = s.chars().map(|c| if c == '\u{a0}' || c == '\r' || c == '\n' || c == '\u{feff}' { ' ' } else { c }).collect();
    t.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn round2(x: f64) -> f64 {
    let r = (x * 100.0).round() / 100.0;
    if r == 0.0 { 0.0 } else { r }
}

/// Parse a spec-sheet number: `35`, `36.599999999999994`, `0,5`, `1/2`, `3 1/2`, `3½`, `-1/4`,
/// `12 cm`, `1,234.5`. Returns the raw value (not rounded). `None` if not a number.
pub fn parse_number(s: &str) -> Option<f64> {
    let mut t = String::new();
    for ch in s.trim().chars() {
        match ch {
            '\u{2212}' | '\u{2013}' => t.push('-'),
            '\u{a0}' => t.push(' '),
            '½' => t.push_str(" 1/2"),
            '¼' => t.push_str(" 1/4"),
            '¾' => t.push_str(" 3/4"),
            '⅓' => t.push_str(" 1/3"),
            '⅔' => t.push_str(" 2/3"),
            '⅛' => t.push_str(" 1/8"),
            '⅜' => t.push_str(" 3/8"),
            '⅝' => t.push_str(" 5/8"),
            '⅞' => t.push_str(" 7/8"),
            c => t.push(c),
        }
    }
    let mut t = t.trim();
    if t.len() >= 2 && t.is_char_boundary(t.len() - 2) && t[t.len() - 2..].eq_ignore_ascii_case("cm") {
        t = t[..t.len() - 2].trim_end();
    }
    let (neg, rest) = if let Some(r) = t.strip_prefix('-') {
        (true, r)
    } else if let Some(r) = t.strip_prefix('+') {
        (false, r)
    } else {
        (false, t)
    };
    let rest = rest.trim();
    if rest.is_empty() || rest.len() > 40 {
        return None;
    }
    let all_digits = |x: &str| !x.is_empty() && x.bytes().all(|b| b.is_ascii_digit());
    let v: f64 = if rest.contains('/') {
        let toks: Vec<&str> = rest.split_whitespace().collect();
        let (whole, frac) = match toks.len() {
            1 => (0.0, toks[0]),
            2 if all_digits(toks[0]) => (toks[0].parse::<f64>().ok()?, toks[1]),
            _ => return None,
        };
        let mut it = frac.split('/');
        let (n, d) = (it.next()?, it.next()?);
        if it.next().is_some() || !all_digits(n) || !all_digits(d) {
            return None;
        }
        let (n, d) = (n.parse::<f64>().ok()?, d.parse::<f64>().ok()?);
        if d == 0.0 {
            return None;
        }
        whole + n / d
    } else {
        if !rest.bytes().all(|b| b.is_ascii_digit() || b == b'.' || b == b',') || !rest.bytes().any(|b| b.is_ascii_digit()) {
            return None;
        }
        let (dots, commas) = (rest.matches('.').count(), rest.matches(',').count());
        let norm: String = if dots > 0 && commas > 0 {
            let (ld, lc) = (rest.rfind('.')?, rest.rfind(',')?);
            if ld > lc {
                rest.replace(',', "") // 1,234.5
            } else {
                rest.replace('.', "").replace(',', ".") // 1.234,5
            }
        } else if commas == 1 {
            rest.replace(',', ".")
        } else if commas > 1 {
            let parts: Vec<&str> = rest.split(',').collect();
            let ok = (1..=3).contains(&parts[0].len()) && parts[1..].iter().all(|p| p.len() == 3) && parts.iter().all(|p| all_digits(p));
            if !ok {
                return None;
            }
            rest.replace(',', "")
        } else if dots > 1 {
            return None; // 17.03.2026
        } else {
            rest.to_string()
        };
        norm.parse::<f64>().ok()?
    };
    if !v.is_finite() {
        return None;
    }
    Some(if neg { -v } else { v })
}

fn is_blank_placeholder(s: &str) -> bool {
    matches!(s.trim(), "" | "-" | "--" | "—" | "–" | "/" | "n/a" | "N/A" | "na" | "NA" | "#N/A")
}

// ---------------------------------------------------------------------------------------------
// delimited text -> records

fn detect_delimiter(text: &str) -> char {
    let (mut tab, mut semi, mut pipe, mut comma) = (0usize, 0usize, 0usize, 0usize);
    for line in text.lines().take(400) {
        if line.contains('\t') { tab += 1; }
        if line.contains(';') { semi += 1; }
        if line.contains('|') { pipe += 1; }
        if line.contains(',') { comma += 1; }
    }
    let cands = [('\t', tab * 2), (';', semi), ('|', pipe), (',', comma)];
    let mut best = (',', 0usize);
    for (c, n) in cands {
        if n > best.1 {
            best = (c, n);
        }
    }
    best.0
}

/// RFC4180-ish reader. A quote only opens a quoted field at the *start* of a field (so `12"` in
/// the middle of a cell is literal, as in Excel-pasted TSV). An unterminated quote is literal.
fn parse_records(text: &str, delim: char) -> Vec<Vec<String>> {
    let ch: Vec<char> = text.chars().collect();
    let n = ch.len();
    let mut recs: Vec<Vec<String>> = Vec::new();
    let mut rec: Vec<String> = Vec::new();
    let mut field = String::new();
    let mut i = 0;
    let mut quotes_possible = true;
    let mut field_start = true;
    while i < n {
        let c = ch[i];
        if c == '"' && field_start && quotes_possible {
            let mut j = i + 1;
            let mut buf = String::new();
            let mut closed = false;
            while j < n {
                if ch[j] == '"' {
                    if j + 1 < n && ch[j + 1] == '"' {
                        buf.push('"');
                        j += 2;
                        continue;
                    }
                    closed = true;
                    break;
                }
                buf.push(ch[j]);
                j += 1;
            }
            if closed {
                field.push_str(&buf);
                i = j + 1;
                field_start = false;
                continue; // trailing junk up to the delimiter is appended by the normal path
            }
            quotes_possible = false;
        }
        if c == delim {
            rec.push(std::mem::take(&mut field));
            field_start = true;
        } else if c == '\n' || c == '\r' {
            if c == '\r' && i + 1 < n && ch[i + 1] == '\n' {
                i += 1;
            }
            rec.push(std::mem::take(&mut field));
            recs.push(std::mem::take(&mut rec));
            field_start = true;
        } else {
            field.push(c);
            field_start = false;
        }
        i += 1;
    }
    if !field.is_empty() || !rec.is_empty() {
        rec.push(field);
        recs.push(rec);
    }
    recs
}

// ---------------------------------------------------------------------------------------------
// header block + table header

#[derive(Default)]
struct Block {
    style: String,
    description: String,
    brand: String,
    fit: String,
    season: String,
    base: String,
    range: String,
}

fn block_key(label: &str) -> Option<&'static str> {
    Some(match keyify(label).as_str() {
        "STYLE" | "STYLE NO" | "STYLE NUMBER" | "STYLE CODE" | "STYLE REF" | "STYLE NAME" => "style",
        "STYLE DESCRIPTION" | "DESCRIPTION" | "DESC" | "PRODUCT DESCRIPTION" => "description",
        "BRAND" => "brand",
        "SEASON" => "season",
        "BASE PATTERN FIT" | "FIT" | "BASE PATTERN" | "FIT TYPE" => "fit",
        "SIZE RANGE" | "SIZES" | "RANGE" => "range",
        "BASE SIZE" | "SAMPLE SIZE" | "BASE SAMPLE SIZE" | "SAMPLE SIZE BASE" => "base",
        _ => return None,
    })
}

fn is_label(c: &str) -> bool {
    block_key(c).is_some() || c.trim_end().ends_with(':')
}

fn clean_scalar(s: &str) -> String {
    let t = s.trim();
    if let Some(p) = t.strip_suffix(".0") {
        if !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit()) {
            return p.to_string();
        }
    }
    t.to_string()
}

fn scan_block(rows: &[Vec<String>]) -> Block {
    let mut b = Block::default();
    fn put(b: &mut Block, k: &str, v: &str) {
        let v = clean_scalar(v);
        if v.is_empty() {
            return;
        }
        let slot = match k {
            "style" => &mut b.style,
            "description" => &mut b.description,
            "brand" => &mut b.brand,
            "fit" => &mut b.fit,
            "season" => &mut b.season,
            "base" => &mut b.base,
            "range" => &mut b.range,
            _ => return,
        };
        if slot.is_empty() {
            *slot = v;
        }
    }
    for row in rows {
        let mut i = 0;
        while i < row.len() {
            let c = &row[i];
            if c.is_empty() {
                i += 1;
                continue;
            }
            if let Some(k) = block_key(c) {
                let mut j = i + 1;
                while j < row.len() && row[j].is_empty() {
                    j += 1;
                }
                if j < row.len() && !is_label(&row[j]) {
                    put(&mut b, k, &row[j]);
                    i = j + 1;
                    continue;
                }
            } else if let Some(pos) = c.find(':') {
                // single-cell "STYLE# : 1086464"; ':' is ASCII so slicing is on a char boundary
                if let Some(k) = block_key(&c[..pos]) {
                    put(&mut b, k, &c[pos + 1..]);
                }
            }
            i += 1;
        }
    }
    b
}

#[derive(Debug)]
struct Header {
    pom_col: Option<usize>,
    name_col: usize,
    first_size: usize,
    sizes: Vec<(usize, String)>,
    tol_plus: Option<usize>,
    tol_minus: Option<usize>,
}

fn is_pom_header(c: &str) -> bool {
    matches!(
        keyify(c).as_str(),
        "POM" | "CODES" | "POM CODES" | "POM CODE" | "POM NO" | "POM ID" | "POM NUMBER" | "CODE" | "POINT OF MEASURE" | "POINT OF MEASUREMENT" | "POM NR"
    )
}

fn is_size_label(c: &str) -> bool {
    let k = keyify(c);
    if k.is_empty() || k.len() > 8 {
        return false;
    }
    if matches!(k.as_str(), "XXXS" | "XXS" | "XS" | "S" | "M" | "L" | "XL" | "XXL" | "XXXL" | "2XL" | "3XL" | "4XL" | "5XL" | "OS" | "1X" | "2X" | "3X") {
        return true;
    }
    k.len() <= 2 && k.bytes().all(|b| b.is_ascii_digit()) && k.parse::<u32>().map(|v| v <= 70).unwrap_or(false)
}

fn analyse_header(row: &[String]) -> Option<Header> {
    let pom_col = row.iter().position(|c| is_pom_header(c));
    let start = pom_col.map(|p| p + 1).unwrap_or(0);
    let mut sizes: Vec<(usize, String)> = Vec::new();
    let mut tols: Vec<(usize, String)> = Vec::new();
    for (i, c) in row.iter().enumerate().skip(start) {
        if c.is_empty() {
            continue;
        }
        if fold_upper(c).contains("TOL") {
            tols.push((i, fold_upper(c)));
        } else if is_size_label(c) {
            sizes.push((i, c.trim().to_uppercase()));
        }
    }
    if sizes.is_empty() {
        return None;
    }
    if pom_col.is_none() {
        let alpha = sizes.iter().filter(|(_, s)| !s.bytes().all(|b| b.is_ascii_digit())).count();
        if alpha < 2 {
            return None;
        }
    }
    let first_size = sizes[0].0;
    let name_col = (start..first_size)
        .find(|&i| !row[i].is_empty() && !fold_upper(&row[i]).contains("TOL"))
        .unwrap_or(if pom_col.is_some() { start } else { 0 });
    let (mut tp, mut tm) = (None, None);
    match tols.len() {
        0 => {}
        1 => {
            tp = Some(tols[0].0);
            tm = Some(tols[0].0);
        }
        _ => {
            for (i, t) in &tols {
                let (plus, minus) = (t.contains('+') || t.contains("PLUS"), t.contains('-') || t.contains("MINUS"));
                if plus && !minus && tp.is_none() {
                    tp = Some(*i);
                } else if minus && !plus && tm.is_none() {
                    tm = Some(*i);
                }
            }
            if tp.is_none() {
                tp = Some(tols[0].0);
            }
            if tm.is_none() {
                tm = tols.iter().map(|t| t.0).find(|i| Some(*i) != tp).or(tp);
            }
        }
    }
    Some(Header { pom_col, name_col, first_size, sizes, tol_plus: tp, tol_minus: tm })
}

fn snake(s: &str) -> String {
    let t = s.replace('½', " half ").replace("1/2", " half ");
    let k = keyify(&t);
    k.to_lowercase().replace(' ', "_")
}

/// Default base size: `M` if present, otherwise the (lower) middle size.
pub fn default_base_size(sizes: &[String]) -> String {
    if sizes.is_empty() {
        return String::new();
    }
    if let Some(m) = sizes.iter().find(|s| s.eq_ignore_ascii_case("M")) {
        return m.clone();
    }
    sizes[(sizes.len() - 1) / 2].clone()
}

/// Parse a spec sheet from TSV / CSV / pasted Excel text.
pub fn parse_spec_text(text: &str) -> Result<SpecSheet, String> {
    if text.len() > MAX_INPUT {
        return Err("input too large for a spec sheet".into());
    }
    if text.trim().is_empty() {
        return Err("no spec data".into());
    }
    let delim = detect_delimiter(text);
    let recs: Vec<Vec<String>> = parse_records(text, delim)
        .into_iter()
        .map(|r| r.iter().map(|c| clean_cell(c)).collect())
        .collect();
    let (hi, hdr) = recs
        .iter()
        .enumerate()
        .find_map(|(i, r)| analyse_header(r).map(|h| (i, h)))
        .ok_or_else(|| "could not find the table header row (expected 'POM | MEASUREMENT POINTS | XS | S | M ...')".to_string())?;
    if hdr.sizes.len() > MAX_SIZES {
        return Err("too many size columns".into());
    }
    let block = scan_block(&recs[..hi]);
    let mut warnings: Vec<String> = Vec::new();
    let sizes: Vec<String> = hdr.sizes.iter().map(|(_, s)| s.clone()).collect();
    for (i, s) in sizes.iter().enumerate() {
        if sizes[..i].contains(s) {
            warnings.push(format!("duplicate size column '{}'", s));
        }
    }
    let get = |row: &Vec<String>, i: usize| -> String { row.get(i).cloned().unwrap_or_default() };
    let mut rows: Vec<PomRow> = Vec::new();
    for (off, row) in recs[hi + 1..].iter().enumerate() {
        let line = hi + 2 + off;
        if row.iter().all(|c| c.is_empty()) {
            continue;
        }
        if analyse_header(row).map(|h| h.pom_col.is_some()).unwrap_or(false) {
            warnings.push(format!("line {}: second table header found; rows after it were ignored", line));
            break;
        }
        if rows.len() >= MAX_ROWS {
            warnings.push("row limit reached; remaining rows ignored".into());
            break;
        }
        let mut code = hdr.pom_col.map(|p| clean_scalar(&get(row, p))).unwrap_or_default();
        let mut name = get(row, hdr.name_col);
        let mut local = (hdr.name_col + 1..hdr.first_size).map(|i| get(row, i)).find(|c| !c.is_empty()).unwrap_or_default();
        if name.is_empty() && !local.is_empty() {
            name = std::mem::take(&mut local);
        }
        let mut values = Vec::with_capacity(sizes.len());
        for (ci, label) in &hdr.sizes {
            let cell = get(row, *ci);
            if is_blank_placeholder(&cell) {
                values.push(f64::NAN);
            } else if let Some(v) = parse_number(&cell) {
                values.push(round2(v));
            } else {
                warnings.push(format!("line {}: size {}: '{}' is not a number", line, label, cell));
                values.push(f64::NAN);
            }
        }
        if values.iter().all(|v| v.is_nan()) {
            if !code.is_empty() && !name.is_empty() {
                warnings.push(format!("line {}: POM {} has no values; skipped", line, code));
            }
            continue;
        }
        if code.is_empty() {
            if name.is_empty() {
                continue;
            }
            code = snake(&name);
            warnings.push(format!("line {}: row '{}' has no POM code; using '{}'", line, name, code));
        }
        let read_tol = |col: Option<usize>, warnings: &mut Vec<String>| -> f64 {
            match col {
                None => f64::NAN,
                Some(c) => {
                    let cell = get(row, c);
                    if is_blank_placeholder(&cell) {
                        f64::NAN
                    } else if let Some(v) = parse_number(&cell) {
                        round2(v.abs())
                    } else {
                        warnings.push(format!("line {}: tolerance '{}' is not a number", line, cell));
                        f64::NAN
                    }
                }
            }
        };
        let tol_plus = read_tol(hdr.tol_plus, &mut warnings);
        let tol_minus = if hdr.tol_minus == hdr.tol_plus { tol_plus } else { read_tol(hdr.tol_minus, &mut warnings) };
        if rows.iter().any(|r: &PomRow| r.code == code) {
            warnings.push(format!("line {}: duplicate POM code {}", line, code));
        }
        rows.push(PomRow { code, name, name_local: local, values, tol_plus, tol_minus, map_to: None });
    }
    if rows.is_empty() {
        return Err("no measurement rows found under the table header".into());
    }
    // "SIZE / RANGE : L" on a chart whose columns are S..3XL names the sample (base) size
    let block_base = if block.base.trim().is_empty() { block.range.trim().to_string() } else { block.base.trim().to_string() };
    let block = Block { base: block_base, ..block };
    let base_size = if sizes.iter().any(|s| s.eq_ignore_ascii_case(block.base.trim())) && !block.base.is_empty() {
        sizes.iter().find(|s| s.eq_ignore_ascii_case(block.base.trim())).cloned().unwrap_or_default()
    } else {
        default_base_size(&sizes)
    };
    Ok(SpecSheet {
        style: block.style,
        description: block.description,
        brand: block.brand,
        fit: block.fit,
        season: block.season,
        sizes,
        base_size,
        rows,
        warnings,
    })
}

// ---------------------------------------------------------------------------------------------
// canonical POM mapping

fn has_any(n: &str, alts: &[&str]) -> bool {
    alts.iter().any(|a| n.contains(a))
}

/// Pant drafter fields a spec row can be mapped to (key, label).
pub const PANT_TARGETS: &[(&str, &str)] = &[
    ("half_waist_relaxed", "1/2 waist (relaxed)"), ("half_waist_stretched", "1/2 waist (stretched)"), ("half_seat", "1/2 seat"),
    ("hip_pos_side_seam", "hip position at side seam"), ("hip_pos_center_front", "hip position at centre front"),
    ("half_thigh", "1/2 thigh"), ("front_rise", "front rise"), ("back_rise", "back rise"), ("half_knee", "1/2 knee"),
    ("half_leg_opening", "1/2 leg opening"), ("hem_height", "hem height"), ("inseam", "inseam"), ("waistband_width", "waistband width"),
    ("pocket_opening_waist", "pocket opening at waist"), ("pocket_opening_side", "pocket opening down side"),
    ("pocket_bag_depth", "pocket bag depth"), ("drawcord_half", "1/2 drawcord length"),
];

/// Drafter fields a spec row can drive for `garment` ("pant" or "shirt"): (key, label).
pub fn map_targets(garment: &str) -> Vec<(&'static str, String)> {
    if garment.eq_ignore_ascii_case("shirt") {
        crate::garments::ShirtSpec::field_names().into_iter().map(|k| (k, k.replace('_', " "))).collect()
    } else {
        PANT_TARGETS.iter().map(|(k, l)| (*k, l.to_string())).collect()
    }
}

/// Resolve a user-chosen key to the matching static drafter key (None if it is not a valid target).
pub fn map_target_static(key: &str) -> Option<&'static str> {
    PANT_TARGETS.iter().map(|(k, _)| *k).find(|k| *k == key)
        .or_else(|| crate::garments::ShirtSpec::field_names().into_iter().find(|k| *k == key))
}

/// Map a POM code and/or name to a canonical key (`None` if unknown). Codes win over names.
/// Bottoms are mapped by Colin's codes; tops (no code table available) by name keywords.
pub fn canonical_pom(code: &str, name: &str) -> Option<&'static str> {
    let c: String = fold_upper(code).chars().filter(|c| c.is_alphanumeric()).collect();
    let by_code = match c.as_str() {
        "20125" => Some("half_waist_relaxed"),
        "20245" => Some("half_waist_stretched"),
        "20305" => Some("half_seat"),
        "20305A" => Some("hip_pos_side_seam"),
        "20305B" => Some("hip_pos_center_front"),
        "20865" => Some("half_thigh"),
        "21505" => Some("front_rise"),
        "21545" => Some("back_rise"),
        "20905" => Some("half_knee"),
        "21125" => Some("half_leg_opening"),
        "30210" => Some("hem_height"),
        "21885" => Some("inseam"),
        "20265" => Some("waistband_width"),
        "22145" => Some("pocket_opening_waist"),
        "22165" => Some("pocket_opening_side"),
        "22565" => Some("pocket_bag_depth"),
        "30845" => Some("drawcord_half"),
        _ => None,
    };
    by_code.or_else(|| canon_by_name(name))
}

fn canon_by_name(name: &str) -> Option<&'static str> {
    let pre = fold_upper(name).replace("1/2", " HALF ").replace('½', " HALF ");
    let n = format!(" {} ", keyify(&pre));
    if n.trim().is_empty() {
        return None;
    }
    let h = |a: &[&str]| has_any(&n, a);
    let pocket = h(&[" POCKET ", " PKT ", " CEP "]);
    let sleeve = h(&[" SLEEVE ", " SLV ", " KOL "]);
    // pockets first: they reuse words like length/width/side
    if pocket {
        if h(&[" BAG ", " TORBA"]) && h(&[" DEPTH ", " LENGTH ", " DERINLIGI "]) {
            return Some("pocket_bag_depth");
        }
        if h(&[" WB ", " W B ", " WAISTBAND ", " KEMER "]) {
            return Some("pocket_opening_waist");
        }
        if h(&[" SIDE SEAM ", " OUTSEAM ", " OUT SEAM ", " DWN ", " DOWN ", " SS ", " YAN "]) {
            return Some("pocket_opening_side");
        }
        if h(&[" WIDTH "]) {
            return Some("pocket_width");
        }
        if h(&[" LENGTH ", " DEPTH ", " HEIGHT ", " DROP "]) {
            return Some("pocket_length");
        }
        return None;
    }
    // shirt-chart rows that must not fall into the generic shoulder / sleeve / waist rules below
    if h(&[" FORWARD SHOULDER "]) || h(&[" TIE GAP ", " BUTTON ", " BUTTONHOLE "]) || h(&[" ELBOW "]) {
        return None;
    }
    if sleeve && h(&[" PLACKET "]) {
        return Some(if h(&[" WIDTH "]) { "sleeve_placket_width" } else { "sleeve_placket" });
    }
    if sleeve && h(&[" CAP "]) && h(&[" HEIGHT ", " DEPTH "]) {
        return Some("sleeve_cap_height");
    }
    if h(&[" CURVED CORNER ", " CURVE CORNER "]) {
        return Some("hem_curve_height");
    }
    if h(&[" MID ARMHOLE ", " MID ARM HOLE "]) {
        if h(&[" BACK ", " ARKA "]) { return Some("across_back"); }
        if h(&[" FRONT ", " FRT ", " ON "]) { return Some("across_chest"); }
        return None;
    }
    if h(&[" COLLAR "]) && h(&[" OUTSIDE EDGE ", " OUTER EDGE "]) {
        return Some("collar_outer_edge");
    }
    if h(&[" CUFF "]) && h(&[" EDGE TO EDGE ", " SEAM EDGE "]) {
        return Some("cuff_opening_full");
    }
    if sleeve && h(&[" FM SHLDR ", " FROM SHOULDER ", " FM SHOULDER ", " FROM SHLDR "]) {
        return Some("sleeve_length");
    }
    if h(&[" WAIST "]) && h(&[" POSITION "]) && !h(&[" HIP ", " SEAT "]) {
        return Some("waist_position");
    }
    if h(&[" FRONT ", " FRT "]) && h(&[" LENGTH "]) && h(&[" HPS ", " NECK ", " SHOULDER "]) && !sleeve {
        return Some("body_length");
    }
    if h(&[" BACK "]) && !h(&[" FRONT ", " FRT "]) && h(&[" LENGTH "]) && h(&[" HPS ", " NECK ", " SHOULDER "]) && !sleeve {
        return Some("back_length");
    }
    if h(&[" DRAWCORD ", " DRAWSTRING ", " DRAW CORD ", " KORDON "]) {
        return Some("drawcord_half");
    }
    if h(&[" WAISTBAND ", " WAIST BAND ", " WB ", " KEMER "]) && h(&[" WIDTH ", " HEIGHT ", " DEPTH ", " ENI "]) {
        return Some("waistband_width");
    }
    if h(&[" HIP ", " SEAT ", " BASEN "]) && h(&[" POSITION "]) {
        if h(&[" CENTER ", " CENTRE ", " CF ", " FRONT ", " ON ORTA"]) {
            return Some("hip_pos_center_front");
        }
        if h(&[" SIDE ", " YAN "]) {
            return Some("hip_pos_side_seam");
        }
        return None;
    }
    if h(&[" HEM ", " BOTTOM HEM ", " PACA KIVIRMA "]) && h(&[" HEIGHT ", " DEPTH ", " KIVIRMA "]) && !sleeve {
        return Some("hem_height");
    }
    if h(&[" INSEAM ", " INSIDE LEG ", " ICBOY "]) {
        return Some("inseam");
    }
    if h(&[" OUTSEAM ", " OUT SEAM ", " DISBOY "]) {
        return Some("outseam");
    }
    if h(&[" RISE ", " AG "]) {
        if h(&[" FRONT ", " FRT ", " ON AG "]) {
            return Some("front_rise");
        }
        if h(&[" BACK ", " BCK ", " ARKA "]) {
            return Some("back_rise");
        }
        return Some("rise");
    }
    if h(&[" LEG OPENING ", " LEG OPEN ", " PACA "]) && !h(&[" KIVIRMA "]) {
        return Some("half_leg_opening");
    }
    if h(&[" KNEE ", " DIZ "]) {
        return Some("half_knee");
    }
    if h(&[" THIGH ", " BALDIR "]) {
        return Some("half_thigh");
    }
    if h(&[" HIP ", " SEAT ", " BASEN "]) {
        return Some("half_seat");
    }
    if h(&[" WAIST ", " BEL "]) {
        if h(&[" STRETCH ", " STRETCHED ", " TEXT D ", " GERGIN ", " EXTENDED ", " EXT D ", " EXTENDED "]) {
            return Some("half_waist_stretched");
        }
        if h(&[" TOP EDGE ", " RELAXED ", " RLX ", " DURGUN ", " UST KENAR "]) {
            return Some("half_waist_relaxed");
        }
        return Some("half_waist");
    }
    // tops
    if h(&[" SHOULDER ", " OMUZ "]) {
        if h(&[" SLOPE ", " DROP "]) {
            return Some("shoulder_drop");
        }
        if h(&[" STRAP "]) {
            return Some("strap_width");
        }
        return Some("across_shoulder");
    }
    if h(&[" CHEST ", " BUST ", " GOGUS "]) {
        if h(&[" ACROSS "]) && !h(&[" HALF "]) {
            return Some("across_chest");
        }
        return Some("half_chest");
    }
    if h(&[" ACROSS BACK ", " BACK WIDTH "]) {
        return Some("across_back");
    }
    if h(&[" ARMHOLE ", " ARM HOLE ", " AH ", " ARMSCYE ", " KOL OYUGU "]) {
        return Some("armhole");
    }
    if h(&[" BICEP ", " BICEPS ", " MUSCLE ", " UPPER ARM "]) {
        return Some("half_bicep");
    }
    if h(&[" CUFF "]) && h(&[" HEIGHT ", " WIDTH ", " DEPTH ", " BAND "]) {
        return Some("cuff_height");
    }
    if sleeve && h(&[" LENGTH ", " LEN ", " BOYU "]) {
        return Some("sleeve_length");
    }
    if h(&[" CUFF ", " KOL AGZI "]) || (sleeve && h(&[" OPENING ", " OPEN "])) {
        return Some("half_sleeve_opening");
    }
    if h(&[" COLLAR ", " YAKA "]) {
        if h(&[" STAND ", " BAND ", " MOON "]) && !h(&[" LENGTH "]) {
            return Some("collar_stand_height");
        }
        if h(&[" POINT "]) {
            return Some("collar_point_length");
        }
        if h(&[" SPREAD "]) {
            return Some("collar_spread");
        }
        if h(&[" HEIGHT ", " DEPTH ", " WIDTH ", " AT CB "]) {
            return Some("collar_height");
        }
        return Some("collar_length");
    }
    if h(&[" NECK "]) {
        if h(&[" CIRC ", " CIRCUMFERENCE ", " SIZE "]) {
            return Some("neck_circumference");
        }
        if h(&[" DROP ", " DEPTH "]) {
            return Some(if h(&[" BACK "]) { "back_neck_drop" } else { "neck_drop" });
        }
        if h(&[" WIDTH ", " OPENING ", " OPEN "]) {
            return Some("neck_width");
        }
        return None;
    }
    if h(&[" PLACKET "]) {
        if h(&[" WIDTH "]) {
            return Some("placket_width");
        }
        if h(&[" LENGTH "]) {
            return Some("placket_length");
        }
        return None;
    }
    if h(&[" YOKE "]) && h(&[" DEPTH ", " HEIGHT ", " DROP ", " WIDTH "]) {
        return Some("yoke_depth");
    }
    if h(&[" LENGTH "]) && !h(&[" SLEEVE ", " SLV ", " PLACKET ", " COLLAR "]) {
        if h(&[" FRONT ", " FRT ", " CF "]) && !h(&[" BACK ", " CB ", " HPS "]) {
            return Some("front_length");
        }
        if h(&[" BODY ", " HPS ", " BACK ", " CB ", " SHIRT ", " TOTAL ", " CENTER BACK ", " SHOULDER TO HEM "]) {
            return Some("body_length");
        }
    }
    if h(&[" HEM ", " SWEEP ", " BOTTOM OPENING ", " BOTTOM WIDTH ", " ETEK "]) {
        return Some("hem_sweep");
    }
    None
}

/// Canonical keys that are recorded as half-garment widths on spec sheets.
pub fn is_half_measure(canon: &str) -> bool {
    canon.starts_with("half_") || canon == "drawcord_half"
}

fn plausible_range(canon: &str) -> Option<(f64, f64)> {
    Some(match canon {
        "half_waist_relaxed" => (15.0, 90.0),
        "half_waist_stretched" => (20.0, 120.0),
        "half_waist" => (15.0, 100.0),
        "half_seat" => (25.0, 100.0),
        "half_thigh" => (15.0, 60.0),
        "front_rise" => (15.0, 50.0),
        "back_rise" => (20.0, 60.0),
        "half_knee" => (10.0, 45.0),
        "half_leg_opening" => (8.0, 50.0),
        "hem_height" => (0.0, 12.0),
        "inseam" => (10.0, 100.0),
        "waistband_width" => (1.0, 15.0),
        "half_chest" => (30.0, 90.0),
        "across_shoulder" => (25.0, 70.0),
        "sleeve_length" => (3.0, 90.0),
        "body_length" => (40.0, 120.0),
        _ => return None,
    })
}

// ---------------------------------------------------------------------------------------------
// SpecSheet API

impl SpecSheet {
    pub fn size_index(&self, size: &str) -> Option<usize> {
        let s = size.trim();
        self.sizes.iter().position(|x| x.eq_ignore_ascii_case(s))
    }

    pub fn base_index(&self) -> usize {
        self.size_index(&self.base_size).unwrap_or(0)
    }

    /// Canonical key for a row (code first, then English name, then local name).
    pub fn canonical(&self, row: &PomRow) -> Option<&'static str> {
        if let Some(k) = row.map_to { return if k.is_empty() { None } else { Some(k) }; } // "" = explicitly unused
        // the local-language description is only a fallback for rows that have no English name at all
        canonical_pom(&row.code, &row.name).or_else(|| if row.name.trim().is_empty() { canonical_pom("", &row.name_local) } else { None })
    }

    /// Values for `size`, keyed by POM code (blank cells omitted). Unknown size -> empty.
    pub fn size_map(&self, size: &str) -> BTreeMap<String, f64> {
        let mut m = BTreeMap::new();
        if let Some(i) = self.size_index(size) {
            for r in &self.rows {
                if let Some(v) = r.value(i) {
                    m.insert(r.code.clone(), v);
                }
            }
        }
        m
    }

    /// Values for `size`, keyed by normalized snake_case POM name (`1/2`/`½` -> `half`).
    /// Colliding names get `_2`, `_3` ... suffixes.
    pub fn name_map(&self, size: &str) -> BTreeMap<String, f64> {
        let mut m = BTreeMap::new();
        if let Some(i) = self.size_index(size) {
            for r in &self.rows {
                if let Some(v) = r.value(i) {
                    let base = snake(&if r.name.is_empty() { r.code.clone() } else { r.name.clone() });
                    let mut key = base.clone();
                    let mut k = 2;
                    while m.contains_key(&key) {
                        key = format!("{}_{}", base, k);
                        k += 1;
                    }
                    m.insert(key, v);
                }
            }
        }
        m
    }

    /// Values for `size`, keyed by canonical key (unmapped rows omitted; first row wins).
    pub fn canonical_map(&self, size: &str) -> BTreeMap<String, f64> {
        let mut m = BTreeMap::new();
        if let Some(i) = self.size_index(size) {
            for r in &self.rows {
                if let (Some(k), Some(v)) = (self.canonical(r), r.value(i)) {
                    m.entry(k.to_string()).or_insert(v);
                }
            }
        }
        m
    }

    /// Per POM code: differences between consecutive sizes (len = sizes-1; NaN where a cell is blank).
    pub fn grade_increments(&self) -> Vec<(String, Vec<f64>)> {
        self.rows
            .iter()
            .map(|r| {
                let d = r.values.windows(2).map(|w| round2(w[1] - w[0])).collect();
                (r.code.clone(), d)
            })
            .collect()
    }

    /// Linear extrapolation keyed by POM code: start at the value of `steps_from`, move `steps`
    /// sizes up (>0) or down (<0). Steps inside the existing range use the real increments; steps
    /// beyond use the last (up) or first (down) increment. `new_size_label` is informational;
    /// use [`SpecSheet::add_extrapolated_size`] to append the column.
    pub fn extrapolate(&self, new_size_label: &str, steps_from: &str, steps: i32) -> BTreeMap<String, f64> {
        let _ = new_size_label;
        let mut m = BTreeMap::new();
        let from = match self.size_index(steps_from) {
            Some(i) => i,
            None => return m,
        };
        for r in &self.rows {
            let v = walk(&r.values, from, steps.clamp(-100, 100));
            if v.is_finite() {
                m.insert(r.code.clone(), round2(v));
            }
        }
        m
    }

    /// Append a new size column (e.g. `3XL`) extrapolated as in [`SpecSheet::extrapolate`].
    pub fn add_extrapolated_size(&mut self, label: &str, steps_from: &str, steps: i32) -> Result<(), String> {
        let label = label.trim().to_uppercase();
        if label.is_empty() {
            return Err("empty size label".into());
        }
        if self.size_index(&label).is_some() {
            return Err(format!("size {} already exists", label));
        }
        let from = self.size_index(steps_from).ok_or_else(|| format!("unknown size '{}'", steps_from))?;
        let st = steps.clamp(-100, 100);
        for r in &mut self.rows {
            let v = walk(&r.values, from, st);
            r.values.push(if v.is_finite() { round2(v) } else { f64::NAN });
        }
        self.sizes.push(label);
        Ok(())
    }

    fn canon_value(&self, key: &str, si: usize) -> Option<f64> {
        self.rows.iter().find(|r| self.canonical(r) == Some(key)).and_then(|r| r.value(si))
    }

    /// Sanity warnings (non-monotonic grading, impossible values, missing tolerance, stretch<relaxed ...).
    pub fn check(&self) -> Vec<String> {
        let mut w = Vec::new();
        if self.rows.is_empty() {
            w.push("spec sheet has no measurement rows".into());
        }
        if self.sizes.is_empty() {
            w.push("spec sheet has no sizes".into());
        } else if self.size_index(&self.base_size).is_none() {
            w.push(format!("base size '{}' is not one of the sizes", self.base_size));
        }
        for r in &self.rows {
            let tag = format!("POM {} ({})", r.code, r.name);
            if r.values.len() != self.sizes.len() {
                w.push(format!("{}: {} values for {} sizes", tag, r.values.len(), self.sizes.len()));
            }
            if !r.has_tolerance() {
                w.push(format!("{}: tolerance missing", tag));
            } else if r.tol_plus < 0.0 || r.tol_minus < 0.0 {
                w.push(format!("{}: negative tolerance", tag));
            }
            let blanks = r.values.iter().filter(|v| !v.is_finite()).count();
            if blanks > 0 && blanks < r.values.len() {
                w.push(format!("{}: {} size(s) have no value", tag, blanks));
            }
            let canon = self.canonical(r);
            let range = canon.and_then(plausible_range);
            for (i, v) in r.values.iter().enumerate() {
                if !v.is_finite() {
                    continue;
                }
                let sz = self.sizes.get(i).map(|s| s.as_str()).unwrap_or("?");
                if *v < 0.0 || *v > 250.0 {
                    w.push(format!("{}: size {} value {} cm is impossible", tag, sz, v));
                } else if *v == 0.0 && canon != Some("hem_height") {
                    w.push(format!("{}: size {} value is 0", tag, sz));
                } else if let Some((lo, hi)) = range {
                    if *v < lo || *v > hi {
                        let inch = *v * 2.54;
                        let hint = if inch >= lo && inch <= hi { " (inches?)" } else { "" };
                        w.push(format!("{}: size {} value {} cm outside plausible {}..{} cm{}", tag, sz, v, lo, hi, hint));
                    }
                }
                if r.has_tolerance() && *v > 0.0 && (r.tol_plus > 0.2 * v || r.tol_minus > 0.2 * v) {
                    w.push(format!("{}: size {} tolerance {}/{} is large relative to value {}", tag, sz, r.tol_plus, r.tol_minus, v));
                    break;
                }
            }
            let inc: Vec<f64> = r.values.windows(2).map(|p| p[1] - p[0]).filter(|d| d.is_finite()).collect();
            let up = inc.iter().any(|d| *d > 0.005);
            let down = inc.iter().any(|d| *d < -0.005);
            if up && down {
                w.push(format!("{}: grading is not monotonic across sizes ({:?})", tag, r.values.iter().map(|v| round2(*v)).collect::<Vec<_>>()));
            } else if down {
                w.push(format!("{}: value decreases as size increases", tag));
            }
            for (i, p) in r.values.windows(2).enumerate() {
                let d = p[1] - p[0];
                let lo = p[0].abs().min(p[1].abs());
                if d.is_finite() && lo > 0.0 && d.abs() > 0.2 * lo {
                    w.push(format!("{}: suspicious jump {} -> {} between {} and {}", tag, p[0], p[1], self.sizes.get(i).map(|s| s.as_str()).unwrap_or("?"), self.sizes.get(i + 1).map(|s| s.as_str()).unwrap_or("?")));
                    break;
                }
            }
        }
        for (si, sz) in self.sizes.iter().enumerate() {
            if let (Some(rx), Some(st)) = (self.canon_value("half_waist_relaxed", si), self.canon_value("half_waist_stretched", si)) {
                if st < rx {
                    w.push(format!("size {}: waist stretched ({}) is smaller than waist relaxed ({})", sz, st, rx));
                }
            }
            if let (Some(wa), Some(se)) = (self.canon_value("half_waist_relaxed", si), self.canon_value("half_seat", si)) {
                if se < wa {
                    w.push(format!("size {}: seat ({}) is smaller than relaxed waist ({})", sz, se, wa));
                }
            }
            if let (Some(f), Some(b)) = (self.canon_value("front_rise", si), self.canon_value("back_rise", si)) {
                if b < f {
                    w.push(format!("size {}: back rise ({}) is shorter than front rise ({})", sz, b, f));
                }
            }
        }
        w
    }

    pub fn to_json(&self) -> Json {
        let rows: Vec<Json> = self
            .rows
            .iter()
            .map(|r| {
                Json::obj()
                    .set("code", Json::str(&r.code))
                    .set("name", Json::str(&r.name))
                    .set("name_local", Json::str(&r.name_local))
                    .set("canonical", self.canonical(r).map(Json::str).unwrap_or(Json::Null))
                    .set("map_to", r.map_to.map(Json::str).unwrap_or(Json::Null))
                    .set("values", Json::nums(&r.values)) // NaN -> null
                    .set("tol_plus", Json::num(r.tol_plus))
                    .set("tol_minus", Json::num(r.tol_minus))
            })
            .collect();
        Json::obj()
            .set("style", Json::str(&self.style))
            .set("description", Json::str(&self.description))
            .set("brand", Json::str(&self.brand))
            .set("fit", Json::str(&self.fit))
            .set("season", Json::str(&self.season))
            .set("sizes", Json::Arr(self.sizes.iter().map(|s| Json::str(s)).collect()))
            .set("base_size", Json::str(&self.base_size))
            .set("rows", Json::Arr(rows))
            .set("warnings", Json::Arr(self.warnings.iter().map(|s| Json::str(s)).collect()))
    }

    pub fn from_json(j: &Json) -> Result<SpecSheet, String> {
        let s = |k: &str| j.get(k).and_then(|v| v.as_str()).unwrap_or("").to_string();
        let sizes: Vec<String> = j
            .get("sizes")
            .and_then(|v| v.as_arr())
            .ok_or("spec: 'sizes' array required")?
            .iter()
            .map(|v| v.as_str().map(|x| x.to_string()).ok_or("spec: sizes must be strings"))
            .collect::<Result<_, _>>()?;
        if sizes.is_empty() {
            return Err("spec: 'sizes' must not be empty".into());
        }
        let num = |v: Option<&Json>| v.and_then(|x| x.as_f64()).unwrap_or(f64::NAN);
        let mut rows = Vec::new();
        for (i, r) in j.get("rows").and_then(|v| v.as_arr()).ok_or("spec: 'rows' array required")?.iter().enumerate() {
            let rs = |k: &str| r.get(k).and_then(|v| v.as_str()).unwrap_or("").to_string();
            let code = rs("code");
            if code.is_empty() {
                return Err(format!("spec: row {} has no code", i));
            }
            let values: Vec<f64> = r
                .get("values")
                .and_then(|v| v.as_arr())
                .ok_or_else(|| format!("spec: row {} needs 'values'", i))?
                .iter()
                .map(|v| v.as_f64().unwrap_or(f64::NAN))
                .collect();
            if values.len() != sizes.len() {
                return Err(format!("spec: row {} has {} values for {} sizes", i, values.len(), sizes.len()));
            }
            let map_to = r.get("map_to").and_then(|v| v.as_str()).and_then(|k| if k.is_empty() { Some("") } else { map_target_static(k) });
            rows.push(PomRow { code, name: rs("name"), name_local: rs("name_local"), values, tol_plus: num(r.get("tol_plus")), tol_minus: num(r.get("tol_minus")), map_to });
        }
        let mut base_size = s("base_size");
        if !sizes.iter().any(|x| x.eq_ignore_ascii_case(&base_size)) {
            base_size = default_base_size(&sizes);
        }
        let warnings = j.get("warnings").and_then(|v| v.as_arr()).map(|a| a.iter().filter_map(|v| v.as_str().map(|x| x.to_string())).collect()).unwrap_or_default();
        Ok(SpecSheet { style: s("style"), description: s("description"), brand: s("brand"), fit: s("fit"), season: s("season"), sizes, base_size, rows, warnings })
    }

    /// Grade table in the shape the UI's grading view consumes (see `api.rs` "grade"):
    /// `{"sizes":[{"label","step","measurements":{code:value},"table":[{"piece","deltas":[[d,0]]}]}]}`.
    /// `step` is the index offset from the base size, `piece` is the POM name (code in `code`),
    /// and each delta is `[value - base_value, 0]` (a 1-D "node"). Extra fields: `base`, `tolerances`.
    pub fn spec_to_grade_table(&self) -> Json {
        let bi = self.base_index();
        let sizes: Vec<Json> = self
            .sizes
            .iter()
            .enumerate()
            .map(|(si, label)| {
                let mut meas: Vec<(String, Json)> = Vec::new();
                let mut table = Vec::new();
                for r in &self.rows {
                    let v = r.value(si);
                    if let Some(v) = v {
                        meas.push((r.code.clone(), Json::num(v)));
                    }
                    let d = match (v, r.value(bi)) {
                        (Some(v), Some(b)) => round2(v - b),
                        _ => 0.0,
                    };
                    table.push(
                        Json::obj()
                            .set("piece", Json::str(if r.name.is_empty() { &r.code } else { &r.name }))
                            .set("code", Json::str(&r.code))
                            .set("deltas", Json::Arr(vec![Json::nums(&[d, 0.0])])),
                    );
                }
                Json::obj()
                    .set("label", Json::str(label))
                    .set("step", Json::num(si as f64 - bi as f64))
                    .set("measurements", Json::Obj(meas))
                    .set("table", Json::Arr(table))
            })
            .collect();
        let tol: Vec<(String, Json)> = self
            .rows
            .iter()
            .map(|r| (r.code.clone(), Json::obj().set("plus", Json::num(r.tol_plus)).set("minus", Json::num(r.tol_minus))))
            .collect();
        Json::obj()
            .set("spec", Json::Bool(true))
            .set("base", Json::str(&self.base_size))
            .set("sizes", Json::Arr(sizes))
            .set("tolerances", Json::Obj(tol))
    }
}

fn walk(vals: &[f64], from: usize, steps: i32) -> f64 {
    let n = vals.len();
    if from >= n || !vals[from].is_finite() {
        return f64::NAN;
    }
    let (inc_hi, inc_lo) = if n >= 2 { (vals[n - 1] - vals[n - 2], vals[1] - vals[0]) } else { (0.0, 0.0) };
    let mut idx = from as i64;
    let mut cur = vals[from];
    for _ in 0..steps.unsigned_abs() {
        if steps > 0 {
            let nx = idx + 1;
            cur += if (nx as usize) < n && (nx as usize) < n && vals[nx as usize].is_finite() && (idx as usize) < n && vals[idx as usize].is_finite() && idx >= 0 {
                vals[nx as usize] - vals[idx as usize]
            } else {
                inc_hi
            };
            idx = nx;
        } else {
            let nx = idx - 1;
            cur -= if nx >= 0 && (idx as usize) < n && vals[nx as usize].is_finite() && vals[idx as usize].is_finite() {
                vals[idx as usize] - vals[nx as usize]
            } else {
                inc_lo
            };
            idx = nx;
        }
    }
    cur
}

#[cfg(test)]
mod tests {
    use super::*;

    // Fixtures generated once from /home/claude/samples/CL1086464.xlsx (sheets ' graded spec sheet ' and
    // 'non denim speec sheet'). TSV is raw Excel-paste style (unquoted, with 12" inside a cell);
    // CSV was written by Python's csv module (quoted, decimal-comma tolerances as "0,5").
const GRADED_TSV: &str = r##"		DENIM & NON DENIM BOTTOMS MEASUREMENT CHART
											Dok. No:	CL.ÜR.S06-F20
											Y. Tarihi:	2014-03-11
											Rev. No:	01
											Rev. Tarihi:	2021-06-02


STYLE#		1086464							STYLE DESCRIPTION :		pant
BRAND :		COLIN'S							SIZE / RANGE : 		xs/xl
SEASON :		SS27 PH3							BASE PATTERN / FIT :		high rise / wide leg
MANUFACTURER :									FABRICATION :		0
DATE FOLDER CREATED :		17,03,2026							WASH :		1074805 baz

POM	MEASUREMENTS POINTS			XS	S	M	L	XL	XXL		1/2 body yarıda/tolerance  (+),(-)
20125	1/2 WAIST AT TOP EDGE		BEL  (DURGUN)	33	35	37	39.5	42	44.5		1
20245	WAIS TEXT'D  MINUMUM AT TOP EDGE		BEL  (GERGIN)	47	49	51	53.5	56	58.5		1
20305-A	HIP POSITION EXC.WB AT SIDE SEAM		K.H YAN BASEN ÖLÇÜM YERİ	16.5	17	17.5	18	18.5	19		0
20305-B	HIP POSITION EXC.WB AT CENTER FRONT		K.H ÖN ORTADAN BASEN ÖLÇÜM YERİ	15.5	16	16.5	17	17.5	18		0
20305	 ½ SEAT		1/2 BASEN	50	52	54	56.5	59	61.5		1
20865	 THIGH ( 1CM) FM CROTCH POINT		BALDIR ( 1 CM) AŞAĞIDAN	32	33	34	35.3	36.599999999999994	37.89999999999999		0.5
21505	 FRONT RISE TOP EDGE (CURVED )		ÖN AĞ ÜST KENARA ( KAVİSLİ ) K.D	29.5	30.5	31.5	32.8	34.099999999999994	35.39999999999999		0.5
21545	 BACK RISE TO TOP EDGE (CURVED )		ARKA AĞ ÜST KENARDAN (KAVİSLİ) K.D	40	41	42	43.3	44.599999999999994	45.89999999999999		0.5
20905	KNEE WIDTH 12"		DİZ YERİ 12" den	29.3	30	30.7	31.7	32.7	33.7		0.5
21125	 LEG OPENING 1/2 (STRAIGHT )		1/2 PAÇA ( DÜZ)	29.3	30	30.7	31.7	32.7	33.7		0
30210	 BOTTOM HEM HEIGHT		PAÇA KIVIRMA	2.8	2.8	2.8	2.8	2.8	2.8		0
21885	 INSEAM ( ALONG SM)		İÇBOY (DİKİŞ BOYUNCA) 	77	78	79	80	81	82		0,5
20265	 WAISTBAND WIDTH		KEMER ENİ	5.2	5.2	5.2	5.2	5.2	5.2		0
22145	 FRT PKT ALONG W/B		ÖN CEP AÇIKLIĞI ÜST KEMER BOYUNCA	3	3	3.5	3.5	4	4.5		0
22165	 FRT PKT LENGTH DWN OUTSEAM		ÖN CEP AÇIKLIĞI YAN DİKİŞ BOYUNCA	15.5	15.5	16	16	16.5	17		0
22565	 PKT BAG DEPTH		ÖN CEP TORBASI  DERİNLİĞİ ÖN ORTADAN KMR HRÇ	24	24	24	24	24	24		0
30845	1/2 DRAWCORD LENGTH (FOLD TO END)-		KORDON BOYU SARKAN KISIM	30	30	30	30	30	30		0
"##;
const GRADED_CSV: &str = r##",,DENIM & NON DENIM BOTTOMS MEASUREMENT CHART
,,,,,,,,,,,Dok. No:,CL.ÜR.S06-F20
,,,,,,,,,,,Y. Tarihi:,2014-03-11
,,,,,,,,,,,Rev. No:,01
,,,,,,,,,,,Rev. Tarihi:,2021-06-02


STYLE#,,1086464,,,,,,,STYLE DESCRIPTION :,,pant
BRAND :,,COLIN'S,,,,,,,SIZE / RANGE : ,,xs/xl
SEASON :,,SS27 PH3,,,,,,,BASE PATTERN / FIT :,,high rise / wide leg
MANUFACTURER :,,,,,,,,,FABRICATION :,,0
DATE FOLDER CREATED :,,"17,03,2026",,,,,,,WASH :,,1074805 baz

POM,MEASUREMENTS POINTS,,,XS,S,M,L,XL,XXL,,"1/2 body yarıda/tolerance  (+),(-)"
20125,1/2 WAIST AT TOP EDGE,,BEL  (DURGUN),33,35,37,39.5,42,44.5,,1
20245,WAIS TEXT'D  MINUMUM AT TOP EDGE,,BEL  (GERGIN),47,49,51,53.5,56,58.5,,1
20305-A,HIP POSITION EXC.WB AT SIDE SEAM,,K.H YAN BASEN ÖLÇÜM YERİ,16.5,17,17.5,18,18.5,19,,0
20305-B,HIP POSITION EXC.WB AT CENTER FRONT,,K.H ÖN ORTADAN BASEN ÖLÇÜM YERİ,15.5,16,16.5,17,17.5,18,,0
20305, ½ SEAT,,1/2 BASEN,50,52,54,56.5,59,61.5,,1
20865, THIGH ( 1CM) FM CROTCH POINT,,BALDIR ( 1 CM) AŞAĞIDAN,32,33,34,35.3,36.599999999999994,37.89999999999999,,0.5
21505, FRONT RISE TOP EDGE (CURVED ),,ÖN AĞ ÜST KENARA ( KAVİSLİ ) K.D,29.5,30.5,31.5,32.8,34.099999999999994,35.39999999999999,,0.5
21545, BACK RISE TO TOP EDGE (CURVED ),,ARKA AĞ ÜST KENARDAN (KAVİSLİ) K.D,40,41,42,43.3,44.599999999999994,45.89999999999999,,0.5
20905,"KNEE WIDTH 12""",,"DİZ YERİ 12"" den",29.3,30,30.7,31.7,32.7,33.7,,0.5
21125, LEG OPENING 1/2 (STRAIGHT ),,1/2 PAÇA ( DÜZ),29.3,30,30.7,31.7,32.7,33.7,,0
30210, BOTTOM HEM HEIGHT,,PAÇA KIVIRMA,2.8,2.8,2.8,2.8,2.8,2.8,,0
21885, INSEAM ( ALONG SM),,İÇBOY (DİKİŞ BOYUNCA) ,77,78,79,80,81,82,,"0,5"
20265, WAISTBAND WIDTH,,KEMER ENİ,5.2,5.2,5.2,5.2,5.2,5.2,,0
22145, FRT PKT ALONG W/B,,ÖN CEP AÇIKLIĞI ÜST KEMER BOYUNCA,3,3,3.5,3.5,4,4.5,,0
22165, FRT PKT LENGTH DWN OUTSEAM,,ÖN CEP AÇIKLIĞI YAN DİKİŞ BOYUNCA,15.5,15.5,16,16,16.5,17,,0
22565, PKT BAG DEPTH,,ÖN CEP TORBASI  DERİNLİĞİ ÖN ORTADAN KMR HRÇ,24,24,24,24,24,24,,0
30845,1/2 DRAWCORD LENGTH (FOLD TO END)-,,KORDON BOYU SARKAN KISIM,30,30,30,30,30,30,,0
"##;
const SINGLE_TSV: &str = r##"		DENIM & NON DENIM BOTTOMS MEASUREMENT CHART
											Dok. No:	CL.ÜR.S06-F20
											Y. Tarihi:	2014-03-11
											Rev. No:	01
											Rev. Tarihi:	2021-06-02


STYLE#		1086464							STYLE DESCRIPTION :		pant
BRAND :		COLIN'S							SIZE / RANGE : 		xs/xl
SEASON :		SS27 PH3							BASE PATTERN / FIT :		high rise / wide leg
MANUFACTURER :									FABRICATION :		0
DATE FOLDER CREATED :		17,03,2026							WASH :		1074805 baz

POM	MEASUREMENTS POINTS			S							1/2 body yarıda/tolerance  (+),(-)
20125	1/2 WAIST AT TOP EDGE		BEL  (DURGUN)	35							1
20245	WAIS TEXT'D  MINUMUM AT TOP EDGE		BEL  (GERGIN)	49							1
20305-A	HIP POSITION EXC.WB AT SIDE SEAM		K.H YAN BASEN ÖLÇÜM YERİ	17							0
20305-B	HIP POSITION EXC.WB AT CENTER FRONT		K.H ÖN ORTADAN BASEN ÖLÇÜM YERİ	16							0
20305	 ½ SEAT		1/2 BASEN	52							1
20865	 THIGH ( 1CM) FM CROTCH POINT		BALDIR ( 1 CM) AŞAĞIDAN	33							0.5
21505	 FRONT RISE TOP EDGE (CURVED )		ÖN AĞ ÜST KENARA ( KAVİSLİ ) K.D	30.5							0.5
21545	 BACK RISE TO TOP EDGE (CURVED )		ARKA AĞ ÜST KENARDAN (KAVİSLİ) K.D	41							0.5
20905	KNEE WIDTH 12"		DİZ YERİ 12" den	30							0.5
21125	 LEG OPENING 1/2 (STRAIGHT )		1/2 PAÇA ( DÜZ)	30							0
30210	 BOTTOM HEM HEIGHT		PAÇA KIVIRMA	2.8							0
21885	 INSEAM ( ALONG SM)		İÇBOY (DİKİŞ BOYUNCA) 	78							0,5
20265	 WAISTBAND WIDTH		KEMER ENİ	5.2							0
22145	 FRT PKT ALONG W/B		ÖN CEP AÇIKLIĞI ÜST KEMER BOYUNCA	3							0
22165	 FRT PKT LENGTH DWN OUTSEAM		ÖN CEP AÇIKLIĞI YAN DİKİŞ BOYUNCA	15.5							0
22565	 PKT BAG DEPTH		ÖN CEP TORBASI  DERİNLİĞİ ÖN ORTADAN KMR HRÇ	24							0
30845	1/2 DRAWCORD LENGTH (FOLD TO END)-		KORDON BOYU SARKAN KISIM	30							0
"##;

    fn graded() -> SpecSheet {
        parse_spec_text(GRADED_TSV).unwrap()
    }
    fn row<'a>(s: &'a SpecSheet, code: &str) -> &'a PomRow {
        s.rows.iter().find(|r| r.code == code).unwrap_or_else(|| panic!("no row {}", code))
    }

    #[test]
    fn real_graded_sheet() {
        let s = graded();
        assert_eq!(s.style, "1086464");
        assert_eq!(s.description, "pant");
        assert_eq!(s.brand, "COLIN'S");
        assert_eq!(s.season, "SS27 PH3");
        assert_eq!(s.fit, "high rise / wide leg");
        assert_eq!(s.sizes, ["XS", "S", "M", "L", "XL", "XXL"]);
        assert_eq!(s.base_size, "M");
        assert_eq!(s.rows.len(), 17);
        assert!(s.rows.iter().all(|r| r.values.len() == 6));
        assert_eq!(row(&s, "20125").values, [33.0, 35.0, 37.0, 39.5, 42.0, 44.5]);
        assert_eq!(row(&s, "21545").values, [40.0, 41.0, 42.0, 43.3, 44.6, 45.9]);
        // float noise 36.599999999999994 / 37.89999999999999 rounded to 0.01
        assert_eq!(row(&s, "20865").values, [32.0, 33.0, 34.0, 35.3, 36.6, 37.9]);
        assert_eq!(row(&s, "21505").values, [29.5, 30.5, 31.5, 32.8, 34.1, 35.4]);
        // text-typed '3' cells
        assert_eq!(row(&s, "22145").values, [3.0, 3.0, 3.5, 3.5, 4.0, 4.5]);
        // names, Turkish
        assert_eq!(row(&s, "20305").name, "½ SEAT");
        assert_eq!(row(&s, "20305").name_local, "1/2 BASEN");
        assert_eq!(row(&s, "20305-A").name_local, "K.H YAN BASEN ÖLÇÜM YERİ");
        assert_eq!(row(&s, "20905").name, "KNEE WIDTH 12\"");
        assert_eq!(row(&s, "21885").name_local, "İÇBOY (DİKİŞ BOYUNCA)");
        // tolerances: '1', '0,5', '0', numeric
        let t = |c: &str| (row(&s, c).tol_plus, row(&s, c).tol_minus);
        assert_eq!(t("20125"), (1.0, 1.0));
        assert_eq!(t("21885"), (0.5, 0.5)); // decimal comma
        assert_eq!(t("21125"), (0.0, 0.0));
        assert_eq!(t("20865"), (0.5, 0.5));
        assert!(s.rows.iter().all(|r| r.has_tolerance()));
    }

    #[test]
    fn single_size_sheet() {
        let s = parse_spec_text(SINGLE_TSV).unwrap();
        assert_eq!(s.sizes, ["S"]);
        assert_eq!(s.base_size, "S");
        assert_eq!(s.rows.len(), 17);
        assert_eq!(row(&s, "20125").values, [35.0]);
        assert_eq!(s.size_map("s")["20305"], 52.0);
    }

    #[test]
    fn csv_tsv_parity() {
        let a = parse_spec_text(GRADED_TSV).unwrap();
        let b = parse_spec_text(GRADED_CSV).unwrap();
        assert_eq!(a, b);
        assert_eq!(a.to_json().to_string(), b.to_json().to_string());
        assert_eq!(row(&b, "21885").tol_plus, 0.5);
        // ';' separated with unquoted decimal commas
        let semi: String = GRADED_TSV.lines().map(|l| l.replace('\t', ";")).collect::<Vec<_>>().join("\n");
        let c = parse_spec_text(&semi).unwrap();
        assert_eq!(a.rows, c.rows);
        // CRLF + BOM
        let crlf = format!("\u{feff}{}", GRADED_TSV.replace('\n', "\r\n"));
        assert_eq!(parse_spec_text(&crlf).unwrap().rows, a.rows);
    }

    #[test]
    fn pipe_layout_from_task_text() {
        let t = "STYLE# | 1086464 | STYLE DESCRIPTION : | pant\nBRAND : | COLIN'S\nPOM | MEASUREMENTS POINTS | BEL | XS | S | M | tol\n20125 | 1/2 WAIST | BEL (DURGUN) | 33 | 35 | 37 | 0,5\n";
        let s = parse_spec_text(t).unwrap();
        assert_eq!(s.style, "1086464");
        assert_eq!(s.description, "pant");
        assert_eq!(s.brand, "COLIN'S");
        assert_eq!(s.sizes, ["XS", "S", "M"]);
        assert_eq!(s.rows[0].values, [33.0, 35.0, 37.0]);
        assert_eq!(s.rows[0].name_local, "BEL (DURGUN)");
        assert_eq!(s.rows[0].tol_minus, 0.5);
    }

    #[test]
    fn numbers() {
        assert_eq!(parse_number("0,5"), Some(0.5));
        assert_eq!(parse_number("1/2"), Some(0.5));
        assert_eq!(parse_number("3 1/2"), Some(3.5));
        assert_eq!(parse_number("3½"), Some(3.5));
        assert_eq!(parse_number("-1/4"), Some(-0.25));
        assert_eq!(parse_number("12 cm"), Some(12.0));
        assert_eq!(parse_number("1,234.5"), Some(1234.5));
        assert_eq!(parse_number("1.234,5"), Some(1234.5));
        assert_eq!(parse_number("36.599999999999994").map(round2), Some(36.6));
        for bad in ["", "abc", "1/0", "17.03.2026", "17,03,2026", "NaN", "inf", "1e5", "1/2/3", ".", "--1", "½ ½"] {
            assert_eq!(parse_number(bad), None, "{}", bad);
        }
    }

    #[test]
    fn quotes_and_fractions_in_table() {
        let t = "POM,NAME,S,M,L,TOL (+),TOL (-)\n\"A1\",\"HALF \"\"CHEST\"\", wide\",\"20 1/2\",21,\"21,5\",\"1/2\",\"1/4\"\nA2,SLEEVE LENGTH,,60,61,,\n";
        let s = parse_spec_text(t).unwrap();
        assert_eq!(s.rows[0].name, "HALF \"CHEST\", wide");
        assert_eq!(s.rows[0].values, [20.5, 21.0, 21.5]);
        assert_eq!((s.rows[0].tol_plus, s.rows[0].tol_minus), (0.5, 0.25));
        assert!(s.rows[1].values[0].is_nan());
        assert_eq!(s.rows[1].value(0), None);
        assert!(!s.rows[1].has_tolerance());
        assert!(s.check().iter().any(|w| w.contains("A2") && w.contains("tolerance missing")));
        assert_eq!(s.base_size, "M");
    }

    #[test]
    fn garbage_is_err_not_panic() {
        for t in ["", "   \n\t\n", "hello world", "a,b,c\n1,2,3", "\"unterminated", "POM\tNAME\n", "POM,S,M\n", "\0\0\u{1}", "İİİ\tıı\t½½½", "POM\tS\nX\tabc\n"] {
            assert!(parse_spec_text(t).is_err(), "{:?}", t);
        }
        // deterministic pseudo-fuzz: must never panic
        let alpha: Vec<char> = "POM\t,;|\"\n\r XSML12345/½,.İıŞğ:#-+cm\u{a0}é€".chars().collect();
        let mut x: u64 = 0x1234_5678_9abc_def1;
        for _ in 0..3000 {
            let mut s = String::new();
            x ^= x << 13; x ^= x >> 7; x ^= x << 17;
            let len = (x % 120) as usize;
            for _ in 0..len {
                x ^= x << 13; x ^= x >> 7; x ^= x << 17;
                s.push(alpha[(x % alpha.len() as u64) as usize]);
            }
            let _ = parse_spec_text(&s);
        }
        // truncate the real sheet at many char boundaries
        for (i, _) in GRADED_TSV.char_indices().step_by(37) {
            let _ = parse_spec_text(&GRADED_TSV[..i]);
        }
        assert!(parse_spec_text(&"x".repeat(5_000_000)).is_err());
    }

    #[test]
    fn size_and_name_maps() {
        let s = graded();
        let m = s.size_map("L");
        assert_eq!(m.len(), 17);
        assert_eq!(m["20125"], 39.5);
        assert!(s.size_map("3XL").is_empty());
        let n = s.name_map("xs");
        assert_eq!(n["half_seat"], 50.0);
        assert_eq!(n["half_waist_at_top_edge"], 33.0);
        assert_eq!(n["knee_width_12"], 29.3);
        assert_eq!(n.len(), 17);
    }

    #[test]
    fn increments_and_extrapolation() {
        let s = graded();
        let inc = s.grade_increments();
        let w = inc.iter().find(|(c, _)| c == "20125").unwrap();
        assert_eq!(w.1, [2.0, 2.0, 2.5, 2.5, 2.5]);
        assert!(inc.iter().find(|(c, _)| c == "30210").unwrap().1.iter().all(|d| *d == 0.0));
        let e = s.extrapolate("3XL", "XXL", 1);
        assert_eq!(e["20125"], 47.0);
        assert_eq!(e["30210"], 2.8);
        assert_eq!(e["21545"], 47.2);
        // in-range steps use real increments: M +1 = L
        assert_eq!(s.extrapolate("L", "M", 1)["20125"], 39.5);
        assert_eq!(s.extrapolate("XXS", "XS", -1)["20125"], 31.0);
        assert!(s.extrapolate("x", "nope", 1).is_empty());
        let mut s2 = s.clone();
        s2.add_extrapolated_size("3xl", "XXL", 1).unwrap();
        assert_eq!(s2.sizes.last().unwrap(), "3XL");
        assert_eq!(s2.size_map("3XL")["20125"], 47.0);
        assert!(s2.add_extrapolated_size("S", "M", 1).is_err());
    }

    #[test]
    fn canonical_mapping() {
        let s = graded();
        let keys: Vec<&str> = s.rows.iter().map(|r| s.canonical(r).unwrap_or("?")).collect();
        assert!(!keys.contains(&"?"), "{:?}", keys);
        let mut uniq = keys.clone();
        uniq.sort();
        uniq.dedup();
        assert_eq!(uniq.len(), 17);
        assert_eq!(canonical_pom("20125", ""), Some("half_waist_relaxed"));
        assert_eq!(canonical_pom("20305-B", ""), Some("hip_pos_center_front"));
        assert_eq!(canonical_pom("20305 A", ""), Some("hip_pos_side_seam"));
        assert_eq!(canonical_pom("", "FRT PKT ALONG W/B"), Some("pocket_opening_waist"));
        assert_eq!(canonical_pom("", "FRT PKT LENGTH DWN OUTSEAM"), Some("pocket_opening_side"));
        assert_eq!(canonical_pom("", "BOTTOM HEM HEIGHT"), Some("hem_height"));
        // tops by name
        for (n, k) in [
            ("1/2 CHEST 1\" BELOW ARMHOLE", "half_chest"),
            ("ACROSS SHOULDER", "across_shoulder"),
            ("SHOULDER SLOPE", "shoulder_drop"),
            ("SLEEVE LENGTH FROM CB", "sleeve_length"),
            ("SLV OPENING", "half_sleeve_opening"),
            ("ARMHOLE STRAIGHT", "armhole"),
            ("COLLAR STAND HEIGHT", "collar_stand_height"),
            ("NECK DROP FRONT", "neck_drop"),
            ("HEM SWEEP", "hem_sweep"),
            ("BODY LENGTH FROM HPS", "body_length"),
            ("CHEST POCKET WIDTH", "pocket_width"),
            ("PLACKET WIDTH", "placket_width"),
            ("KOL BOYU", "sleeve_length"),
            ("GÖĞÜS ENİ", "half_chest"),
        ] {
            assert_eq!(canonical_pom("", n), Some(k), "{}", n);
        }
        assert_eq!(canonical_pom("99999", "SOMETHING ODD"), None);
        assert_eq!(canonical_pom("", ""), None);
        let cm = s.canonical_map("S");
        assert_eq!(cm["half_seat"], 52.0);
        assert!(is_half_measure("half_seat") && !is_half_measure("inseam"));
    }

    #[test]
    fn json_round_trip_and_grade_table() {
        let mut s = graded();
        s.rows[2].values[3] = f64::NAN; // blank cell survives as null
        let txt = s.to_json().to_string();
        let back = SpecSheet::from_json(&Json::parse(&txt).unwrap()).unwrap();
        assert_eq!(s, back);
        assert!(SpecSheet::from_json(&Json::obj()).is_err());
        let bad = Json::parse(r#"{"sizes":["S","M"],"rows":[{"code":"1","values":[1]}]}"#).unwrap();
        assert!(SpecSheet::from_json(&bad).is_err());

        let g = graded().spec_to_grade_table();
        let sizes = g.get("sizes").unwrap().as_arr().unwrap();
        assert_eq!(sizes.len(), 6);
        let steps: Vec<f64> = sizes.iter().map(|x| x.get("step").unwrap().as_f64().unwrap()).collect();
        assert_eq!(steps, [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]); // base M
        let l = &sizes[3];
        assert_eq!(l.get("label").unwrap().as_str(), Some("L"));
        let tab = l.get("table").unwrap().as_arr().unwrap();
        assert_eq!(tab.len(), 17);
        assert_eq!(tab[0].get("piece").unwrap().as_str(), Some("1/2 WAIST AT TOP EDGE"));
        let d = tab[0].get("deltas").unwrap().as_arr().unwrap()[0].as_arr().unwrap();
        assert_eq!((d[0].as_f64(), d[1].as_f64()), (Some(2.5), Some(0.0)));
        let base_tab = sizes[2].get("table").unwrap().as_arr().unwrap();
        assert!(base_tab.iter().all(|t| t.get("deltas").unwrap().as_arr().unwrap()[0].as_arr().unwrap()[0].as_f64() == Some(0.0)));
        assert_eq!(l.get("measurements").unwrap().get("20125").unwrap().as_f64(), Some(39.5));
    }

    #[test]
    fn checks() {
        let s = graded();
        let c = s.check();
        assert!(!c.iter().any(|w| w.contains("stretched")), "{:?}", c);
        assert!(!c.iter().any(|w| w.contains("monotonic") || w.contains("impossible") || w.contains("tolerance missing")), "{:?}", c);

        let mut b = graded();
        let i = b.rows.iter().position(|r| r.code == "20245").unwrap();
        b.rows[i].values[1] = 30.0; // stretched < relaxed
        let k = b.rows.iter().position(|r| r.code == "21545").unwrap();
        b.rows[k].values[3] = 39.0; // non-monotonic
        let a = b.rows.iter().position(|r| r.code == "20305").unwrap();
        b.rows[a].values[0] = -5.0; // impossible
        b.rows[0].tol_plus = f64::NAN; // missing tolerance
        let ins = b.rows.iter().position(|r| r.code == "21885").unwrap();
        b.rows[ins].values = vec![9.0; 6]; // inches-looking inseam
        let c = b.check();
        let has = |p: &str| c.iter().any(|w| w.contains(p));
        assert!(has("waist stretched (30) is smaller than waist relaxed (35)"), "{:?}", c);
        assert!(has("21545") && has("not monotonic"), "{:?}", c);
        assert!(has("impossible"), "{:?}", c);
        assert!(has("20125") && has("tolerance missing"), "{:?}", c);
        assert!(has("outside plausible"), "{:?}", c);
        assert!(!SpecSheet::default().check().is_empty());
    }
}
