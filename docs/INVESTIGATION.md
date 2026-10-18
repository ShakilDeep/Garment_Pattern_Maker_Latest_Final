# Investigation: Optitex PDS 2D/3D → PatternForge

Three parallel research passes fed the design (full text: `research-features.md`, `research-tech.md`).
Access note: Optitex help pages are login-gated; claims tagged [D] in the feature report are domain knowledge, not verified from Optitex docs.

## Features and workflow (summary)
Measurements → block/sloper → style changes (darts, SA, notches, grainlines) → grading by rules → 3D drape on an avatar with stitch definitions → marker/nesting → export (DXF AAMA/ASTM, PLT, PDF, PDS).

## What PatternForge implements
| Optitex area | PatternForge |
|---|---|
| Measurement chart import | CSV / JSON / pasted text, cm or inches, overlay on base size |
| Block drafting | Parametric bodice, skirt, trousers (Aldrich-style formulas, solved sleeve cap) |
| Point/curve editing | Drag nodes/handles, corner↔smooth, split edge, delete node, undo/redo |
| Seam allowance, notches, darts, drills, grain | In model, inspector, SVG/DXF export |
| Grading | Re-draft per size + per-node delta table, size overlay |
| 3D | Mesh + PBD cloth drape on an elliptical body (preview) |
| Export | SVG, AAMA/ASTM DXF, project JSON; PDS refused (see below) |
Not implemented: marker nesting, fit maps, true avatar scans, plt export.

## File formats and the PDS question
PDS is proprietary and undocumented. REA (the reverse-engineering toolset) was installed and works, but REA needs inputs: an Optitex install or sample `.pds` files. Neither was available, so the format could not be derived. Guessing a binary layout would produce files that Optitex rejects or corrupts, so `export_pds` returns an explicit error instead. Optitex-importable AAMA DXF is provided as the interoperable route (not verified against Optitex). To add real PDS, follow `PDS-SAMPLES.md`.

## Limits
Drafting constants are representative, not calibrated to a published block; toile before production use. The drape is a visual preview, not production cloth physics.
