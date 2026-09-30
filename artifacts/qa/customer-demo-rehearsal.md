# Customer demo rehearsal — 2026-09-10

Status: DOCUMENTED for T038 demo-MVP release candidate (local single-user).

## Rehearsal script

1. Create demo project from Dialogs ("Open demo project").
2. Confirm units/profile/review/placket on Requirements.
3. Generate size M; open Pattern Studio; select a piece; confirm inspector dimensions.
4. Generate all six sizes; open Marker Nesting; run mixed-size S×2 + L×1.
5. Confirm prior-marker overlay and length delta when a second marker exists.
6. Export SVG/PDF/JSON and marker SVG/PDF.
7. Open Validation Center; filter Missing Information Center (blocking/non-blocking).
8. Archive project from Dashboard; restore; confirm archived filter.
9. Edit a measurement without saving; attempt navigation; confirm leave prompt.
10. Run Ask AI selected-piece prompt; dismiss without inventing geometry.

## Pass criteria (demo MVP)

- Happy-path E2E green
- REF-004 within approved 110000-pixel tolerance
- Automated axe scans with zero violations on covered screens
- No invented production drafting or pocket dimensions demonstrated as certified

## Out of scope (state honestly to the customer)

- Production-certified drafting/grading/seams
- Pixel-identical zero-diff vs marketing screenshot
- DXF/AAMA, OCR, 3D simulation, multi-user auth
