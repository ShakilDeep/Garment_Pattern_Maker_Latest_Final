# Findings from the supplied sample files (Colin's buying-house workflow)

## Files
| File | What it is |
|---|---|
| `1078375-_Men_Regular_SS_Shirt.PDS` | Optitex 21.4 style, 6 sizes (S–XXL?, base L), 7 pieces: FRT, back, back YK, CLR, BND TOP, BND IN, Sleeve |
| `1074664_-_CROSS_PKT_PANT.PDS` | Optitex 21.4 style, 5 sizes XS–XL (base S), 7 pieces: WAIST-BELT, FRONT, BACK, PKT-IN, FACING, DRAWSTRING, FACING1 |
| `1078375.pdf` | Tech pack for the shirt (A3, 6 pp): design front/back, options/colourways, technical details (top-stitch 0.2/0.5/2 cm, placket 3.5 cm), fabrics, BOM, measurements |
| `CL1086464.pdf` + `.xlsx` | Tech pack and graded spec sheet for a *different* style: women's high-rise wide-leg linen pant, sizes XS–XXL |

Note: the pant tech pack (CL1086464) does not match the pant PDS (1074664/1079077). Only the shirt PDS and shirt PDF are the same style.
**The shirt .PDS arrived corrupted**: 18,392 `EF BF BD` (UTF-8 replacement) sequences, i.e. binary bytes were text-mangled in transit. Its XML header is intact; its binary body is not. Re-send it zipped (a .zip survives upload). The pant .PDS is intact (0 replacement sequences).

## Real-world workflow shown by the documents
1. Buyer tech pack: sketches, fabric, BOM, stitching details, and a **graded finished-garment spec sheet** keyed by POM codes (e.g. 20125 half waist, 20305 half seat, 21505/21545 front/back rise, 21885 inseam, 21125 leg opening) with a tolerance column. This is garment measurement, not body measurement.
2. CAD designer builds a PDS: pieces graded across sizes, one base size.
3. Marker (nesting) on fabric width to minimise fabric use (the Bengali note in the chat).
4. Pattern pieces carry: cut outline, sew line (seam allowance), notches, grain line, internal lines, quantity, material (A/B…), mirror ("HALF"), nesting flags (rotation 180°, opposite Up/Down).

## PDS container structure (derived, pant file)
```
[ binary header ~69 B: counters, name as length-prefixed string "\x01\x04<len> <style name>" ]
[ <?xml ...?><STYLE>...</STYLE> ]   <- plain-text summary, CRLF + tabs
[ binary body ~75 KB: tagged records ]
```
XML `<STYLE>` content: `OPTITEX` version (21.4.1103.0), `UNITS`, `FILENAME`, `NAME`, `DATE`, `SIZES`, `PIECES`, `SIZES_TABLE` (per-size sums of area/perimeter/sew area/sew perimeter + `BASE_SIZE`), then per `PIECE`: NAME, CODE, UNIQUE (`U00003`…), MATERIAL, QUANTITY, optional `HALF`, `POSITION`, `NESTING_ENABLES`, and per-size `GEOM_INFO SIZE_X SIZE_Y AREA PERIMETER SEW_AREA SEW_PERIMETER` (cm / sq.m; cut vs sew values). It also holds `INTERNALS`, `NOTCH`, `T_NOTCH`, `CUT` counts and a `MARKER` with an SVG preview (cut polygon, sew path, notch lines, grain line; integer coordinates).
Binary body: tagged records (tag words such as `5f18`, `fc17`, `fd47`, `fe63`), a repeating 4-byte separator `C4 05 24 60`, shader/material records (`Shader$…`, `DefaultCloth.cgfx`), increasing int32 index runs, and small **raw-deflate** streams (RLE-like arrays). The point coordinates are NOT stored as plain float32/float64/int32 of the cm values (searched: no hits), so they are packed/compressed. Not decoded yet.

## Consequences
- The XML header gives a verifiable target: a reader can already recover name, sizes, base size, piece names/quantities and per-size bounding boxes, areas and perimeters; and the marker SVG gives the outlines at one size. This is enough to implement **import of the PDS summary + marker outlines** now.
- A writer needs the binary body decoded. Needed: minimal PDS files (one 10×10 square; then single changes), see `PDS-SAMPLES.md`, ideally as .zip. The per-size GEOM_INFO numbers can validate any decoder (area/perimeter checks).
- Product direction: add **garment spec-sheet import** (POM table, Excel), grading from the spec per size (the xlsx has XS–XXL columns), and a **marker/nesting** view, since those are the factory's actual workflow.
