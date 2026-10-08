# Garment Pattern App: Build Plan with Claude Code

Oct 7, 2026 · @careerproai

## Summary

Build a web app in 10 milestones: M0 to M7 cover 2D (roughly 10 to 14 focused weeks for one developer driving Claude Code), and M8 to M9 add 3D (another 7 to 12 weeks). The user uploads one or more garment images plus a measurement Excel file, and the app generates every pattern piece the garment needs, graded for every size. It shows them in a clean 2D workspace and exports DXF-AAMA/ASTM files that Optitex opens.

- **Main objective:** image + measurements in, a complete graded pattern set out (for a shirt: fronts, back, yoke, collar, band, sleeves; for a pant: front, back, waistband, pocket bag, facings).
- **How it gets the pieces right:** the image tells the app *what* the garment is (type and style details). The measurements tell it *how big* every piece is. Pieces are drafted from a library of parametric blocks that encode real pattern-making rules (ease, darts, crotch and armhole curves, seam and hem allowances, notches, grain). See the pattern-drafting knowledge section.
- **Look and feel:** our own clean design, with a guided flow from upload to export and a 2D workspace for reviewing and editing pieces. The feature list comes from researching the Optitex 2D/3D CAD page.
- **Accuracy target:** every POM within the buyer's tolerance (typically ±0.5 to 1 cm), matching seams equal to 0.1 cm, and areas within 3% of your Optitex reference patterns. That is "100% accurate" in the only measurable sense: the pattern hits the spec sheet.
- **Honest headline:** measurements drive accuracy, the image does not. The app cannot read seam positions or ease from a photo to the millimetre, so a pattern maker should still approve each new garment type. Writing native .PDS files is not realistic because the geometry part of the format is proprietary binary.

### Version 1 decisions (agreed 7 Oct 2026)

| Decision | Choice |
| --- | --- |
| Garment order | Men's shirt first (1078375), then pant (CL1086464, with 1074664 as reference), because both have real Optitex files to test against |
| Export format | DXF-AAMA/ASTM with a .RUL grade-rule file |
| Version 1 scope | 2D patterns and markers: milestones M0 to M7, with M6 marker nesting included, not optional |
| Deferred | 3D (M8 and M9) starts only after version 1 ships |

## Your files are the test suite

The three styles you uploaded become the app's golden tests: the app must reproduce their piece list, sizes and areas within a set tolerance. Full analysis: `/mnt/project-files/pattern-marker/analysis/file-analysis.md`.

| Test case | What it gives us | How the app uses it | Gap |
| --- | --- | --- | --- |
| Shirt 1078375 (Optitex PDS 21.4) | 7 pieces (FRT x2, back on fold, yoke x2, collar x2, band top, band in, sleeve x2), sizes S to 3XL, base L. Per-size length, width, area, perimeter. Full base-size outlines as SVG. | Ground truth for the shirt block. Per-size areas (S 1.30 to 3XL 1.68 m²) check grading. | No measurement chart in the tech pack, so measurements are derived from the pattern. |
| Pant CL1086464 (xlsx spec sheet) | Graded POM chart XS to XXL, base S: 1/2 waist 33 to 44.5, 1/2 seat 50 to 61.5, rises, thigh, knee, inseam 77 to 82, hem 2.8, waistband 5.2. Linen with -5% shrinkage. | The real Excel input for milestone 1 and the pant block. | No pattern file to compare against. |
| Pant 1074664 (Optitex PDS) | Similar wide-leg drawstring pant, XS to XL, base S, 7 pieces. Waist grade matches CL1086464 exactly. | Reference shapes and areas (S 1.83 m²) for the pant block. | Different style, so compare shape, not exact numbers. |

What we learned about the PDS format: bytes from about 75 to 21,300 are readable XML (style, sizes, per-size piece dimensions, base-size outlines in SVG at 0.01 cm units); the remaining \~68 KB is undocumented binary holding graded geometry. The app can read the XML part for testing, but should not try to write PDS.

Still missing from you: a shirt measurement chart for 1078375, fabric width, and the order size ratio (both needed only for markers).

## Required features and our UI

### Required features (researched from the Optitex 2D/3D CAD page)

To find every feature this app needs, I went through the [Optitex 2D/3D CAD page](https://optitex.com/products/2d-and-3d-cad-software/) and listed each capability it names. Each one is marked **Now** (milestones M0 to M7), **Later** (M8 and M9, the 3D phase), or **Out** (not planned, with the reason).

| Feature (as named on the Optitex page) | What our version does | Scope | Milestone or reason |
| --- | --- | --- | --- |
| Flexible, user-friendly patternmaking tools | Generate pieces from image + measurements, then edit points, curves, seams | Now | M3, M5, M7 |
| Smart 2D Design: edit multiple points at once | Multi-select points and move or scale them together | Now | M7 |
| Smart 2D Design: create, move and open darts | Dart tool: add, rotate (move) and open a dart to fullness | Now | M7 |
| Smart 2D Design: pleats, including multi-pleats | Pleat tool: knife, box and multiple pleats along a line | Now | M7 |
| Functional Grading: sizes from a base pattern | Re-draft per size plus an editable grade-rule table | Now | M4 |
| Quality and Precision: adjust, compare lengths across sizes | Seam-length compare panel and POM check table for all sizes | Now | M4, M7 |
| Open to leading standard formats; fully compatible with major CAD formats | Export DXF-AAMA/ASTM + RUL; import DXF-AAMA; read Optitex PDS XML | Now | M0, M2 |
| Works with cutters, plotters and digitizers | Plot output as HPGL/PLT and PDF tiles | Later | After M6; needs a plotter to test against |
| Marker Making Suite: marker files, cut and plot output | Marker layout with export to DXF and PLT | Now | M6 |
| Modular Auto Nesting tools | Automatic nesting with efficiency % | Now | M6 |
| Costing reports | Fabric per garment and per order from marker length | Now | M6 |
| Tech Pack Essentials: model data into customisable documents | PDF with piece list, size chart, POM check and marker summary | Later | After M7; low effort, not core |
| Accurate Fabric Simulation | Drape the 2D pieces on an avatar with fabric properties | Later | M9; the hardest feature, see risks |
| Virtual Tension Map | Colour map of stretch and pressure between cloth and avatar | Later | M9; comes free once simulation works |
| Photo Realistic Rendering, 360° with lights and shadows | Real-time 3D view with orbit, lights and shadows; not offline photoreal rendering | Later | M8 |
| Colorways and Print Placement | Apply fabric images, colourways and logos to pieces in 2D and 3D | Later | M8 |
| Multi-Stitch Tool | Define stitch types per seam; shown in 3D and listed in the tech pack | Later | M8 |
| Avatar Editor: morphs, sizes, poses | Parametric avatar sized from the size chart; a few poses | Later | M8 |
| Fabric Management Solution: measure and simulate fabric | Fabric library with weight, stretch, bending values entered by hand | Later | M9; Optitex measures fabric with a physical tester; we start with values entered by hand |
| 3D changes update the 2D pattern | Edit in 3D view writes back to 2D points | Out | Very large effort; edit in 2D and re-drape instead |
| Virtual samples graded across sizes and draped in 3D | Drape any graded size on the avatar for that size | Later | M9 |

### Our own UI

The UI is a clean design of our own, built for one job: image and measurements in, patterns out. It has two parts on one screen.

- **Guided flow (for every user):** Upload image and xlsx, Confirm measurements (mapped POM table, unmapped rows flagged), Confirm style (detected options with confidence, editable), Generate, Review (accuracy suite results), Export (DXF + RUL, PDF).
- **Workspace (for pattern makers):** piece list with quantities on the left, canvas in the centre with zoom, pan and layer toggles, properties of the selected piece or point on the right, size table and POM check table at the bottom.
- **Design basics:** React with a ready component library (Mantine or shadcn/ui), light and dark themes, cm/inch switch, keyboard shortcuts for the editing tools, usable on a 1366 px laptop screen and up.

Workspace layout (wireframe, shown as a diagram in the online plan):

```
+---------------------------------------------------------------+
| App name   File  Edit  View  Piece  Grade  Tools  Help        |
| [Upload] [Measurements] [Style] [Generate] [Review] [Export]  |
| Tools: select, point, curve, notch, dart, pleat, measure, SA  |
+-----------+-------------------------------+-------------------+
| Pieces    | Work area                     | Properties        |
| FRT x2    | grade nest, all sizes on one  | Name, quantity    |
| back x1   | piece, base size highlighted  | Fold, mirror      |
| ...       |                               | Seam allowance    |
+-----------+---------------+---------------+-------------------+
| Size table: S M L(base) XL XXL 3XL | POM check: spec vs pattern |
| Status bar: cursor position, units cm, accuracy suite result   |
+---------------------------------------------------------------+
```

The flow bar walks a new user from upload to export; the panels under it are where a pattern maker reviews and edits.

## Architecture and tech stack

A Python backend owns all geometry; the React frontend only displays and edits what the backend returns. Keeping geometry in one language means one set of tests and one source of truth for every piece.

Architecture (shown as a diagram in the online plan):

```
React web app  <-- JSON API -->  FastAPI backend (Python)
                                 pom_import -> style_detect -> blocks
                                 -> grading -> finishing -> export_dxf -> Optitex (DXF-AAMA + RUL)
                                                 finishing -> nesting (marker + efficiency %)
```

The backend runs the modules in order, top row then bottom row; only the DXF leaves the app, plus the marker from nesting.

| Layer | Choice | Why |
| --- | --- | --- |
| Backend API | Python 3.12, FastAPI, Pydantic v2 | Typed request and response models; Python has the best geometry and DXF libraries. |
| Geometry | Shapely 2, NumPy, own Bézier/spline helpers | Offsets for seam allowance, unions, areas, perimeters. |
| Excel parsing | openpyxl (reads cached formula values), pandas | The CL1086464 sheet uses formulas for graded sizes. |
| Image analysis | Claude API (vision) with a strict JSON schema, optional OpenCV for silhouette ratios | Classifies garment type and style options from photos. |
| DXF export | ezdxf, plus a small AAMA/ASTM layer writer | ezdxf writes R12-compatible DXF that AAMA readers expect. |
| Marker nesting | Sparrow or SVGnest-style no-fit-polygon heuristic, run as a background job | Open-source nesters reach good efficiency without a licence. |
| Storage | PostgreSQL (styles, sizes, jobs), files on disk or S3 (uploads, exports) | SQLite is fine for milestone 1 to 4. |
| Jobs | Arq or Celery with Redis | Nesting and vision calls can take seconds to minutes. |
| Frontend | React 18 + TypeScript + Vite, Zustand, TanStack Query | Simple state, cached API calls. |
| 2D viewer | SVG for up to \~100 pieces, Konva (canvas) if markers get large | Zoom, pan, layer toggles, size nest overlay. |
| Tests | pytest + Hypothesis (backend), Vitest + Playwright (frontend) | Golden-file tests against your PDS data. |
| Packaging | Docker Compose (api, worker, db, redis, web) | One command to run locally. |

Core data model, shared by every module: **Style** (name, garment type, base size, size list, fabric) → **Measurement** (POM code, name, value per size, tolerance) → **Piece** (name, quantity, mirrored, on fold, grain line, rotation allowed) → **Geometry** per size (sew line, cut line, internal lines, notches, drill holes, grade points with rule ids).

## Modules

Seven backend modules, each a Python package with its own tests, called in a fixed pipeline: parse, analyse, draft, grade, finish, export, nest.

### 1. Excel measurement parser (`pom_import`)

- Finds the POM table anywhere in the workbook: scans every sheet for a header row containing size labels (XS, S, M, 32, 34...) and a description column.
- Reads cached values with `openpyxl(data_only=True)` so formula-graded sizes come through; falls back to evaluating simple formulas if the cache is empty.
- Maps free-text POM names ("1/2 WAIST AT TOP EDGE", "1/2 SEAT") to canonical keys (`waist_half`, `seat_half`) using a synonym table first, then a Claude call for unknown rows, then a user confirmation screen.
- Flags half vs full measurements, units (cm or inch), tolerances, and the base size.
- Output: a `MeasurementChart` JSON. Unmapped rows stay visible so nothing is silently dropped.

### 2. Image analysis (`style_detect`)

- Sends the photos to Claude vision with a fixed JSON schema: garment type, fit, and one value per style option (collar: none/band/shirt collar CL28-like; placket width; yoke yes/no; pockets: none/side seam/patch/cross; sleeve: short/long; leg: straight/wide/tapered; waistband: fixed/elastic/drawcord).
- Optional OpenCV step gives silhouette ratios (hem width vs waist, sleeve length vs body) as soft hints only.
- Every detected option is shown to the user as an editable choice with a confidence value. The user's choice always wins.

### 3. Parametric block drafting (`blocks`)

- One Python class per block: `ShirtBlock`, `PantBlock`, later `SkirtBlock`, `TeeBlock`, `DressBlock`. Each takes canonical measurements plus ease plus style options and returns named pieces.
- Drafting follows a documented system (for example Aldrich's *Metric Pattern Cutting*): every point is computed from measurements, with curves as cubic Béziers through named control points.
- Style options are transforms on the block: add a yoke line and split, add a placket extension, add a pocket bag and facing, convert the waist to an elastic casing.
- Shirt first (matches 1078375), pant second (matches CL1086464 using 1074664 as the reference shape).

### 4. Grading (`grading`)

- Two methods, both kept: **re-draft** (run the block again with each size's measurements, simplest and exact to the chart) and **grade rules** (x/y deltas per grade point, AAMA style, needed for the DXF rule table and for editing the base size by hand).
- After re-drafting, the module derives grade rules by matching named points across sizes, so both are always in sync.
- Checks: seams that sew together keep equal length in every size (side seam front vs back, armhole vs sleeve cap within ease), and no piece self-intersects.

### 5. Pattern finishing (`finishing`)

- Seam allowance per edge (1 cm default, 2 cm hems from the 1078375 tech pack), corner types, notches, grain line, fold line, drill holes, piece labels (style, piece, size, quantity).
- Shrinkage compensation: CL1086464 linen has -5% in warp and weft, so pieces are scaled by 1/0.95 along each axis before export.

### 6. 2D viewer (frontend)

- Piece gallery per size, a nested view of all sizes on one piece (the classic grade nest), measurement table beside it, layer toggles (cut, sew, notches, grain, labels).
- Point and curve editing on the base size, with live re-grade.
- Measure tool: click two points or a seam to get its length.

### 7. Export (`export_dxf`) and marker (`nesting`)

- See the next section for DXF.
- Marker: input fabric width, size ratio, piece quantities, rotation rules (1078375 allows 180° only, grain along length). Output: marker length, efficiency % = piece area / (width × length), and a DXF or PDF of the layout.

## Pattern-drafting knowledge the app must encode

Accuracy comes from encoding how a pattern maker drafts, not from the image. The most important rule: a buyer's spec sheet (like CL1086464) gives **finished garment** measurements, with ease already included. So the blocks draft straight to the finished POMs and add only seam and hem allowances. They must never add body ease a second time.

### Pattern maker's order of work (the pipeline mirrors it)

1. Read the spec: POMs, tolerances, base size, fabric, shrinkage, construction details from the tech pack.
2. Choose a block for the garment family and fit (regular shirt, wide-leg pant).
3. Apply style changes: yoke split, placket, pleats, darts moved or converted, pockets, waistband type.
4. True the pattern: matching seams equal ("walking" the seams), curves smooth across seams (neck at shoulder, armhole at side seam, crotch at inseam), corners square where seams meet a fold.
5. Add seam and hem allowances, notches, grain line, labels.
6. Grade to every size, then re-check steps 4 and 5 in each size.
7. Compensate shrinkage (CL1086464 linen: scale by 1 / 0.95 in both directions).

### Rules by garment type (first two are the first blocks)

| Garment | Pieces it must produce | Drafting rules to encode | Checks |
| --- | --- | --- | --- |
| Shirt (1078375) | Front L/R with placket, back on fold, yoke outer + inner, collar, collar band, sleeve | Yoke seam a few cm below the shoulder line, shoulder moved forward into the yoke; armhole depth and across-back from chest and shoulder POMs; low, flat sleeve cap with almost no cap ease (a shirt sleeve, unlike a jacket); collar band length = neckline + button overlap; band and collar curved up at CF so the collar sits close to the neck | Collar band = neckline ±0.2 cm; sleeve cap = armhole + 0 to 1 cm; front and back side seams equal; chest, length, sleeve and cuff POMs within tolerance |
| Pant (CL1086464) | Front L/R, back L/R, waistband (elastic casing + drawcord), side pocket bag, pocket facing | Back crotch extension longer than front (roughly 1.5 to 2 times); back crotch seam slanted and back waist raised at centre back; front and back rise from the spec; grain line on the crease, centred at knee and hem; wide leg so knee and hem nearly equal; elastic waistband cut to the extended waist, gathered to relaxed waist | Front and back inseams equal; side seams equal; 1/2 waist (extended), 1/2 seat, thigh, rises, inseam, leg opening within tolerance |
| T-shirt (later) | Front, back, sleeve, neck rib | Knit: little or negative ease, shallow cap, rib cut shorter than neckline (about 85 to 90%) | Rib length ratio, side seams equal |
| Skirt (later) | Front, back, waistband | Waist darts sized from waist-to-hip difference, hip curve, hem sweep | Darts sum to waist/hip difference |
| Dress (later) | Bodice from block + skirt | Bust dart control, waist seam match | Waist seam lengths equal |

### Rules for every piece

| Rule | Default | Source of the default |
| --- | --- | --- |
| Body seam allowance | 1 cm | Common industrial standard |
| Neck, collar, facings, tight curves | 0.6 to 0.7 cm | Narrow on curves to avoid clipping |
| Hems | 2 cm shirt hem and sleeve hem | 1078375 tech pack topstitch |
| Fold and mirror edges | No allowance, fold line drawn | Optitex fold pieces in your PDS |
| Notches | On the sew line, 0.3 to 0.5 cm deep, matching pairs on both seams | AAMA layer 4 |
| Seam corners | Mitred or squared so allowance lies flat when pressed | Pattern-making practice |
| Grain line | Parallel to CF/CB (shirt) or crease (pant); along fabric length | 1078375: grain along X, 180° rotation only |
| Seam truing | Matching seams equal within 0.1 cm in every size | Pattern-making practice |

The values above are starting points for a pattern maker to confirm. Each one goes into a settings file, so a factory can change it without touching code.

### Reference material to give Claude Code

- Winifred Aldrich, *Metric Pattern Cutting for Menswear* and *for Women's Wear* (standard UK drafting systems, metric).
- [FreeSewing](https://freesewing.eu/docs/designs/): open-source parametric patterns, including Simon (button-down shirt), Titan (trouser block), Brian (body block) and Sarah (skirt block). Study its drafting logic; check the licence before copying code.
- Your own Optitex patterns (1078375, 1074664). These are the best reference, because they show how your factory actually drafts.

## Export to Optitex

Export DXF in the AAMA / ASTM D6673 layout: Optitex PDS imports it directly (File, Import, DXF AAMA/ASTM), and every other CAD system (Gerber, Lectra, Tukatech) reads it too.

- **Two export modes:** (a) base size plus a `.RUL` grade-rule file, which Optitex turns back into a graded pattern you can edit; (b) one DXF with every size drawn as separate blocks, the safer fallback if rule import gives trouble.
- **Layer map** (standard AAMA numbering, verify against the spec while building): 1 cut line, 2 turn points, 3 curve points, 4 notches, 5 grade reference, 6 mirror/fold line, 7 grain line, 8 internal lines, 11 internal cutouts, 13 drill holes, 14 sew line, 15 annotation text.
- **Per-piece text:** piece name, size, quantity, style number, category, so Optitex fills its piece table on import.
- **Units:** write metric (cm or mm) with the unit flag set; your PDS files use cm.
- **Acceptance check:** import the exported 1078375 shirt into Optitex and compare piece count, sizes and the per-size areas stored in the original PDS. Do this by hand once per milestone; there is no free Optitex for automated tests.

Why not native PDS: the XML header is readable, but piece geometry for graded sizes lives in an undocumented \~68 KB binary block. Writing it would need reverse engineering, may break with each Optitex release, and may conflict with the licence. The app should **read** the PDS XML (for test data and for importing a client's existing base pattern) and **write** DXF.

## Milestones and acceptance tests

Build in this order so that each milestone ships something you can open in Optitex. Do not start a milestone until the previous one's tests pass.

**M0. Skeleton and test data (2 to 3 days).** Monorepo, Docker Compose, CI, and a `testdata/` folder holding your files plus a PDS XML reader.

- Test: `pytest` extracts from the 1078375 PDS 6 sizes, base L, 7 pieces, and SUM\_AREA L = 1.4262 m²; from 1074664, 5 sizes, base S, 1.8339 m².
- Test: the base-size SVG outlines convert to polygons whose areas match the PDS piece areas within 0.5%.

**M1. Excel import (3 to 4 days).** `pom_import` plus an upload screen with a mapping table.

- Test: the CL1086464 xlsx yields XS to XXL with base S, 1/2 waist 33/35/37/39.5/42/44.5, inseam 77 to 82, every POM mapped or listed as unmapped.
- Test: a re-saved copy with no cached formula values still parses.

**M2. DXF export round-trip (3 to 4 days), before any drafting.** Export the PDS base outlines from M0 as AAMA DXF.

- Test: ezdxf re-reads the file, layers 1, 4, 6, 7 and 14 exist, each piece's area matches within 0.5%.
- Manual gate: the file opens in Optitex with correct piece names, fold lines and grain.

**M3. Shirt block and viewer (2 to 3 weeks).** `ShirtBlock` with yoke, placket, collar and band, short sleeve; React viewer with layers and measure tool.

- Test: with measurements derived from 1078375 size L, each drafted piece's width and length are within 1.5 cm and area within 3% of the PDS piece.
- Test: collar sew line equals neckline length within 0.3 cm; armhole vs sleeve cap ease within the set range.

**M4. Grading (1 to 2 weeks).** Re-draft per size, derive grade rules, export base + RUL and all-sizes DXF.

- Test: shirt SUM\_AREA per size within 3% of the PDS values (S 1.2965 to 3XL 1.6781 m²).
- Test: matching seams equal in every size; no self-intersections (Hypothesis fuzzing of measurements).
- Manual gate: graded import in Optitex shows all 6 sizes nested correctly.

**M5. Pant block and image analysis (2 to 3 weeks).** `PantBlock` (wide leg, elastic/drawcord waistband, side pocket), shrinkage, `style_detect`.

- Test: CL1086464 measurements produce front, back, waistband, pocket bag and facing; drafted 1/2 waist, 1/2 seat, rises and inseam match the chart within its tolerances (1 cm / 0.5 cm) before shrinkage.
- Test: total area per size is within 8% of the 1074664 values (similar, not identical style).
- Test: the tech-pack sketches for 1078375 and CL1086464 are classified as shirt (collar, yoke, short sleeve) and pant (wide leg, elastic waist, side pockets).

**M6. Marker nesting (1 to 2 weeks, part of version 1).** Needs fabric width and size ratio from you.

- Test: 1078375 at a stated width and ratio gives a marker, efficiency % reported, no overlaps, rotation limited to 180°.
- Benchmark: compare efficiency with an Optitex marker of the same order; target within 3 points.

**M7. Full workspace and 2D editing tools (2 to 3 weeks, built by the frontend sub-agent alongside M3 to M5).** The full UI from the "Our own UI" section.

- Test (Playwright): upload the CL1086464 xlsx and a sketch, run the flow bar to Export, and download a DXF without leaving the workspace.
- Test: the piece strip lists every piece with its quantity; selecting a piece fills the properties panel; toggling sizes in the size table shows the grade nest.
- Test: moving a base-size point re-grades all sizes and updates the POM check table live.
- Gate: a pattern maker who uses Optitex can do the full flow without instructions. Record what they get stuck on.

M7 also delivers the Smart 2D Design tools from the parity list: multi-point select and move, dart create/move/open, and knife, box and multi-pleats.

- Test: opening a 2 cm waist dart on the pant back adds 2 cm at the hem and keeps the waist seam length; a 3-pleat insert adds exactly the set depth.

**M8. 3D viewer, avatar and colourways (3 to 4 weeks, deferred until after version 1).** three.js viewer, parametric avatar sized from the size chart, fabric images and colourways, logo and print placement, stitch types per seam. Pieces are shown wrapped around the avatar without physics.

- Test: the avatar for size L matches the body measurements implied by the 1078375 chart within 1 cm at chest, waist and hip.
- Test: a print placed on the front piece stays in the same place on the 2D piece and in 3D.

**M9. Cloth simulation, tension map and graded 3D samples (4 to 8 weeks, research-heavy, deferred until after version 1).** Sew the pieces along their seam pairs and drape them on the avatar with a cloth solver (position-based dynamics in WebAssembly or on a server GPU); fabric library with weight, stretch and bending values; tension map; drape any graded size.

- Test: the 1078375 shirt sews closed with no unmatched seam and settles without pieces passing through the avatar.
- Test: the tension map shows the highest strain at the fitted areas when a size smaller than the avatar is draped.
- Gate: a fit technician compares the draped shirt with a photo of a real sample and records where they differ. Do not promise customers simulation accuracy until this gate passes.

### Accuracy test suite (runs on every commit from M3 on)

| Check | Pass rule | Applies to |
| --- | --- | --- |
| POM check: every spec POM measured on the drafted pattern | Within the spec's tolerance in every size (CL1086464: 1 cm on waist and seat, 0.5 cm on inseam) | All styles |
| Seam pairs (side seams, inseams, shoulder to yoke, collar to neck, sleeve to armhole) | Equal within 0.1 cm, sleeve cap ease within its set range | All sizes |
| Reference comparison with Optitex patterns | Piece width, length, area within 1.5 cm / 3% of 1078375; total area within 8% of 1074664 | Shirt, pant |
| Geometry validity | No self-intersection, closed outlines, counter-clockwise, no zero-length edges | All pieces |
| Allowance and notches | Allowance matches the settings per edge; every notch has its pair on the matching seam | All pieces |
| Grading sanity | Areas grow from size to size; grade steps match the spec's steps | All sizes |
| DXF round-trip | Re-read DXF equals internal geometry within 0.05 cm | Every export |
| Image classification | Correct garment type and options on a labelled set of at least 30 images per garment family | style\_detect |

A report page in the app shows this suite for each generated style, so the user can see exactly which checks passed before exporting.

## Running Claude Code well

Claude Code with an Opus model writes the code; you act as product owner and pattern-making expert. The loop that works: plan, write failing tests from your files, implement, check visually, commit. Select Opus with `/model` at the start of each session.

### Working loop for every milestone

1. Start in **plan mode** (Shift+Tab). Paste the milestone prompt below. Read the plan; correct any pattern-making mistakes before code is written.
2. Ask for the **tests first**, using the numbers in this document. Run them and confirm they fail.
3. Let Claude implement until the tests pass. Keep sessions to one milestone; use `/clear` between milestones so old context does not leak in.
4. **Look at the output.** Ask Claude to render each piece to PNG and open it, or run the app. Geometry that passes numeric tests can still look wrong.
5. Commit after every green test run. Use git branches per milestone so a bad direction is easy to drop.

### CLAUDE.md (put this at the repo root)

```markdown
# Garment pattern app
Python 3.12 FastAPI backend in /api, React+TS+Vite frontend in /web.
All geometry lives in /api/geometry and /api/blocks. Frontend never computes geometry.

## Units and conventions
- Internal unit: millimetres as float. Convert at import/export only.
- X = fabric length (warp, grain), Y = width. Origin bottom-left. Counter-clockwise polygons.
- Every drafted point has a name (e.g. "CF_neck", "side_waist"). Curves are cubic Beziers between named points.
- Half measurements in POM charts ("1/2 waist") are stored as half; blocks decide how to use them.

## Rules
- Test first. Golden data is in /testdata (Optitex PDS + CL1086464 xlsx). Never edit testdata.
- Never loosen a tolerance to make a test pass; ask instead.
- Seams that sew together must match in length in every size; check it in tests.
- DXF output follows AAMA/ASTM D6673 layers (see docs/dxf-layers.md).
- Do not attempt to write .PDS files.
- Spec-sheet POMs are finished garment measurements: ease is already in them. Never add body ease again.
- Every block has a docs/drafting/<garment>.md reviewed by a pattern maker before code.

## Commands
- make test        # pytest + vitest
- make render STYLE=1078375 SIZE=L   # writes PNGs to /out for visual check
- make dev         # docker compose up
```

### Sub-agents (`.claude/agents/`)

- **pattern-reviewer:** read-only. Reviews a block's drafting against the pattern-making reference and the golden numbers; reports seam mismatches and odd curves. Run after each block change.
- **dxf-validator:** runs the round-trip check (export, re-read with ezdxf, compare areas and layers) and reports differences.
- **test-writer:** turns an acceptance bullet from this plan into pytest cases before implementation starts.
- **frontend-builder:** works only in /web against the OpenAPI schema, so backend and viewer can progress in parallel.

Also add a hook in `.claude/settings.json` that runs `ruff` and the fast unit tests after every edit, so mistakes surface immediately.

### Prompts to paste

**M0:** "Read CLAUDE.md. Set up the monorepo with Docker Compose (api, web, db). Write a PDS reader in /api/importers/pds.py that parses only the XML part of an Optitex .PDS (from `<STYLE>` to `</STYLE>`): sizes, base size, pieces with quantity, fold, rotation, per-size bbox/area/perimeter, and base-size SVG outlines (units 0.01 cm; yellow polygon = cut, black path = sew, #FF6633 = fold, blue = notch). Write the tests from the M0 section of the plan first, then implement."

**M1:** "Build /api/importers/pom\_excel.py. It must find the POM table on any sheet, read cached formula values, detect size columns, base size, tolerance and half vs full measurements, and map names to canonical keys via /api/importers/pom\_synonyms.yaml. Unknown names go to an `unmapped` list. Tests first, using testdata/CL1086464.xlsx and the values in the plan. Then add an upload page in /web that shows the chart and lets the user fix mappings."

**M2:** "Write /api/export/dxf\_aama.py using ezdxf. Export pieces with cut line, sew line, notches, grain line, fold line and piece text on AAMA layers, plus a .RUL grade-rule file. Test by exporting the 1078375 base outlines from the PDS reader, re-reading the DXF, and comparing areas within 0.5%. Document the layer map in docs/dxf-layers.md."

**M3:** "Plan first, no code. Propose a ShirtBlock for a men's regular short-sleeve shirt with back yoke, 3.5 cm front placket, two-piece collar (collar + band) and set-in sleeve, drafted from named points. List the measurements it needs and how to derive them from the 1078375 PDS piece dimensions, since that style has no chart. After I approve, write tests comparing each piece with the PDS base size L, implement, and render PNGs for me to review."

**M4:** "Add grading: re-draft ShirtBlock for every size, derive per-point grade rules by name, and check seam-length matching. Add Hypothesis tests over random measurement sets. Export base+RUL and all-sizes DXF. Compare per-size total area with the PDS SUM\_AREA values within 3%."

**M5:** "Plan first. Propose a PantBlock for a high-rise wide-leg pant with elastic waistband and drawcord, side pockets, pocket bag and facing, driven by the CL1086464 chart, with -5% shrinkage compensation. Use the 1074664 PDS shapes as a visual reference only. Then add style\_detect: a Claude vision call with a strict JSON schema of style options, shown to the user as editable choices."

**M6:** "Add /api/nesting as a background job. Input: pieces per size, size ratio, fabric width, rotation rules. Output: marker length, efficiency %, layout DXF and SVG. Start with a bottom-left-fill heuristic on no-fit polygons; keep the interface so a stronger nester can replace it."

**M7:** "Build the workspace in /web following the 'Our own UI' section of the plan: tool icons, piece list on the left, canvas work area in the centre, properties panel on the right, size table and POM check table at the bottom, and a flow bar (Upload, Confirm measurements, Confirm style, Generate, Review, Export). Write Playwright tests from the M7 section first."

**Before each block (M3, M5):** "Before drafting, write docs/drafting/\<garment>.md listing every point, line and curve of the block, the measurement each comes from, and the trueing checks, using the 'Pattern-drafting knowledge' section and Aldrich as the reference. Stop and show it to me for review by a pattern maker. Then turn every check into a test in the accuracy suite."

## Risks and honest limits

| Risk or limit | Impact | What to do |
| --- | --- | --- |
| "100% accurate from an image" is not achievable | A photo shows style, not dimensions. Seam placement, ease and curve shapes cannot be measured from pixels to the millimetre, and the back of the garment is often not shown | Accuracy comes from the measurements and the blocks. The image only picks the block and options, which the user confirms. 100% is defined as passing the accuracy suite |
| Only as many garment types as blocks you build | Optitex can make any shape because a person draws it; this app can only make families it has blocks for | Start with shirt and pant, then add tee, skirt, dress by demand; keep manual point editing in the workspace |
| Drafting needs pattern-making knowledge | Claude knows standard drafting systems but can make fit mistakes (crotch curve, sleeve cap ease) | A pattern maker reviews each docs/drafting file and each block; encode their fixes as tests |
| Fit cannot be proven by numbers | Matching POMs does not guarantee a good fit on a body | Plan a physical sample for each new block before using it in production |
| Spec sheets vary between buyers | Different POM names, half vs full, inches, merged cells | Synonym table, confirmation screen, unmapped list; add every new buyer's sheet to testdata |
| DXF import quirks in Optitex | Grade rules or notches may not come through | M2 manual gate early; all-sizes DXF as fallback |
| PDS stays read-only | No native Optitex file; markers made in Optitex need the DXF imported first | Accept; DXF-AAMA is the industry exchange format |
| No 3D | 3D (M8 to M9) is the riskiest part; cloth simulation that matches a real sample takes Optitex-scale engineering | Start 3D only after the 2D accuracy suite passes; treat M9 as research with a fit-technician gate |
| No Optitex licence in CI | Optitex checks stay manual | One manual import per milestone, recorded with screenshots |
| Nesting efficiency | Simple heuristics land a few points below commercial nesters | Ship the simple nester in version 1; plug in a stronger one later |
| Vision API cost and privacy | Buyer images go to an external API | Use a business API account with no-training terms; resize images first |

Realistic outcome after M5: a tool that turns a buyer's spec sheet into a correct, graded first pattern for shirts and pants in minutes, exported to Optitex for a pattern maker to finish. That saves most of the drafting and grading time, not the pattern maker.
