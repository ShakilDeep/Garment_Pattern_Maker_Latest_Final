//! Zero-dependency `.xlsx` reader.
//!
//! An `.xlsx` file is a ZIP archive of XML parts.  This module implements, with no third-party
//! crates and no `unsafe`:
//!
//! * a minimal ZIP reader (central directory + local file headers; STORED and DEFLATE methods),
//! * a self-contained DEFLATE/INFLATE decoder (stored, fixed- and dynamic-Huffman blocks),
//! * a tolerant XML scanner for the SpreadsheetML parts we need
//!   (`workbook.xml`, `xl/_rels/workbook.xml.rels`, `sharedStrings.xml`, `styles.xml`,
//!   `worksheets/sheetN.xml`).
//!
//! The public surface is [`read_xlsx`] → `Vec<Sheet>` and [`sheet_to_tsv`].
//!
//! Robustness: the reader never panics on a truncated or garbled archive.  Every byte access is
//! bounds-checked; malformed input yields `Err(String)` (for whole-file problems) or is skipped
//! (for a single unreadable part).  See `docs/XLSX.md` for the format notes and coverage limits.
//!
//! wasm-safe: no threads, no `Instant`, no file IO — operates purely on the input byte slice.

// ===========================================================================================
// Public data model
// ===========================================================================================

/// One worksheet, expanded to a dense grid of cells (row-major, padded to the sheet's used
/// width so every row has the same number of columns).
#[derive(Clone, Debug, PartialEq)]
pub struct Sheet {
    pub name: String,
    pub rows: Vec<Vec<Cell>>,
}

/// A single cell.  `text` is the display text (shared/inline string, formula-string result,
/// shortest round-trip number, or a formatted date-time); `num` is the parsed numeric value
/// when the cell is numeric (for a date cell this is the Excel serial number).
#[derive(Clone, Debug, PartialEq, Default)]
pub struct Cell {
    pub text: String,
    pub num: Option<f64>,
}

impl Cell {
    fn empty() -> Cell {
        Cell { text: String::new(), num: None }
    }
}

// ===========================================================================================
// Public API
// ===========================================================================================

/// Parse a complete `.xlsx` file.  Returns one [`Sheet`] per worksheet, in workbook order.
///
/// Errors only when the archive itself cannot be read or when `xl/workbook.xml` is missing.
/// A single corrupt worksheet part is skipped (its sheet is returned empty) rather than
/// failing the whole read.
pub fn read_xlsx(bytes: &[u8]) -> Result<Vec<Sheet>, String> {
    let zip = Zip::parse(bytes)?;

    let workbook = zip
        .by_name("xl/workbook.xml")
        .ok_or_else(|| "not an xlsx: xl/workbook.xml missing".to_string())?;
    let wb_xml = String::from_utf8_lossy(&workbook);

    // Sheet declarations: name + r:id, in document order.
    let sheet_decls = parse_workbook_sheets(&wb_xml);
    if sheet_decls.is_empty() {
        return Err("workbook declares no sheets".to_string());
    }

    // r:id -> target part path (relative to xl/).
    let rels = zip
        .by_name("xl/_rels/workbook.xml.rels")
        .map(|b| parse_rels(&String::from_utf8_lossy(&b)))
        .unwrap_or_default();

    // Shared strings table (optional).
    let shared = zip
        .by_name("xl/sharedStrings.xml")
        .map(|b| parse_shared_strings(&String::from_utf8_lossy(&b)))
        .unwrap_or_default();

    // Style index -> is-date-format flag (optional).
    let date_styles = zip
        .by_name("xl/styles.xml")
        .map(|b| parse_date_styles(&String::from_utf8_lossy(&b)))
        .unwrap_or_default();

    let mut out = Vec::with_capacity(sheet_decls.len());
    for (name, rid) in sheet_decls {
        // Resolve the worksheet part; fall back to a positional guess if rels are missing.
        let target = rels.iter().find(|(id, _)| *id == rid).map(|(_, t)| t.clone());
        let path = match target {
            Some(t) => normalize_part(&t),
            None => String::new(),
        };
        let data = if !path.is_empty() {
            zip.by_name(&path)
        } else {
            None
        };
        let rows = match data {
            Some(bytes) => {
                parse_worksheet(&String::from_utf8_lossy(&bytes), &shared, &date_styles)
            }
            None => Vec::new(),
        };
        out.push(Sheet { name, rows });
    }
    Ok(out)
}

/// Render a sheet as TSV: cells tab-separated, rows newline-separated, no trailing newline.
/// Numeric cells use their display text (shortest round-trip number, or formatted date-time),
/// matching what a conventional spreadsheet extractor produces.
pub fn sheet_to_tsv(s: &Sheet) -> String {
    let mut out = String::new();
    for (i, row) in s.rows.iter().enumerate() {
        if i > 0 {
            out.push('\n');
        }
        for (j, c) in row.iter().enumerate() {
            if j > 0 {
                out.push('\t');
            }
            out.push_str(&c.text);
        }
    }
    out
}

// ===========================================================================================
// ZIP reader
// ===========================================================================================

struct ZipEntry {
    name: String,
    method: u16,
    comp_size: u64,
    uncomp_size: u64,
    local_header_off: u64,
}

struct Zip<'a> {
    data: &'a [u8],
    entries: Vec<ZipEntry>,
}

const SIG_EOCD: u32 = 0x0605_4b50;
const SIG_EOCD64: u32 = 0x0606_4b50;
const SIG_EOCD64_LOC: u32 = 0x0707_4b50;
const SIG_CDH: u32 = 0x0201_4b50;
const SIG_LFH: u32 = 0x0403_4b50;

fn rd_u16(b: &[u8], p: usize) -> Option<u16> {
    b.get(p..p + 2).map(|s| u16::from_le_bytes([s[0], s[1]]))
}
fn rd_u32(b: &[u8], p: usize) -> Option<u32> {
    b.get(p..p + 4).map(|s| u32::from_le_bytes([s[0], s[1], s[2], s[3]]))
}
fn rd_u64(b: &[u8], p: usize) -> Option<u64> {
    b.get(p..p + 8)
        .map(|s| u64::from_le_bytes([s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]]))
}

impl<'a> Zip<'a> {
    fn parse(data: &'a [u8]) -> Result<Zip<'a>, String> {
        if data.len() < 22 {
            return Err("file too small to be a zip".to_string());
        }
        // Find the End Of Central Directory record by scanning backwards for its signature.
        // The EOCD comment can be up to 65535 bytes, so scan at most that far.
        let max_back = data.len().min(22 + 0xFFFF);
        let start = data.len() - max_back;
        let mut eocd: Option<usize> = None;
        let mut i = data.len() - 22;
        loop {
            if rd_u32(data, i) == Some(SIG_EOCD) {
                eocd = Some(i);
                break;
            }
            if i == start {
                break;
            }
            i -= 1;
        }
        let eocd = eocd.ok_or_else(|| "zip: end-of-central-directory not found".to_string())?;

        let mut cd_count = rd_u16(data, eocd + 10).unwrap_or(0) as u64;
        let mut cd_size = rd_u32(data, eocd + 12).unwrap_or(0) as u64;
        let mut cd_off = rd_u32(data, eocd + 16).unwrap_or(0) as u64;

        // ZIP64: when any field is saturated, read the ZIP64 EOCD record.
        if cd_off == 0xFFFF_FFFF || cd_size == 0xFFFF_FFFF || cd_count == 0xFFFF {
            if eocd >= 20 {
                let loc = eocd - 20;
                if rd_u32(data, loc) == Some(SIG_EOCD64_LOC) {
                    if let Some(z64) = rd_u64(data, loc + 8) {
                        let z64 = z64 as usize;
                        if rd_u32(data, z64) == Some(SIG_EOCD64) {
                            cd_count = rd_u64(data, z64 + 32).unwrap_or(cd_count);
                            cd_size = rd_u64(data, z64 + 40).unwrap_or(cd_size);
                            cd_off = rd_u64(data, z64 + 48).unwrap_or(cd_off);
                        }
                    }
                }
            }
        }

        let cd_start = cd_off as usize;
        let cd_end = cd_start.saturating_add(cd_size as usize).min(data.len());
        let mut entries = Vec::new();
        let mut p = cd_start;
        // Cap iterations defensively so a malformed count cannot spin forever.
        let cap = (cd_count as usize).saturating_add(4).min(1 << 20);
        while p + 46 <= cd_end && entries.len() < cap {
            if rd_u32(data, p) != Some(SIG_CDH) {
                break;
            }
            let method = rd_u16(data, p + 10).unwrap_or(0);
            let mut comp_size = rd_u32(data, p + 20).unwrap_or(0) as u64;
            let mut uncomp_size = rd_u32(data, p + 24).unwrap_or(0) as u64;
            let name_len = rd_u16(data, p + 28).unwrap_or(0) as usize;
            let extra_len = rd_u16(data, p + 30).unwrap_or(0) as usize;
            let comment_len = rd_u16(data, p + 32).unwrap_or(0) as usize;
            let mut local_off = rd_u32(data, p + 42).unwrap_or(0) as u64;

            let name_start = p + 46;
            let name_end = name_start + name_len;
            let name = match data.get(name_start..name_end) {
                Some(s) => String::from_utf8_lossy(s).into_owned(),
                None => break,
            };

            // ZIP64 extra field (id 0x0001) overrides saturated sizes/offset, in a fixed order.
            let extra_start = name_end;
            let extra_end = extra_start + extra_len;
            if let Some(extra) = data.get(extra_start..extra_end.min(data.len())) {
                let mut q = 0usize;
                while q + 4 <= extra.len() {
                    let id = u16::from_le_bytes([extra[q], extra[q + 1]]);
                    let sz = u16::from_le_bytes([extra[q + 2], extra[q + 3]]) as usize;
                    let body_start = q + 4;
                    if body_start + sz > extra.len() {
                        break;
                    }
                    if id == 0x0001 {
                        let mut b = body_start;
                        if uncomp_size == 0xFFFF_FFFF {
                            uncomp_size = rd_u64(extra, b).unwrap_or(uncomp_size);
                            b += 8;
                        }
                        if comp_size == 0xFFFF_FFFF {
                            comp_size = rd_u64(extra, b).unwrap_or(comp_size);
                            b += 8;
                        }
                        if local_off == 0xFFFF_FFFF {
                            local_off = rd_u64(extra, b).unwrap_or(local_off);
                        }
                    }
                    q = body_start + sz;
                }
            }

            entries.push(ZipEntry {
                name,
                method,
                comp_size,
                uncomp_size,
                local_header_off: local_off,
            });
            p = extra_end + comment_len;
        }

        if entries.is_empty() {
            return Err("zip: no entries in central directory".to_string());
        }
        Ok(Zip { data, entries })
    }

    /// Decompress the named entry.  Returns `None` when the entry is absent or unreadable.
    fn by_name(&self, name: &str) -> Option<Vec<u8>> {
        let e = self.entries.iter().find(|e| e.name == name)?;
        self.read_entry(e)
    }

    fn read_entry(&self, e: &ZipEntry) -> Option<Vec<u8>> {
        let data = self.data;
        let lh = e.local_header_off as usize;
        if rd_u32(data, lh) != Some(SIG_LFH) {
            return None;
        }
        let name_len = rd_u16(data, lh + 26)? as usize;
        let extra_len = rd_u16(data, lh + 28)? as usize;
        let start = lh + 30 + name_len + extra_len;
        let comp = e.comp_size as usize;
        let body = data.get(start..start.checked_add(comp)?.min(data.len()))?;
        match e.method {
            0 => Some(body.to_vec()), // STORED
            8 => {
                let hint = (e.uncomp_size as usize).min(1 << 28);
                inflate(body, hint).ok()
            }
            _ => None, // unsupported method
        }
    }
}

// ===========================================================================================
// DEFLATE / INFLATE (RFC 1951), self-contained.
// ===========================================================================================

struct BitReader<'a> {
    data: &'a [u8],
    pos: usize, // byte index
    bitbuf: u32,
    bitcnt: u32,
}

impl<'a> BitReader<'a> {
    fn new(data: &'a [u8]) -> Self {
        BitReader { data, pos: 0, bitbuf: 0, bitcnt: 0 }
    }
    #[inline]
    fn getbit(&mut self) -> Result<u32, String> {
        if self.bitcnt == 0 {
            let b = *self.data.get(self.pos).ok_or("inflate: unexpected end of input")?;
            self.pos += 1;
            self.bitbuf = b as u32;
            self.bitcnt = 8;
        }
        let bit = self.bitbuf & 1;
        self.bitbuf >>= 1;
        self.bitcnt -= 1;
        Ok(bit)
    }
    #[inline]
    fn getbits(&mut self, n: u32) -> Result<u32, String> {
        let mut v = 0u32;
        for i in 0..n {
            v |= self.getbit()? << i;
        }
        Ok(v)
    }
    fn align_byte(&mut self) {
        self.bitbuf = 0;
        self.bitcnt = 0;
    }
}

/// Canonical Huffman decode table built from a list of code lengths.
struct Huff {
    // For each symbol, its code length (0 = unused).
    counts: [u16; 16],
    symbols: Vec<u16>,
}

impl Huff {
    fn build(lengths: &[u16]) -> Result<Huff, String> {
        let mut counts = [0u16; 16];
        for &l in lengths {
            if l as usize > 15 {
                return Err("inflate: code length out of range".to_string());
            }
            counts[l as usize] += 1;
        }
        counts[0] = 0;
        // offsets of each length group
        let mut offs = [0u16; 16];
        let mut sum = 0u16;
        for len in 1..16 {
            offs[len] = sum;
            sum += counts[len];
        }
        let mut symbols = vec![0u16; lengths.len()];
        for (sym, &l) in lengths.iter().enumerate() {
            if l != 0 {
                let idx = offs[l as usize] as usize;
                if idx >= symbols.len() {
                    return Err("inflate: bad huffman table".to_string());
                }
                symbols[idx] = sym as u16;
                offs[l as usize] += 1;
            }
        }
        Ok(Huff { counts, symbols })
    }

    fn decode(&self, br: &mut BitReader) -> Result<u16, String> {
        let mut code: i32 = 0;
        let mut first: i32 = 0;
        let mut index: i32 = 0;
        for len in 1..16 {
            code |= br.getbit()? as i32;
            let count = self.counts[len] as i32;
            if code - first < count {
                let i = (index + (code - first)) as usize;
                return self
                    .symbols
                    .get(i)
                    .copied()
                    .ok_or_else(|| "inflate: symbol index out of range".to_string());
            }
            index += count;
            first += count;
            first <<= 1;
            code <<= 1;
        }
        Err("inflate: invalid huffman code".to_string())
    }
}

const LEN_BASE: [u16; 29] = [
    3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131,
    163, 195, 227, 258,
];
const LEN_EXTRA: [u8; 29] = [
    0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0,
];
const DIST_BASE: [u16; 30] = [
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537,
    2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577,
];
const DIST_EXTRA: [u8; 30] = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13,
    13,
];

/// Inflate a raw DEFLATE stream (no zlib/gzip wrapper).  `size_hint` pre-reserves output.
fn inflate(data: &[u8], size_hint: usize) -> Result<Vec<u8>, String> {
    let mut br = BitReader::new(data);
    let mut out: Vec<u8> = Vec::with_capacity(size_hint.min(1 << 24));
    // Hard cap on output to avoid a decompression bomb from crafted input.
    let out_cap: usize = size_hint.saturating_mul(4).max(1 << 20).min(1 << 30);

    loop {
        let bfinal = br.getbit()?;
        let btype = br.getbits(2)?;
        match btype {
            0 => inflate_stored(&mut br, &mut out, out_cap)?,
            1 => inflate_block(&mut br, &mut out, &fixed_litlen()?, &fixed_dist()?, out_cap)?,
            2 => {
                let (lit, dist) = read_dynamic_tables(&mut br)?;
                inflate_block(&mut br, &mut out, &lit, &dist, out_cap)?;
            }
            _ => return Err("inflate: reserved block type".to_string()),
        }
        if bfinal == 1 {
            break;
        }
    }
    Ok(out)
}

fn inflate_stored(br: &mut BitReader, out: &mut Vec<u8>, out_cap: usize) -> Result<(), String> {
    br.align_byte();
    let len = *br.data.get(br.pos).ok_or("inflate: stored len")? as usize
        | (*br.data.get(br.pos + 1).ok_or("inflate: stored len")? as usize) << 8;
    br.pos += 4; // skip LEN + NLEN
    let end = br.pos.checked_add(len).ok_or("inflate: stored overflow")?;
    let chunk = br.data.get(br.pos..end).ok_or("inflate: stored truncated")?;
    if out.len() + chunk.len() > out_cap {
        return Err("inflate: output exceeds cap".to_string());
    }
    out.extend_from_slice(chunk);
    br.pos = end;
    Ok(())
}

fn inflate_block(
    br: &mut BitReader,
    out: &mut Vec<u8>,
    lit: &Huff,
    dist: &Huff,
    out_cap: usize,
) -> Result<(), String> {
    loop {
        let sym = lit.decode(br)?;
        if sym == 256 {
            return Ok(()); // end of block
        }
        if sym < 256 {
            if out.len() + 1 > out_cap {
                return Err("inflate: output exceeds cap".to_string());
            }
            out.push(sym as u8);
            continue;
        }
        let li = (sym - 257) as usize;
        if li >= LEN_BASE.len() {
            return Err("inflate: invalid length symbol".to_string());
        }
        let length =
            LEN_BASE[li] as usize + br.getbits(LEN_EXTRA[li] as u32)? as usize;
        let dsym = dist.decode(br)? as usize;
        if dsym >= DIST_BASE.len() {
            return Err("inflate: invalid distance symbol".to_string());
        }
        let distance =
            DIST_BASE[dsym] as usize + br.getbits(DIST_EXTRA[dsym] as u32)? as usize;
        if distance == 0 || distance > out.len() {
            return Err("inflate: distance too far back".to_string());
        }
        if out.len() + length > out_cap {
            return Err("inflate: output exceeds cap".to_string());
        }
        let start = out.len() - distance;
        for k in 0..length {
            let b = out[start + k];
            out.push(b);
        }
    }
}

fn read_dynamic_tables(br: &mut BitReader) -> Result<(Huff, Huff), String> {
    let hlit = br.getbits(5)? as usize + 257;
    let hdist = br.getbits(5)? as usize + 1;
    let hclen = br.getbits(4)? as usize + 4;
    if hlit > 286 || hdist > 30 {
        return Err("inflate: bad dynamic header counts".to_string());
    }
    const ORDER: [usize; 19] = [
        16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15,
    ];
    let mut cl_lengths = [0u16; 19];
    for i in 0..hclen {
        cl_lengths[ORDER[i]] = br.getbits(3)? as u16;
    }
    let cl_huff = Huff::build(&cl_lengths)?;

    let total = hlit + hdist;
    let mut lengths: Vec<u16> = Vec::with_capacity(total);
    while lengths.len() < total {
        let sym = cl_huff.decode(br)?;
        match sym {
            0..=15 => lengths.push(sym),
            16 => {
                let prev = *lengths.last().ok_or("inflate: repeat with no previous")?;
                let rep = 3 + br.getbits(2)? as usize;
                for _ in 0..rep {
                    if lengths.len() >= total {
                        break;
                    }
                    lengths.push(prev);
                }
            }
            17 => {
                let rep = 3 + br.getbits(3)? as usize;
                for _ in 0..rep {
                    if lengths.len() >= total {
                        break;
                    }
                    lengths.push(0);
                }
            }
            18 => {
                let rep = 11 + br.getbits(7)? as usize;
                for _ in 0..rep {
                    if lengths.len() >= total {
                        break;
                    }
                    lengths.push(0);
                }
            }
            _ => return Err("inflate: bad code-length symbol".to_string()),
        }
    }
    if lengths.len() != total {
        return Err("inflate: code-length overrun".to_string());
    }
    let lit = Huff::build(&lengths[..hlit])?;
    let dist = Huff::build(&lengths[hlit..])?;
    Ok((lit, dist))
}

fn fixed_litlen() -> Result<Huff, String> {
    let mut l = [0u16; 288];
    for (i, item) in l.iter_mut().enumerate() {
        *item = if i < 144 {
            8
        } else if i < 256 {
            9
        } else if i < 280 {
            7
        } else {
            8
        };
    }
    Huff::build(&l)
}

fn fixed_dist() -> Result<Huff, String> {
    Huff::build(&[5u16; 30])
}

// ===========================================================================================
// XML scanning (tolerant, no dependency)
// ===========================================================================================

fn xml_unescape(s: &str) -> String {
    if !s.contains('&') {
        return s.to_string();
    }
    let mut out = String::with_capacity(s.len());
    let mut chars = s.char_indices().peekable();
    while let Some((i, c)) = chars.next() {
        if c != '&' {
            out.push(c);
            continue;
        }
        // read entity up to ';'
        let rest = &s[i + 1..];
        if let Some(semi) = rest.find(';') {
            let ent = &rest[..semi];
            let replaced = match ent {
                "lt" => Some('<'),
                "gt" => Some('>'),
                "amp" => Some('&'),
                "quot" => Some('"'),
                "apos" => Some('\''),
                _ if ent.starts_with("#x") || ent.starts_with("#X") => {
                    u32::from_str_radix(&ent[2..], 16).ok().and_then(char::from_u32)
                }
                _ if ent.starts_with('#') => {
                    ent[1..].parse::<u32>().ok().and_then(char::from_u32)
                }
                _ => None,
            };
            if let Some(ch) = replaced {
                out.push(ch);
                // advance iterator past the entity + ';'
                for _ in 0..(semi + 1) {
                    chars.next();
                }
                continue;
            }
        }
        out.push('&');
    }
    out
}

/// Value of attribute `key` inside an element start-tag `tag` (`<c r="A1" .../>`).
fn attr<'a>(tag: &'a str, key: &str) -> Option<&'a str> {
    let mut search = 0;
    while let Some(rel) = tag[search..].find(key) {
        let at = search + rel;
        // ensure the match is a whole attribute name (preceded by space / tag start)
        let prev_ok = at == 0 || tag.as_bytes()[at - 1] == b' ' || tag.as_bytes()[at - 1] == b'<';
        let after = at + key.len();
        let eq = tag[after..].trim_start();
        if prev_ok && eq.starts_with('=') {
            let rest = eq[1..].trim_start();
            let quote = rest.as_bytes().first().copied();
            if quote == Some(b'"') || quote == Some(b'\'') {
                let q = quote.unwrap() as char;
                if let Some(end) = rest[1..].find(q) {
                    return Some(&rest[1..1 + end]);
                }
            }
        }
        search = after;
    }
    None
}

/// Collect the `<sheet .../>` declarations from `workbook.xml`: `(name, r:id)` in order.
fn parse_workbook_sheets(xml: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut pos = 0;
    while let Some(rel) = xml[pos..].find("<sheet ") {
        let start = pos + rel;
        let end = match xml[start..].find('>') {
            Some(e) => start + e + 1,
            None => break,
        };
        let tag = &xml[start..end];
        let name = attr(tag, "name").map(xml_unescape).unwrap_or_default();
        let rid = attr(tag, "r:id")
            .or_else(|| attr(tag, "id"))
            .unwrap_or_default()
            .to_string();
        out.push((name, rid));
        pos = end;
    }
    out
}

/// Parse `workbook.xml.rels`: `(Id, Target)` pairs.
fn parse_rels(xml: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    let mut pos = 0;
    while let Some(rel) = xml[pos..].find("<Relationship") {
        let start = pos + rel;
        let end = match xml[start..].find('>') {
            Some(e) => start + e + 1,
            None => break,
        };
        let tag = &xml[start..end];
        let id = attr(tag, "Id").unwrap_or_default().to_string();
        let target = attr(tag, "Target").map(xml_unescape).unwrap_or_default();
        if !id.is_empty() {
            out.push((id, target));
        }
        pos = end;
    }
    out
}

/// Normalize a rels Target into a zip part path under `xl/`.
fn normalize_part(target: &str) -> String {
    let t = target.trim();
    if let Some(stripped) = t.strip_prefix('/') {
        return stripped.to_string();
    }
    if t.starts_with("xl/") {
        return t.to_string();
    }
    format!("xl/{}", t)
}

/// Parse `sharedStrings.xml` into the ordered string table.  Each `<si>` concatenates all of
/// its `<t>` runs (rich-text runs are flattened to plain text).
fn parse_shared_strings(xml: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut pos = 0;
    while let Some(rel) = xml[pos..].find("<si>") {
        let start = pos + rel + 4;
        let end = match xml[start..].find("</si>") {
            Some(e) => start + e,
            None => break,
        };
        out.push(collect_text_runs(&xml[start..end]));
        pos = end + 5;
    }
    out
}

/// Concatenate the text of every `<t ...>...</t>` run inside a fragment.
fn collect_text_runs(frag: &str) -> String {
    let mut s = String::new();
    let mut pos = 0;
    while let Some(rel) = frag[pos..].find("<t") {
        let tstart = pos + rel;
        // next char must be '>' or whitespace (so we don't match <table> etc.)
        let after = &frag[tstart + 2..];
        let is_t = after.starts_with('>') || after.starts_with(' ') || after.starts_with('/');
        if !is_t {
            pos = tstart + 2;
            continue;
        }
        let open_end = match frag[tstart..].find('>') {
            Some(e) => tstart + e + 1,
            None => break,
        };
        // self-closing <t/> -> empty
        if frag[tstart..open_end].ends_with("/>") {
            pos = open_end;
            continue;
        }
        let close = match frag[open_end..].find("</t>") {
            Some(e) => open_end + e,
            None => break,
        };
        s.push_str(&xml_unescape(&frag[open_end..close]));
        pos = close + 4;
    }
    s
}

// ---- styles → date detection -------------------------------------------------------------

/// Returns, indexed by cell style index (`s=` on a `<c>`), whether that style is a date/time
/// number format.  Built-in date format ids (14-22, 45-47) and custom formats whose code
/// contains date/time tokens (y/m/d/h/s) are treated as dates.
fn parse_date_styles(xml: &str) -> Vec<bool> {
    // custom numFmtId -> is-date
    let mut custom_date: Vec<(u32, bool)> = Vec::new();
    let mut pos = 0;
    while let Some(rel) = xml[pos..].find("<numFmt ") {
        let start = pos + rel;
        let end = match xml[start..].find('>') {
            Some(e) => start + e + 1,
            None => break,
        };
        let tag = &xml[start..end];
        if let (Some(id), Some(code)) = (attr(tag, "numFmtId"), attr(tag, "formatCode")) {
            if let Ok(idn) = id.parse::<u32>() {
                custom_date.push((idn, fmt_is_date(&xml_unescape(code))));
            }
        }
        pos = end;
    }

    // Locate the cellXfs block and read each <xf>'s numFmtId in order.
    let block = match (xml.find("<cellXfs"), xml.find("</cellXfs>")) {
        (Some(a), Some(b)) if b > a => &xml[a..b],
        _ => return Vec::new(),
    };
    let mut out = Vec::new();
    let mut p = 0;
    while let Some(rel) = block[p..].find("<xf") {
        let start = p + rel;
        let end = match block[start..].find('>') {
            Some(e) => start + e + 1,
            None => break,
        };
        let tag = &block[start..end];
        let fid = attr(tag, "numFmtId").and_then(|s| s.parse::<u32>().ok()).unwrap_or(0);
        let is_date = builtin_is_date(fid)
            || custom_date.iter().find(|(i, _)| *i == fid).map(|(_, d)| *d).unwrap_or(false);
        out.push(is_date);
        p = end;
    }
    out
}

fn builtin_is_date(id: u32) -> bool {
    (14..=22).contains(&id) || (45..=47).contains(&id)
}

/// Heuristic: a format code is a date/time format if, after removing bracketed sections,
/// quoted literals and escapes, it contains any of y/m/d/h/s and no pure-number placeholder
/// that would mark it as a plain numeric format.
fn fmt_is_date(code: &str) -> bool {
    let mut cleaned = String::with_capacity(code.len());
    let mut chars = code.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '[' => {
                // skip to matching ]
                for n in chars.by_ref() {
                    if n == ']' {
                        break;
                    }
                }
            }
            '"' => {
                for n in chars.by_ref() {
                    if n == '"' {
                        break;
                    }
                }
            }
            '\\' => {
                chars.next();
            }
            _ => cleaned.push(c),
        }
    }
    let lower = cleaned.to_ascii_lowercase();
    lower.chars().any(|c| matches!(c, 'y' | 'm' | 'd' | 'h' | 's'))
}

// ---- worksheet parsing -------------------------------------------------------------------

/// Parse column letters of an A1 reference into a zero-based column index.
fn col_index(a1: &str) -> Option<usize> {
    let mut col: usize = 0;
    let mut any = false;
    for b in a1.bytes() {
        if b.is_ascii_uppercase() {
            col = col.checked_mul(26)?.checked_add((b - b'A' + 1) as usize)?;
            any = true;
        } else if b.is_ascii_digit() {
            break;
        } else if b.is_ascii_lowercase() {
            col = col.checked_mul(26)?.checked_add((b - b'a' + 1) as usize)?;
            any = true;
        } else {
            return None;
        }
    }
    if any {
        Some(col - 1)
    } else {
        None
    }
}

/// Grid limits (Excel itself allows 1,048,576 x 16,384; real specs are tiny).
const MAX_ROWS: usize = 200_000;
const MAX_COLS: usize = 1_024;

fn parse_worksheet(xml: &str, shared: &[String], date_styles: &[bool]) -> Vec<Vec<Cell>> {
    // grid[row][col]; we collect sparse then densify.
    let mut cells: Vec<(usize, usize, Cell)> = Vec::new();
    let mut max_row = 0usize;
    let mut max_col = 0usize;

    // iterate rows
    let mut pos = 0;
    while let Some(rel) = xml[pos..].find("<row") {
        let rstart = pos + rel;
        let rhead_end = match xml[rstart..].find('>') {
            Some(e) => rstart + e + 1,
            None => break,
        };
        let row_tag = &xml[rstart..rhead_end];
        let self_closing = row_tag.ends_with("/>");
        let r = attr(row_tag, "r").and_then(|s| s.parse::<usize>().ok());
        if self_closing {
            pos = rhead_end;
            continue;
        }
        let rbody_end = match xml[rhead_end..].find("</row>") {
            Some(e) => rhead_end + e,
            None => xml.len(),
        };
        let body = &xml[rhead_end..rbody_end];

        // track the current row number; cells may carry their own r so we recompute per cell
        let row_num_default = r.unwrap_or(max_row + 1).min(MAX_ROWS + 1);

        // iterate cells
        let mut cp = 0;
        let mut auto_col = 0usize;
        while let Some(crel) = body[cp..].find("<c") {
            let cstart = cp + crel;
            // ensure <c is a cell, not <col> or <cols>
            let after = &body[cstart + 2..];
            if !(after.starts_with(' ') || after.starts_with('>') || after.starts_with('/')) {
                cp = cstart + 2;
                continue;
            }
            let chead_end = match body[cstart..].find('>') {
                Some(e) => cstart + e + 1,
                None => break,
            };
            let ctag = &body[cstart..chead_end];
            let cell_self_closing = ctag.ends_with("/>");
            let cref = attr(ctag, "r");
            let (row_num, col_num) = match cref {
                Some(a1) => {
                    let rn = a1
                        .bytes()
                        .skip_while(|b| b.is_ascii_alphabetic())
                        .fold(0usize, |acc, b| {
                            if b.is_ascii_digit() {
                                acc * 10 + (b - b'0') as usize
                            } else {
                                acc
                            }
                        });
                    let cn = col_index(a1).unwrap_or(auto_col);
                    (if rn == 0 { row_num_default } else { rn }, cn)
                }
                None => (row_num_default, auto_col),
            };
            auto_col = col_num + 1;

            let ty = attr(ctag, "t").unwrap_or("n");
            let style = attr(ctag, "s").and_then(|s| s.parse::<usize>().ok());

            let (inner, next) = if cell_self_closing {
                ("", chead_end)
            } else {
                let cbody_end = match body[chead_end..].find("</c>") {
                    Some(e) => chead_end + e,
                    None => body.len(),
                };
                (&body[chead_end..cbody_end], (cbody_end + 4).min(body.len()))
            };

            if row_num > MAX_ROWS || col_num >= MAX_COLS {
                cp = next;
                continue; // hostile / absurd coordinates: ignore rather than allocate
            }
            let cell = build_cell(ty, style, inner, shared, date_styles);
            if cell.text.is_empty() && cell.num.is_none() {
                // still record position so densify keeps width, but only if it has a style ref
            }
            if row_num > max_row {
                max_row = row_num;
            }
            if col_num > max_col {
                max_col = col_num;
            }
            cells.push((row_num, col_num, cell));
            cp = next;
        }

        pos = (rbody_end + 6).min(xml.len());
        if row_num_default > max_row && row_num_default <= MAX_ROWS {
            max_row = row_num_default;
        }
    }

    if cells.is_empty() {
        return Vec::new();
    }

    let width = max_col + 1;
    if max_row.saturating_mul(width) > 8_000_000 {
        return Vec::new(); // refuse pathological sparse sheets
    }
    let mut grid: Vec<Vec<Cell>> = (0..max_row).map(|_| vec![Cell::empty(); width]).collect();
    for (r, c, cell) in cells {
        if r >= 1 && r <= max_row && c < width {
            grid[r - 1][c] = cell;
        }
    }
    grid
}

fn build_cell(
    ty: &str,
    style: Option<usize>,
    inner: &str,
    shared: &[String],
    date_styles: &[bool],
) -> Cell {
    match ty {
        "s" => {
            // shared string: <v>index</v>
            let idx = inner_value(inner).and_then(|v| v.trim().parse::<usize>().ok());
            let text = idx.and_then(|i| shared.get(i)).cloned().unwrap_or_default();
            Cell { text, num: None }
        }
        "inlineStr" => {
            let text = collect_text_runs(inner);
            Cell { text, num: None }
        }
        "str" => {
            // formula string result in <v>
            let text = inner_value(inner).map(xml_unescape).unwrap_or_default();
            Cell { text, num: None }
        }
        "b" => {
            let v = inner_value(inner).unwrap_or("0");
            let text = if v.trim() == "1" { "TRUE" } else { "FALSE" };
            Cell { text: text.to_string(), num: None }
        }
        "e" => {
            // error value
            let text = inner_value(inner).map(xml_unescape).unwrap_or_default();
            Cell { text, num: None }
        }
        _ => {
            // numeric (default). <v> holds the raw number string.
            match inner_value(inner) {
                Some(raw) => {
                    let raw = raw.trim();
                    let num = raw.parse::<f64>().ok();
                    let is_date = style
                        .and_then(|s| date_styles.get(s).copied())
                        .unwrap_or(false);
                    let text = match num {
                        Some(n) if is_date => format_excel_date(n),
                        Some(n) => format_number(raw, n),
                        None => raw.to_string(),
                    };
                    Cell { text, num }
                }
                None => Cell::empty(),
            }
        }
    }
}

/// Extract the text inside the first `<v>...</v>` of a cell body.
fn inner_value(inner: &str) -> Option<&str> {
    let start = inner.find("<v")?;
    let open_end = inner[start..].find('>')? + start + 1;
    if inner[start..open_end].ends_with("/>") {
        return Some("");
    }
    let close = inner[open_end..].find("</v>")? + open_end;
    Some(&inner[open_end..close])
}

/// Format a numeric cell to match a conventional extractor: integer-looking source stays
/// integer; anything with a fraction/exponent uses the shortest round-trip float text.
fn format_number(raw: &str, n: f64) -> String {
    if raw.contains('.') || raw.contains('e') || raw.contains('E') {
        // Rust's default f64 Display is shortest round-trip, matching Python's repr.
        format!("{}", n)
    } else {
        raw.to_string()
    }
}

/// Convert an Excel serial date-time (1900 date system, with the historical 1900 leap-year
/// bug) to `YYYY-MM-DD HH:MM:SS`, matching openpyxl's `str(datetime)` output.
fn format_excel_date(serial: f64) -> String {
    let mut day_serial = serial.trunc() as i64;
    let frac = serial - serial.trunc();
    let mut total_secs = (frac * 86400.0).round() as i64;
    if total_secs >= 86400 {
        // rounding carried into the next day
        total_secs -= 86400;
        day_serial += 1;
    }
    let (year, month, day) = date_from_serial(day_serial);
    let (hh, mm, ss) = (total_secs / 3600, (total_secs % 3600) / 60, total_secs % 60);
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}:{:02}",
        year, month, day, hh, mm, ss
    )
}

/// Civil date from an Excel 1900-system serial day number (day 0 == 1899-12-30, which absorbs
/// the historical fake 1900-02-29 for serials >= 60).  1899-12-30 is 25569 days before the
/// Unix civil epoch 1970-01-01.
fn date_from_serial(serial_days: i64) -> (i64, i64, i64) {
    // For serials before the phantom 1900-02-29 (serial 60), Excel is one day ahead of the
    // 1899-12-30 epoch, so those use the 1899-12-31 epoch instead.
    if serial_days < 60 {
        civil_from_days(serial_days - 25568)
    } else {
        civil_from_days(serial_days - 25569)
    }
}

/// days since 1970-01-01 -> (year, month, day).  (Hinnant, http://howardhinnant.github.io)
fn civil_from_days(z: i64) -> (i64, i64, i64) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as i64; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365; // [0, 399]
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let d = doy - (153 * mp + 2) / 5 + 1; // [1, 31]
    let m = if mp < 10 { mp + 3 } else { mp - 9 }; // [1, 12]
    (if m <= 2 { y + 1 } else { y }, m, d)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn col_index_basic() {
        assert_eq!(col_index("A1"), Some(0));
        assert_eq!(col_index("B2"), Some(1));
        assert_eq!(col_index("Z9"), Some(25));
        assert_eq!(col_index("AA1"), Some(26));
        assert_eq!(col_index("AB10"), Some(27));
        assert_eq!(col_index("N31"), Some(13));
    }

    #[test]
    fn date_conversion_known_points() {
        // Excel serial 41709 == 2014-03-11, 44349 == 2021-06-02 (verified against openpyxl).
        assert_eq!(format_excel_date(41709.0), "2014-03-11 00:00:00");
        assert_eq!(format_excel_date(44349.0), "2021-06-02 00:00:00");
        // Serial 1 == 1900-01-01 in the Excel 1900 system.
        assert_eq!(format_excel_date(1.0), "1900-01-01 00:00:00");
    }

    #[test]
    fn number_format_matches_repr() {
        assert_eq!(format_number("39.5", 39.5), "39.5");
        assert_eq!(format_number("42", 42.0), "42");
        assert_eq!(format_number("0", 0.0), "0");
        // shortest round-trip of this specific double is the long form
        let v: f64 = "36.599999999999994".parse().unwrap();
        assert_eq!(format_number("36.599999999999994", v), "36.599999999999994");
        let v2: f64 = "35.299999999999997".parse().unwrap();
        assert_eq!(format_number("35.299999999999997", v2), "35.3");
    }

    #[test]
    fn inflate_stored_roundtrip() {
        // A single stored block: BFINAL=1, BTYPE=00, then LEN/NLEN, then bytes.
        let payload = b"hello world";
        let mut raw = Vec::new();
        raw.push(0x01u8); // bfinal=1, btype=00 -> byte 0b00000001
        let len = payload.len() as u16;
        raw.extend_from_slice(&len.to_le_bytes());
        raw.extend_from_slice(&(!len).to_le_bytes());
        raw.extend_from_slice(payload);
        let out = inflate(&raw, payload.len()).unwrap();
        assert_eq!(out, payload);
    }

    fn lcg(seed: &mut u64) -> u64 {
        *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        *seed >> 33
    }

    fn crc32(d: &[u8]) -> u32 {
        let mut c = !0u32;
        for &b in d {
            c ^= b as u32;
            for _ in 0..8 {
                c = if c & 1 != 0 { (c >> 1) ^ 0xEDB8_8320 } else { c >> 1 };
            }
        }
        !c
    }

    /// Build a STORED-only zip (tests the container + XML parser without any sample file).
    fn build_zip(files: &[(&str, &str)]) -> Vec<u8> {
        let mut out = Vec::new();
        let mut cd = Vec::new();
        for (name, body) in files {
            let off = out.len() as u32;
            let crc = crc32(body.as_bytes());
            let mut lh = Vec::new();
            lh.extend_from_slice(&0x0403_4b50u32.to_le_bytes());
            lh.extend_from_slice(&[20, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
            lh.extend_from_slice(&crc.to_le_bytes());
            lh.extend_from_slice(&(body.len() as u32).to_le_bytes());
            lh.extend_from_slice(&(body.len() as u32).to_le_bytes());
            lh.extend_from_slice(&(name.len() as u16).to_le_bytes());
            lh.extend_from_slice(&0u16.to_le_bytes());
            lh.extend_from_slice(name.as_bytes());
            out.extend_from_slice(&lh);
            out.extend_from_slice(body.as_bytes());
            cd.extend_from_slice(&0x0201_4b50u32.to_le_bytes());
            cd.extend_from_slice(&[20, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
            cd.extend_from_slice(&crc.to_le_bytes());
            cd.extend_from_slice(&(body.len() as u32).to_le_bytes());
            cd.extend_from_slice(&(body.len() as u32).to_le_bytes());
            cd.extend_from_slice(&(name.len() as u16).to_le_bytes());
            cd.extend_from_slice(&[0u8; 12]);
            cd.extend_from_slice(&off.to_le_bytes());
            cd.extend_from_slice(name.as_bytes());
        }
        let cd_off = out.len() as u32;
        out.extend_from_slice(&cd);
        out.extend_from_slice(&0x0605_4b50u32.to_le_bytes());
        out.extend_from_slice(&[0, 0, 0, 0]);
        out.extend_from_slice(&(files.len() as u16).to_le_bytes());
        out.extend_from_slice(&(files.len() as u16).to_le_bytes());
        out.extend_from_slice(&(cd.len() as u32).to_le_bytes());
        out.extend_from_slice(&cd_off.to_le_bytes());
        out.extend_from_slice(&0u16.to_le_bytes());
        out
    }

    fn mini_xlsx() -> Vec<u8> {
        build_zip(&[
            ("xl/workbook.xml", r#"<workbook><sheets><sheet name="A &amp; B" sheetId="1" r:id="rId1"/></sheets></workbook>"#),
            ("xl/_rels/workbook.xml.rels", r#"<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>"#),
            ("xl/sharedStrings.xml", r#"<sst><si><t>hello</t></si><si><r><t>wor</t></r><r><t>ld</t></r></si></sst>"#),
            ("xl/worksheets/sheet1.xml", r#"<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1"><v>36.599999999999994</v></c></row><row r="3"><c r="B3" t="inlineStr"><is><t>in</t></is></c><c r="C3" t="s"><v>1</v></c></row></sheetData></worksheet>"#),
        ])
    }

    #[test]
    fn synthetic_xlsx_parses() {
        let sheets = read_xlsx(&mini_xlsx()).unwrap();
        assert_eq!(sheets.len(), 1);
        assert_eq!(sheets[0].name, "A & B");
        assert_eq!(sheets[0].rows.len(), 3);
        assert_eq!(sheets[0].rows[0][0].text, "hello");
        assert_eq!(sheets[0].rows[0][2].num, Some(36.599999999999994));
        assert_eq!(sheets[0].rows[2][1].text, "in");
        assert_eq!(sheets[0].rows[2][2].text, "world");
        assert_eq!(sheet_to_tsv(&sheets[0]), "hello\t\t36.599999999999994\n\t\t\n\tin\tworld");
    }

    #[test]
    fn fuzz_truncated_and_garbled_never_panic() {
        let base = mini_xlsx();
        for n in 0..base.len() {
            let _ = read_xlsx(&base[..n]);
        }
        let mut seed = 0x1234_5678_9abc_def0u64;
        for _ in 0..4000 {
            let mut m = base.clone();
            for _ in 0..1 + (lcg(&mut seed) % 6) {
                let i = (lcg(&mut seed) as usize) % m.len();
                m[i] = lcg(&mut seed) as u8;
            }
            let _ = read_xlsx(&m);
        }
        for len in [0usize, 1, 21, 22, 23, 100] {
            let v: Vec<u8> = (0..len).map(|_| lcg(&mut seed) as u8).collect();
            assert!(read_xlsx(&v).is_err() || len > 22);
        }
        // hostile cell coordinates must not allocate a giant grid
        let evil = build_zip(&[
            ("xl/workbook.xml", r#"<workbook><sheets><sheet name="x" r:id="rId1"/></sheets></workbook>"#),
            ("xl/_rels/workbook.xml.rels", r#"<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>"#),
            ("xl/worksheets/sheet1.xml", r#"<worksheet><sheetData><row r="99999999"><c r="ZZZZZZ99999999"><v>1</v></c></row><row r="1"><c r="A1"><v>2</v></c></row></sheetData></worksheet>"#),
        ]);
        let s = read_xlsx(&evil).unwrap();
        assert_eq!(s[0].rows.len(), 1);
    }

    #[test]
    fn fuzz_real_file_never_panics() {
        let b = match std::fs::read("/home/claude/samples/CL1086464.xlsx") {
            Ok(b) => b,
            Err(_) => return,
        };
        assert!(read_xlsx(&b).is_ok());
        let mut seed = 42u64;
        for _ in 0..60 {
            let n = (lcg(&mut seed) as usize) % b.len();
            let _ = read_xlsx(&b[..n]); // truncated
        }
        for _ in 0..60 {
            let mut m = b.clone();
            for _ in 0..8 {
                let i = (lcg(&mut seed) as usize) % m.len();
                m[i] ^= 1 << (lcg(&mut seed) % 8);
            }
            let _ = read_xlsx(&m); // bit flips (may hit deflate streams)
        }
    }

    #[test]
    fn xml_unescape_entities() {
        assert_eq!(xml_unescape("a &amp; b &lt;c&gt; &#65;"), "a & b <c> A");
        assert_eq!(xml_unescape("plain"), "plain");
    }

    #[test]
    fn attr_extraction() {
        let tag = r#"<c r="A1" s="252" t="s">"#;
        assert_eq!(attr(tag, "r"), Some("A1"));
        assert_eq!(attr(tag, "s"), Some("252"));
        assert_eq!(attr(tag, "t"), Some("s"));
        assert_eq!(attr(tag, "x"), None);
    }
}
