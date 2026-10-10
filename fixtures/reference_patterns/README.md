# Build-plan reference patterns (M0, T125)

Client source files that the build plan's acceptance tests run against. They were copied byte for byte on 2026-10-08. **Never edit, re-save or regenerate them.** `backend/tests/test_reference_fixtures.py` checks the hashes below.

| File | Original name | SHA-256 | Role |
|---|---|---|---|
| `1078375.PDS` | `1078375- Men Regular SS Shirt.PDS` | `3bb70849a5567db409c55b4a74588a7b2074df78e54d55ea1eb14342538ba347` | REF-006: Optitex 21.4 shirt; sizes S–3XL, base L, 7 pieces, SUM_AREA L 1.4262 m² |
| `1074664.PDS` | `1074664 - CROSS PKT PANT.PDS` | `deae727f203f70a9570d2668a2c858edd7a8c27fa38bcf2ab1b3ea5bd7ab7e1d` | REF-008: Optitex pant; sizes XS–XL, base S, 7 pieces, SUM_AREA S 1.8339 m² |
| `CL1086464.xlsx` | `CL1086464 pant folder summer.xlsx` | `34c8e8e9a9311905567c007c0538cffc1a6dd96dc5a302f1f4ddc68253596993` | REF-007: pant measurement chart (M1, T126) |
| `1078375.pdf` | `1078375.pdf` | `ea2d3f7a37847bd861b09671f2d685965048e635966c1d192db6f11b637f48e5` | Shirt tech pack; page 1 flats classified by `style_detect` (T132). **Local only, gitignored** |
| `CL1086464.pdf` | `CL1086464.pdf` | `03e6344dc8f17f0668e6a77bce96c063fb375b86c8b9b4608c24a5481b295ff2` | Pant tech pack; page 1 flats classified by `style_detect` (T132). **Local only, gitignored** |

## What `read_pds` uses from the PDS files

Only the readable XML from `<STYLE>` to `</STYLE>` is parsed. The roughly 68 KB of binary after it holds the graded geometry in an undocumented format, and it is never read or written.

- `UNITS`: lengths in cm, areas in m².
- `SIZES_TABLE`: per-size totals and `BASE_SIZE`. Σ (piece AREA × QUANTITY) = SUM_AREA.
- `PIECE`:
  - `QUANTITY`
  - `HALF=CLOSE`, meaning the piece is cut on the fold
  - `NESTING_ENABLES ROTATION`
  - per-size `GEOM_INFO`: bbox, area and perimeter, for both cut and sew
- `MARKER/VIEW/svg`: the base-size outlines in 0.01 cm units with y pointing down, drawn in PIECE order. Pieces cut on the fold are drawn as two mirrored halves plus a fold line. Colour legend:
  - `#FFBE46` polygon: cut line
  - `#000000` path: sew line
  - `#FF6633` path: fold line
  - `#0000FF` path: notch
  - `#CCCC33` polygon: marker cloth (ignored)

The pant file is named 1074664, but its internal style `NAME` is `1079077- CROSS PKT PANT`. The file is kept exactly as received.

The two tech-pack PDFs are not committed: the repository is public and they hold the client's designs, people and bill of materials (owner, 2026-10-11). Copy them from `reference/` to run the T132 tests that need them; the tests skip without them.

The PDS `FILENAME` element holds the client's original local folder path. The repository is public, and committing these files was the owner's decision (2026-10-08).
