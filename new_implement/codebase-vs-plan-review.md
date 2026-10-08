# Codebase review against the build plan

Reviewed 8 Oct 2026. Folder: `F:\Garment-PatternMaker-Codex` (read only, nothing changed).
Plan: `software-plan/garment-pattern-app-build-plan.md` (identical copy in the folder at `new_implement/`).

## Verdict

**Yes, with conditions.** If Claude Code follows the plan, it can build an app where a user uploads a measurement Excel file plus one or more images, gets a complete graded pattern set, sees it in a 2D workspace, and exports a DXF that Optitex opens. That applies to the garment families the app has drafting blocks for (shirt, then pant in version 1).

**No** to "everything Optitex Pattern Design Software does", for three reasons the plan already states:

1. Optitex is a manual CAD tool, so a person can draw any garment in it. This app can only generate garment families it has a block for. Each new family (tee, skirt, dress, jacket) is a few weeks of work plus a pattern maker's review.
2. The image picks the style. It cannot set the sizes. Accuracy comes from the Excel measurements and the blocks.
3. Native `.PDS` export is not realistic. DXF-AAMA/ASTM plus a `.RUL` grade file is the route, and only a person with Optitex can confirm the import works.

The existing code is a real head start. It is a working, tested demo of the same pipeline for one shirt. But the plan's milestone prompts assume a brand-new project. They have to be rewritten to extend this codebase, or Claude Code will build a second app next to the first one.

## What the codebase is

| Item | Finding |
| --- | --- |
| Name | Garment Pattern Maker V5, partly extended toward a "V6" Optitex-style CAD suite |
| Stack | Python 3.12 FastAPI + SQLite backend (`backend/app`, ~9,900 lines), React 19 + Vite + TypeScript frontend (`frontend/src`, ~2,300 lines), ~6,600 lines of backend tests, Vitest and Playwright tests |
| Architecture | Ports and adapters: `api/` → `application/` → `domain/` + `infrastructure/`. Every project is one JSON document with an audit trail and a state machine |
| Specs | 118 spec files in `markdown/`, plus its own V6 plan `Follow/plan.md` (phases P0 to P5) |
| History | 45 commits. P0 (clean-up) and P1-01 to P1-10 (typed pattern model, command bus, draft, modify and garment tools) are done. Last commit: DXF export matches the preview |
| Demo data | Style 1078983: `Book2(4).xlsx` (full shirt chart S to 3XL) and tech pack PDF. **Not** the plan's 1078375, CL1086464 or 1074664 files |
| Status | Its own README calls it a "working demo application, not a production-certified garment CAD system". The pytest cache shows 5 tests failing at the last recorded run (I did not re-run them) |

## Milestone by milestone

| Plan milestone | Already in the code | Still missing |
| --- | --- | --- |
| **M0** Skeleton, test data, PDS reader | FastAPI + React app, SQLite, Dockerfile, Render and DigitalOcean deploy files, pytest/Vitest/Playwright, golden fixtures for 1078983 | Optitex PDS XML reader; the plan's test files (1078375, 1074664, CL1086464) in a test-data folder |
| **M1** Excel import | Strong base: `infrastructure/parsers.py` reads formulas **and** cached values with cell provenance; mapping status, unit confirmation, Missing Information flow, manual edits with undo | It only works for the demo workbook. Size headers must be exactly S, M, L, XL, XXL, 3XL (`domain/catalog.py`), and rows are mapped by 35 client-specific codes in column A (`catalog_source_codes.py`). CL1086464 (XS to XXL, free-text POM names) would not import. Needs a generic table finder, any size labels and a synonym mapping |
| **M2** DXF export for Optitex | `infrastructure/dxf_export.py` writes a 1:1 AutoCAD DXF with ezdxf: cut, sew, grain, notch and label layers, units set, 10 cm test square | Not AAMA/ASTM: named layers instead of AAMA numbers (1, 4, 6, 7, 14...), notches as points, R2010 format, one size only, no grade points and no `.RUL`. No DXF import. No round-trip test. Never opened in Optitex |
| **M3** Shirt block and viewer | `domain/drafting.py` drafts an 8-piece **long-sleeve** shirt (front, back, yoke, sleeve, collar, stand, cuff, sleeve placket) from 21 measurements, with validation and seam warnings. Canvas with pan, zoom, fit and piece selection | Labelled "demo profile, not a client block": curves are sampled polylines, back neck drop fixed at 2 cm, seam allowance 0 by default, sleeve cap mismatch shown as a warning. No short-sleeve option, no named points, no comparison with an Optitex pattern. No measure tool or layer toggles in the UI |
| **M4** Grading | Re-drafts every size S to 3XL and shows overlays | No grade rules derived from named points, no `.RUL`, no all-sizes DXF, no per-size area check against PDS values. The V6 typed model supports grade-rule refs, but nothing uses them yet |
| **M5** Pant block, shrinkage, image analysis | Nothing | All of it. There is no image upload or vision step anywhere. The AI assistant is text only (an offline local provider; Gemini and Groq were chosen on 1 Oct 2026 but are not wired for images) |
| **M6** Marker nesting | Working marker: mixed sizes, quantities, fabric width, spacing, utilization %, SVG/PDF export, overlap and bounds checks | It is a row packer on bounding boxes (`marker_pack.py`), capped at 20 garments, no 180° rotation, no no-fit-polygon nesting, no DXF marker. Efficiency will sit well below Optitex (the demo gets about 69%) |
| **M7** Workspace and editing tools | Pages for Dashboard, Measurements, Pattern Studio, Grading, Marker, Validation and Export; keyboard access; accessibility tests. Backend has typed CAD tools (point, line, curve, offset, move, rotate, mirror, split, join, trim, smooth, dart, pleat, slash-spread, fold) with 100-step undo | The frontend never calls the CAD tools (no `/styles` calls in `frontend/src`), so there is no point, curve, dart or pleat editing on screen. No POM check table, size table or grade-nest toggle as the plan describes |
| **M8 to M9** 3D | Nothing | All of it (deferred anyway) |

Rough read: about half the work of M0, M1, M4, M6 and M7 exists, and less of M2 and M3. M5 and the image step have not started. The hardest parts left are the ones that decide "can Optitex open it" and "is it accurate": AAMA DXF + RUL, calibrated blocks, and the pant block.

## What the plan needs to cover for this codebase

1. **Build on this repo, not a new monorepo.** The M0 and M7 prompts say to create `/api` and `/web`, Docker Compose, PostgreSQL and a fresh CLAUDE.md. That clashes with the existing `backend/`, `frontend/`, SQLite and CLAUDE.md. Add a "Starting point" section that maps each milestone to the existing modules, and rewrite the prompts to say "extend `infrastructure/dxf_export.py`", "generalise `parsers.py`", and so on.
2. **Pick one governing plan.** The repo already has `Follow/plan.md` (V6, P0 to P5, which is a much bigger Optitex-parity scope including multi-user, editions and cut planning), and its CLAUDE.md tells Claude Code to follow it and the `markdown/` spec pack. With two plans, Claude Code will follow whichever CLAUDE.md points at. Recommendation: make the new build plan govern, and pull in only these V6 steps as implementation details: P1-11 (measure and walk seams), P1-18 (any size range, editable POM chart), P1-19 (grade rules), P1-22 (DXF-AAMA/ASTM), P2-01 (block template registry), P3-03 (no-fit-polygon nesting).
3. **Remove the hard-coding before anything else.** Fixed sizes S to 3XL, the 35-code mapping and the single `demo_v1` profile block every other milestone.
4. **Join the two pattern models.** V5 drafting outputs polygon dicts; the V6 model (`domain/pattern/`) has Bézier curves, point ids, per-edge seam allowance and grade-rule refs. Blocks should output the V6 model with named points, since the plan's grade-rule derivation and RUL export need named points.
5. **Add the image path explicitly.** Upload, vision call, editable style options. The plan says Claude vision; the repo decided Gemini and Groq on 1 Oct 2026. That is a choice for you.
6. **Test data.** Put 1078375, 1074664 and CL1086464 into the repo's test data. The existing 1078983 workbook is useful too: it is the only full shirt measurement chart you have, though it has no Optitex pattern to compare against.
7. **UI direction.** The repo's CLAUDE.md says to reproduce a fixed reference screenshot (REF-004) pixel for pixel. The plan says "our own clean design". Update CLAUDE.md so the two agree.
8. **Housekeeping.** Fix the 5 failing tests first, commit or drop the uncommitted README change, and keep `.env` and `sshkey.md` out of anything shared (`.env` is git-ignored; `sshkey.md` is not listed in `.gitignore`).

## Risks

- **Optitex import is unproven.** No file from this app has been opened in Optitex yet. Do the M2 manual test early, because it decides whether the whole export route works.
- **Accuracy is uncalibrated.** The current shirt is explicitly a demo block. Matching the plan's targets (areas within 3%, seams within 0.1 cm) needs calibrated blocks and a pattern maker's review.
- **Scope creep.** `Follow/plan.md` covers multi-user, editions, plotters, cut planning and 3D. Following it would delay the version 1 you agreed on (shirt and pant, 2D, markers).
- **Repo rules slow edits.** A 100-line file limit, one commit per step and the spec-pack task log are good discipline but add overhead to every change.

## Recommended next step

1. Add a "Starting from the existing codebase" section to the build plan (the mapping above), and point the repo's CLAUDE.md at it.
2. First coding round: fix the failing tests, then M0 + M1 on this repo (PDS XML reader, generic Excel import that passes the CL1086464 test).
3. Second round: M2, upgrading `dxf_export.py` to AAMA layers plus `.RUL`, and open the result in Optitex by hand. If that import works, the rest of the plan is straightforward engineering.
