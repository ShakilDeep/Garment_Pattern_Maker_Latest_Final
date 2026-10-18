# Optitex PDS binary container (v21.4.1103.0) - what is established

Scope: reverse engineering from ONE intact sample (`pant_1074664.PDS`, 90404 B, 5 sizes XS S M L XL,
base S, 7 pieces) plus the XML of one corrupted upload (`shirt_1078375_CORRUPTED_UPLOAD.PDS`, whose
binary bytes >= 0x80 were replaced by `EF BF BD`; it is NOT used for decoding, only as negative
evidence below). Reader: `src/pds_bin.rs` (`decode`, `inspect`). All claims carry a status:

* PROVEN: re-derives independent ground truth (XML `GEOM_INFO`, MARKER svg) on the pant sample, or is a
  byte-exact structural fact checked by tests.
* HYPOTHESIS: consistent with the sample, not independently confirmed.
* UNKNOWN: seen, meaning not established.

Offsets: "file" = absolute in the .PDS; "tail" = offset in `61dcbea7.tail`, which starts at the CRLF
after `</STYLE>` (file offset 15158). The Rust reader's tail starts 2 bytes later (after the CRLF,
file offset 15160), so Rust offsets = tail offsets - 2.

## 1. Container framing (PROVEN, `pant_inspect_framing`)

```
file 0   dc 54 ef 12            magic (bytes), u32 LE 0x12ef54dc
     4   25 00 00 00            u32 = 37   (UNKNOWN meaning; shirt: 0x29)
     8   4a 00 00 00            u32 = 74   (UNKNOWN; shirt: 0x5a)
    12   c4 05 24 60            u32 0x602405c4 = THE XOR KEY (section 2)
    16   66 00 00 00 | 6d 00 00 00 | 1c 00 00 00      UNKNOWN u32 x3 (shirt: 0x26, ?, 0x4d)
    28   01 04 17 20 "1079077- CROSS PKT PANT"        tag 01 04, u8 len 23, 0x20, style name (== XML <NAME>)
    55   10 28 02 29 02 2a 5c 2f 0c 0c               UNKNOWN small tags
    65   f3 3a 00 00            u32 = 15091 = length of the XML block INCLUDING its trailing CRLF
    69   "<?xml ... </STYLE>\r\n"   (69 .. 15160)
 15160   24 0b 87 00 "F:\ALL Pattern\...\1074664 - CROSS PKT PANT.PDS"   id 24, type 0b, u16 len 135, string
 15301   29 10 30 c0 91 01 00 00 31 10 01 28 32 c4 ...   start of the tagged record stream
```

* `u32 @ (xml_start-4) == tail_start - xml_start` holds (15091). Used as a damage warning only.
* Header numbers other than the XOR key are UNKNOWN. Nothing in the reader depends on them.

## 2. Coordinates are f32 XOR-obfuscated with a per-file key (PROVEN on pant)

Plain float/double/int copies of the cm values do not exist because every f32 in the tail is stored as
`le32(bits(f32) XOR KEY)`, `KEY` = u32 at file offset 12 (pant: `0x602405c4`).

Evidence (pant, KEY = 0x602405c4): the 4-byte unit `c4 05 24 60` (= KEY) decodes to `0.0` and is by far the
most frequent unit of the tail; `c4 05 a4 5f` -> `1.0`; `c4 05 24 a0` -> `-2.0`; `a2 63 82 5f` -> `1.3` (the
seam allowance); `1f 0a ed 5f` -> `1.5707964` (pi/2); `00 1d 18 23` -> `188.0967` and `1d 87 b1 23` ->
`299.0222`, which are exactly `<POSITION X=188.0967 Y=299.0222>` of WAIST- BELT in the XML.

Key derivation status (item #24): on the pant, header dword @12 == the most frequent tail dword
(3777 occurrences = keyed 0.0) == `0x602405c4`, two independent routes to the same value, test
`key_header_equals_most_frequent_tail_dword`. The key is NOT derived from any other header word
(`0x25`, `0x4a`, `0x66`, `0x6d`, `0x1c` are unrelated to it as far as one file can show), so there
is no formula to implement: the key is READ from the header and CROSS-CHECKED against the tail mode.
`decode` now (a) tries header@12, tail mode, sample key, (b) keeps the candidate validating most
piece/sizes, (c) breaks ties in favour of the candidate equal to the tail mode. Measured limits of
XML validation (test `pant_key_bit_sensitivity`, single-bit key errors on the pant):
rejected: bits 14-19, 23-30; accepted (35/35 or partial): bits 0-8 (< 0.01 cm error), 9-13
(partial), 20-22 (2-6 of 35), and **bit 31 (35/35)**. Bit 31 flips the sign of every coordinate,
a point reflection that preserves bbox/area/perimeter, so XML validation alone would return mirrored
geometry; the tie-break fixes this whenever the tail has >= 16 keyed zeros (every real file; test
`sign_flipped_header_key_does_not_reflect_geometry`). A damaged header is recovered from the tail
(`damaged_header_key_is_recovered_from_tail`); wrong keys are rejected (`wrong_key_is_rejected`,
`pant_wrong_key_rejected`). UNPROVEN: that header@12 is the key for any file other than the pant.

Per-file key (PROVEN as "not a global constant", HYPOTHESIS that it is the header dword): the shirt upload has
a different header dword (`?? 2b 4c 57`, first byte destroyed) and its tail contains `?? 2b 4c 57` 3899 times
(its encoding of 0.0) and `ef bf bd 05 24 60` zero times. How the key is derived is UNKNOWN. The reader
tries: header dword@12, the most frequent tail dword, then the sample key, and keeps the candidate that
validates the most piece/size entries against the XML.

## 3. Typed values of the tail stream (PROVEN for the codes used)

A value is `[id u8][type u8][payload]`. Type codes understood by `read_typed` (all others make the parser stop,
never guess):

| type byte | payload | evidence |
|---|---|---|
| `0x80,0x84,..,0x9c` | `((t-0x80)/4+1)` f32 (keyed) | `a0 80 <pi/2>` 1 elem; `af 84` 2; `bd 88` 3; `61 90` 5; `ad 9c` 8 |
| `0xa0` | u16 count, then f32 x count | `5e a0 0a 00` = 10 floats (belt contour) |
| `0xc0..0xdc` (low bits 0/1) | `((t&0xfc)-0xc0)/4+1` u32 | `63 c8` 3 ints, `c4` 2 ints, `62 d0` 5 ints |
| `0xe0` | u16 count, u32 x count | `62 e0 18 00` 24 point ids |
| `0x43..0x5f` (low bits 11) | `(t-0x43)/4+1` u16 | `fd 53` 5 x u16, `fe 4f` 4 x u16 |
| `0x63` | u16 count, u16 x count | `fd 63 18 00` |
| `0x18` | u16 count, u8 x count | `5f 18 18 00 <24 flag bytes>` |
| `0x17` | u32 N, then 2N bytes | `fc 17 60 00 00 00` + 192 B (24 vertices x 2 keyed f32) |
| `0x0b` | u16 len + chars | `24 0b 87 00 ...`, `32 0b 03 00 "C:\"` |
| `0x10` | struct/record start (see 4.2) | `04 10 ..`, `69 10 ..`, `02 10 <len> 20 <name>` |

The "count in the type byte" scheme is a regularity (inline counts 1..8, explicit count beyond) seen across 40+
distinct values; it is HYPOTHESIS beyond the exact codes listed.

## 4. Pieces, contours, grading (PROVEN on pant, see section 6 for residuals)

### 4.1 Piece anchor
`02 10 <len u8> 20 <name>` e.g. tail 1387 `02 10 0b 20 "WAIST- BELT"`, 4159 FRONT, 13044 BACK, 20569 PKT-IN,
31643 FACING, 34755 DRAWSTRING, 36685 FACING1 (same order as the XML). The region of a piece runs to the next
anchor. (The tail past FACING1 ~ 39182 is a shader/material library, `*.cgfx`, `msl_*` strings: UNKNOWN
semantics, skipped.)

### 4.2 Contour object (the geometry)
Each piece region holds several contour objects. Header immediately before the coordinate array
(N = number of vertices):

| role | header bytes (PROVEN by match with XML) |
|---|---|
| sew outline | `03 04 N 24 63 c8 <u32 a> <u32 b> ff ff ff ff` (a,b = object ids, UNKNOWN meaning) |
| cut outline | `4f 04 N 24 40 28 63 c8 <u32 a> <u32 b> ff ff ff ff` |
| auxiliary | `03 04 N 24 80 28 ...` (preceded by `05 10 01 28 bf c0 <id> be c4 .. <idx>`): UNKNOWN meaning (FRONT has 2, BACK 1, PKT-IN 10; bbox/area do not match any XML number). Ignored. |

Then `5e <f32 array type>` = interleaved x,y (cm, absolute layout coordinates, y up), 2N floats, followed by
per-vertex arrays in this order (ids are fixed): `62` u32 point ids, `5f 18` u8 flags, `fe` u16 zeros, `fc 17` 2 f32
per vertex (all 0.0 in sample), `fd` u16 ones (all 1 in sample), `61` f32 per-vertex seam-allowance width
(1.0 / 1.3 / -1.0 ...), `60 18` u8 (0x64 'd', belt ends 0x65 'e'; UNKNOWN), then vertex records.

Vertex records: `04 10 [k 24] <fields> 00 00` (k omitted for vertex 0). Fields are ordinary typed values
(`a0 80 <f32>` UNKNOWN single float, e.g. pi/2 or 6.215; `ad 9c <8 f32>`; `af 84 <2 f32>`).
Sequential parsing stops at the first unknown byte; scanning for `04 10` anywhere is WRONG (it picks up the
next piece's records; this was the cause of a false 1 cm error during the analysis).

### 4.3 Grading (PROVEN for size order XS,S,M,L,XL with base S)
Only the BASE size has absolute coordinates. `ad 9c` holds 4 (dx,dy) pairs = steps between consecutive sizes
of the XML size list: pair i connects size i and size i+1 and `p[i+1] = p[i] - step[i]` (negative numbers in
the file mean the later size is larger). `af 84 <dx dy>` = the same step for all four pairs. A vertex with no
`ad/af` field has zero steps if its flag byte has bit 0x80 set; if bit 0x80 is clear (flag `0x40` or `0x00`) the vertex is a
non-rule point: its step is the arc-length (base size) weighted interpolation between the previous and next
vertex with bit 0x80 (cyclic). Flag values seen: 0x80, 0xc0 (rule), 0x40, 0x00 (interpolated). Bit 0x40 = curve vertex: see section 4.6.

Examples (WAIST- BELT sew vertex 1: steps `-2.0 -2.0 -2.5 -2.5` -> sew width 49.5 / 51.5 / 53.5 / 56.0 / 58.5 =
XML SEW_PERIMETER 218.8 .. 254.8 exactly; FACING1 vertices 4,5: `0 1.0 0 1.0` -> XS=S, M=L, as in the XML).

### 4.4 HALF pieces
`<HALF>CLOSE</HALF>`: the file stores one half; the fold edge is the closing edge (last->first vertex). XML
`SIZE_X/SIZE_Y` describe the stored half, `AREA/PERIMETER` the mirrored whole (belt S: 52.8x13.0, area 0.1373 =
2 x 686.4 cm2, perimeter 237.2 = 2 x (131.6 - 13.0)). The reader mirrors across the fold line and
validates that. (The MARKER svg draws both halves; the left polygon equals the mirror, PROVEN.)

### 4.5 Notches (PROVEN positions of the base size)
Record `69 10 <k> 24 0a 28 .. 2a e1 c4 <i32> 2b/.. <..> 20 4e 00 00 e3 88 <3 f32> e4 94 <6 f32> 00 00`; the six
floats are `x1 y1 x2 y2 0 0`: x1,y1 = a point that coincides with sew vertex k (checked for k=2 of PKT-IN), x2,y2 = the inner end of the 0.7 cm notch line. Notches appear on the
sew contour records and again (at cut vertices) on the cut contour records. PKT-IN S: (277.578,320.261)-(276.879,320.223)
and (262.383,315.227)-(262.393,315.926) equal the blue MARKER notch lines after the global transform below. XML
`<NOTCH><COUNT>2` for PKT-IN and FACING matches. Notch types, other internals (drills, internal lines, grain
line, text) are UNKNOWN. Notch grading is UNKNOWN (only base size is returned).

### 4.6 Curves (item #20) - what is stored, what is reconstructed
FINDINGS (pant, all 6 curved pieces):
* **No control points / tangents / bulges are stored.** The only per-vertex curve datum is flag bit `0x40`.
  The `fc 17` per-vertex 2xf32 blob is all 0.0 in every piece, vertex records carry only grading steps
  (`ad 9c` / `af 84`), and no other float field varies per vertex. A curve is therefore a run of closely
  spaced vertices, i.e. Optitex already stores the spline as a dense sampling.
* Consequence: the headroom is small. Even Optitex's own MARKER polygon (its tessellation) is within
  +-0.011 % of XML PERIMETER, and the vertex polygon is within 0.041 % at base size S.
* `PdsContour::tessellate` is a RECONSTRUCTION, not decoded data. Rule: an edge i->i+1 becomes the arc of
  the circle through (i-1, i, i+1) when BOTH endpoints carry 0x40; all other edges stay straight.
  Rejected alternatives (Python prototypes, `scratch/variants.py`, base S, sum of |perimeter error|):
  vertex polygon 0.0667 %, circular arc 0.0328 %, centripetal Catmull-Rom 0.0558 % (tension 0.5) / 0.0337 % (1.0);
  an unmodified centripetal CR overshoots by 0.2-1.1 % and "either endpoint flagged" by ~6 %.
  Independent shape check against the marker polygon (base S, FRONT, Python only): max deviation
  0.065 cm (chords) -> 0.041 cm (arcs).
* VALIDATION (Rust test `pant_curve_tessellation`, 35 piece/sizes, max_chord 0.05 cm, error vs XML PERIMETER):
  mean |error| 0.0284 % -> 0.0241 %, max 0.1685 % -> 0.1488 % (PKT-IN XL). Base size: PKT-IN 0.0409 -> 0.0164 %,
  FRONT 0.0046 -> 0.0021 %, BACK 0.0059 -> 0.0007 %, FACING 0.0151 -> 0.0135 %. NOT an improvement everywhere:
  FRONT XS (0.0296 -> 0.0368 %) and BACK XS (0.0253 -> 0.0307 %) got slightly worse; belt, DRAWSTRING,
  FACING1 have no (or no effective) curves. The residual of the reconstruction is of the same order as the
  XML's own rounding in graded sizes (non-rule vertices are interpolated, see 4.3), so it cannot be pushed
  down further without ground truth. Conclusion: PROVEN = the flag marks curve vertices and curves are
  dense-sampled; UNPROVEN = the exact curve Optitex evaluates between them (which spline, what tension).
* What would settle it: `sq10_curve.pds` (section 9, item 3): ONE curved edge defined by 3 vertices with a
  known radius; the arc/spline type is then readable from where the intermediate edges deviate from the circle.

### 4.7 Metadata (item #21)
* **Quantity**: from XML `<QUANTITY>` (test checks all 35 entries); no separate binary decode needed/attempted.
* **Grain line** (PROVEN association, partly proven geometry). Per piece region, two `type 0x8c` records
  (4 keyed f32): `55 8c [scale, gx, gy, angle]` (anchor + direction, e.g. 3pi/2 for the belt, 0.321 rad FACING1)
  and `c2 8c [x1, y1, x2, y2]` (line endpoints). The midpoint of the endpoints equals the anchor
  (< 0.01 cm, used by the finder). Anchor y == XML `<POSITION>` y for 7/7 pieces (6 within 0.001 cm,
  rotated FACING1 within 0.01 cm). Anchor x does NOT equal POSITION x (FRONT 0.20, BACK 0.41, FACING 0.76 cm,
  belt 25.75 cm off; only DRAWSTRING equal), so only y is used for validation and `grain` is set only if it holds.
  MARKER svg: belt grain is the `#FF6633` path (vertical, 12.48 cm, midpoint = POSITION). Stored belt line is
  vertical but 6.24 cm = half of 12.48 (HYPOTHESIS: HALF piece stores half the grain); grain LENGTH is therefore
  not claimed validated. The marker draws grain only for the belt, so no other piece can be checked that way.
  Returned for the base size only (`PdsPieceGeom.grain`); grading of grain is unproven. `position` is the XML value.
* **Notch grading across sizes**: notch anchors are returned for every size = base notch + the (validated) grading
  delta of its anchor sew vertex (PKT-IN: XS=S, M/L = S-1.0 cm in y, XL = S-2.0 cm). RECONSTRUCTION: only the base
  size is checked against the marker (PROVEN, test `pant_matches_marker_svg`); the graded positions are NOT
  independently validated (the marker holds only the base size, XML has only counts/lengths), and the assumption that
  the 0.7 cm notch keeps its offset under grading is unproven. Notch type/length: XML only (`T_NOTCH`, 2.4 mm entries).
* **Internal lines, drills**: the pant has none (XML has no internal-line/drill tags, marker draws none), so
  `internal_lines` / `drills` are always empty; the binary encoding is UNKNOWN. Needs `sq10_drill.pds`,
  `sq10_internal.pds` (section 9).

## 5. Validation transform to the MARKER svg (PROVEN, test `pant_matches_marker_svg`)
`marker_x = (x - 124.9967) * 100`, `marker_y = (399.462 - y) * 100` (svg units 0.01 cm), one transform for all
pieces of this file. Every decoded base-size cut vertex of FRONT, BACK, PKT-IN, FACING, DRAWSTRING, FACING1
lies within 0.08 cm of the marker outline (marker points are re-tessellated, rounded to 0.01 cm). Marker corner
vertices coincide with vertices flagged 0x80/0xc0 to 0.01 cm. The marker is NOT used by `decode`.

## 6. Residuals (pant, `pant_residuals_are_small`, 35 piece/size cut outlines vs XML GEOM_INFO)
* base size S: max perimeter error 0.041 %, bbox exact for belt/FRONT/BACK/DRAWSTRING/FACING1; PKT-IN 0.042x0.017 cm,
  FACING 0.02 cm (control polygon vs. true curve).
* all sizes: max perimeter 0.169 %, max area 0.379 % (XML areas are rounded to 1 cm2, i.e. up to 0.8 % on FACING1), max bbox 0.134 cm.
* sew outlines: perimeter <= 0.22 %, area <= 0.48 % (same rounding caveat). DRAWSTRING and the belt are exact.
Therefore tolerances in code (bbox 0.2 cm, perimeter 0.3 %, area 0.6 % + 0.6 cm2) are looser than the requested 0.1 %.
The reason is NOT noise: polygons run through the stored vertices, while Optitex draws curves between 0x40 vertices.
Curve evaluation is UNKNOWN; `PdsContour::tessellate` offers an arc RECONSTRUCTION that lowers these residuals slightly (section 4.6); `cut`/`sew` stay vertex polygons.

## 7. Things that look like structure but are not
* The "small raw-deflate streams" at tail 8119, 9684, 10188, 16903: all four offsets lie inside uncompressed
  typed arrays (zero u16 array `fe 63 1c 00`, float arrays). Raw-deflate on repetitive bytes decodes by
  coincidence. The `@@@@`/`dddd` runs are the u8 arrays `5f 18` (0x40/0x80) and `60 18` (0x64). No compression
  is needed to explain any geometry. (Absence of compression elsewhere is UNPROVEN.)
* `c4 05 24 60` repeated = 0.0 keyed, not a separator. `0f a1 39 00` + 57 units = 57 keyed floats in a
  per-object block (3D/cloth data, UNKNOWN, ignored).
* 4x4 identity doubles (`9b 19 80` + 16 x 8 B, `f0 3f` = 1.0) are raw, un-keyed doubles: transform matrices.

## 8. UNPROVEN / UNKNOWN (reader refuses or ignores these)
1. Whether the header dword is always the key (only one intact file); it is not derivable from the other header words (section 2).
2. Files with a different number of sizes or a base size other than the second: the step-to-size mapping
   was only validated for (5 sizes, base index 1). The reader still tries and validates against XML.
3. Exact curve type between 0x40 vertices (arc reconstruction only, 4.6); other flag bits, `60 18` array, `fc 17`/`fd`/`fe` arrays, `a0 80` field,
   ids `a`,`b` of contour headers, auxiliary contours, `66 4c ..`.
4. Validated notch grading, notch types, grain length/grading, drills, internal lines, text, mirror-pair/`HALF` values other than CLOSE,
   piece quantity/material in binary (XML is used), POSITION in binary (belt's `188.0967 299.0222` appears at tail 3145).
5. Other Optitex versions. Shirt: unverified (binary destroyed).
6. Extended sections (shader library, 3D, textures) and the leading header words.
7. A PDS writer: deliberately not implemented (cannot round-trip in Optitex).

## 8b. Items blocked on more files (#22, #23)
* **#22 other Optitex versions / size layouts**: needs, EXACTLY: (a) the same pant saved by a different Optitex
  version (any != 21.4.1103.0) to see which tags/ids move; (b) a style with a base size that is first and one
  where it is last, and one with 1 and with 3 sizes (step-to-size mapping and `ad`/`af` field widths are only
  proven for 5 sizes, base index 1); (c) a second intact file at 21.4.1103.0 to test "header@12 == key" and the
  `0x55 8c / c2 8c` grain records on pieces other than these 7.
* **#23 intact shirt**: `shirt_1078375_CORRUPTED_UPLOAD.PDS` has every byte >= 0x80 replaced by `EF BF BD`, which is
  not reversible; its binary tail cannot be decoded. Needs the original `1078375- Men Regular SS Shirt.PDS`
  uploaded as a binary (zip it or base64 it so no UTF-8 re-encoding happens). It would also supply the first
  file with internal lines / drills / more notches (collar, sleeve) and HALF-less curved pieces.

## 9. Minimal extra samples that would settle the rest
Save from Optitex, one change per file, starting from an empty style:
1. `sq10.pds`: single 10x10 cm square piece, 1 size, no SA, no notch (checks key vs header, N=4, flag bytes, record layout).
2. `sq10_sa1.pds`: same + 1 cm SA (SA array `61`, cut vs sew relation).
3. `sq10_curve.pds`: one corner converted to a curve point (meaning of flag 0x40, curve parameters).
4. `sq10_notch.pds`, `sq10_drill.pds`, `sq10_grain.pds`, `sq10_internal.pds`: one each (record ids `69 10`, drills etc.).
5. `sq10_2sizes.pds` (base first) and `sq10_3sizes_baseM.pds`: grade step order and base handling; give one vertex dx=1 only.
6. `sq10_rename.pds`, `sq10_qty2.pds`, `sq10_material.pds`: which header/anchor bytes change.
7. Same style saved twice (resave) and with a different file name: does KEY change (derivation).
8. A style with HALF=OPEN or a different mirror setting.

## 10. REA log (what the reverse-engineering MCP contributed)
Nothing material. `F:\optitex` (the only linked folder) turned out to be a copy of the PatternForge repo itself
(`src/`, `docs/`, `web/node_modules/`): no Optitex install, DLLs or PDS files were present, so there was no
loader to decompile, and the samples were never staged to the PC. All results come from Python/Rust analysis:
tag/length regularities in the hex, XOR key found from `c4 05 24 60`/`c4 05 a4 5f` differing by exactly the bits of 1.0f,
then validation against the XML and MARKER svg.
