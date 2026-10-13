# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Garment Pattern Maker: a FastAPI + SQLite backend and React 19 + Vite frontend. Today it takes a shirt measurement workbook (XLSX) and tech pack (PDF), drafts an eight-piece demo shirt pattern, regenerates it for sizes S–3XL, nests a fabric marker, and exports SVG/PDF/JSON/AutoCAD DXF. It is being extended under the **master build spec** (below) into an app that turns a measurement chart into a complete graded shirt or pant pattern set, exported as DXF-AAMA/ASTM + `.RUL` that loads in Optitex. It is not production-certified CAD. The goal is that every pattern it generates opens **100 % accurately in Optitex PDS** (Pattern Design Software, v21.4, the client's CAD). That covers piece names, quantities, fold, grain, sew and cut lines, notches, grading, and areas and perimeters that agree with Optitex's own numbers (see "Client reference files and Optitex PDS"). Never invent drafting, grading or manufacturing rules that the sources don't supply. Missing inputs must go through the requirements / Missing Information flow and must never be guessed.

## Governing plan (since 2026-10-11)

1. **`markdown/MASTER.md`, section "START HERE"** decides scope and order. Scope is locked to: chart → pattern for every size → DXF-AAMA + `.RUL` that loads in Optitex PDS 21.4. Shirt goes first, then pant. Path: T140 → T141 → T142 → T143 → T147 → T144 → T145 → T146 (shirt export + Optitex check) → T133 → T134 → T146 (pant). Marker nesting (T135), workspace polish (T136) and 3D are DEFERRED: their code stays, but don't work on them.
2. **`new_implement/MASTER_BUILD_SPEC.md`** (pack copy `markdown/docs/127_MASTER_BUILD_SPEC.md`) holds the facts, the rules, the acceptance numbers (§7) and the gates (§8).
3. `markdown/docs/124_BUILD_PLAN_STARTING_POINT.md` maps milestones to modules.

The 2026-10-08 build plan, its review and `Follow/plan.md` are history; they survive only in git.

**Extend this repo; never start a second app.** Older plan prompts were written for a blank project. Where they conflict with this repo, this repo wins:

| Plan says | Do instead |
|---|---|
| Monorepo `/api` + `/web`, Docker Compose, PostgreSQL, Redis, Arq/Celery | Keep `backend/` + `frontend/`, SQLite, the existing `Dockerfile`; run nesting off the request path without new infrastructure |
| Paste the plan's CLAUDE.md at the repo root | Don't. Its rules on naming points, test-first work, seam matching, AAMA layers, no `.PDS` writing and no double ease apply. Its paths, `make` commands and stack do not |
| Internal unit millimetres | Keep cm, quantized to 1e-6 (`tolerances.py`); convert at import/export |
| Claude vision for `style_detect` | Gemini vision behind `AIProvider` (see AI providers) |
| `/testdata` | `fixtures/` (tracked); never edit golden files |
| `/api/importers/pom_excel.py`, `/api/export/dxf_aama.py`, … | Generalize `infrastructure/parsers.py`, `domain/catalog.py`, `catalog_source_codes.py`; upgrade `infrastructure/dxf_export.py`; blocks via a registry emitting the `domain/pattern/` model with named points |
| React 18, Zustand, Mantine/shadcn | Keep React 19, `useAppController.ts`, `api.ts` and the existing tokens/components |

Only a person with Optitex can confirm an import, so record it in MASTER as external evidence and never claim it. Until then, say "Optitex import not yet verified".

## Environment & commands

The Python env is Conda `patter-codex` (Python 3.12), created from `environment.yml`, which installs `-e ./backend[dev]`. Frontend dependencies live in `frontend/` and need Node 22.12+ (Vitest 5 and jest-dom 7 require it).

```bash
# Backend tests (from repo root)
conda run -n patter-codex python -m pytest backend/tests -c backend/pyproject.toml
conda run -n patter-codex python -m pytest backend/tests/test_workflow.py -c backend/pyproject.toml   # single file
conda run -n patter-codex python -m pytest backend/tests -c backend/pyproject.toml -k "marker"        # by name

# Lint / types (from backend/)
conda run -n patter-codex python -m ruff check app tests      # line-length 110
conda run -n patter-codex python -m mypy app

# Frontend (from frontend/)
npm test                          # vitest (jsdom), *.test.ts(x) beside sources in src/
npx vitest run src/download.test.ts   # single test file
npm run build                     # tsc --noEmit + vite build -> frontend/dist
npm run test:e2e                  # Playwright; starts scripts/e2e_server.py on :8765 with a temp DB

# Run the app
cd backend && python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000   # serves API + built frontend/dist
cd frontend && npm run dev        # :5173, proxies /api -> :8000
```

- Backend tests read the demo sources from `references/` (for example, `conftest.py` loads `references/Book2(4).xlsx`). `references/` and `markdown/` are gitignored, so those tests fail on a clean clone that lacks them.
- Playwright runs at a fixed viewport of 1536×1024 and resolves snapshots to `../references/ui/`. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` if Chromium lives outside Playwright's cache.
- WSL: if Vite reports a missing `@rollup/rollup-linux-x64-gnu`, delete `node_modules` and run `npm ci --include=optional`. Never reuse a `node_modules` directory installed from Windows.
- Deploy: the multi-stage `Dockerfile` builds the SPA and serves it from uvicorn (`render.yaml` and `.do/app.yaml`). `/health` is the health check. `DATABASE_URL` defaults to `sqlite:///garment.db`, relative to `backend/`.

## Client reference files and Optitex PDS

`reference/` (Windows: `F:\Garment-PatternMaker-Codex\reference\`; gitignored) holds the client's (COLIN'S) original files. They are the **source of truth**:
- `1078375- Men Regular SS Shirt.PDS`: the Optitex shirt. Sizes S–3XL, base L, 7 pieces, SUM_AREA L 1.4262 m².
- `1078375.pdf`: the shirt tech pack (placket 3.5 cm, 2 cm hems, topstitch widths). **It has no measurement chart.**
- `1074664 - CROSS PKT PANT.PDS`: the pant reference. Sizes XS–XL, base S, SUM_AREA S 1.8339 m².
- `CL1086464 pant folder summer.xlsx`: the pant POM chart, XS–XXL, base S.
- `CL1086464.pdf`: the pant tech pack (100 % linen, −5 % warp and weft).
- The owner's explainer image.

This folder is not `references/`, which holds the V5 demo sources and UI PNGs. Never edit or re-save these files. Tests use the byte-for-byte copies in `fixtures/reference_patterns/`; their sha256 hashes are checked by `test_reference_fixtures.py`.

**PDS format** (read-only, `infrastructure/pds/`):
- The readable XML `<STYLE>` section holds:
  - `SIZES_TABLE`, with `BASE_SIZE` and the SUM_* totals
  - `PIECE`: quantity, `HALF=CLOSE` (cut on fold), rotation, and per-size `GEOM_INFO` (bbox, area, perimeter, sew area, sew perimeter)
  - `MARKER/VIEW/svg`: base-size outlines in 0.01 cm units with y pointing down. The colour legend is in `fixtures/reference_patterns/README.md`.
- About 68 KB of undocumented binary follows, holding the graded geometry. It is never read or written. **Never write `.PDS`.**

**Route into Optitex:** DXF-AAMA/ASTM + `.RUL` (`infrastructure/aama/`). Never claim Optitex compatibility until a person with Optitex has opened the file and the result is recorded as external evidence in MASTER.

**Accuracy rules:**
- Take values verbatim from the sources. Keep the 1e-6 cm quantization and never re-round.
- Check outlines against the PDS: area within 0.5 % and bbox within 0.1 cm (`test_pds_outlines.py`). Also check against the acceptance numbers in the master build spec (§7).
- Facts measured from the PDS:
  - Notches are 0.7 cm slits from the sew line.
  - Per-edge seam allowances are in `domain/data/finishing.json`, with their evidence. The PDS values win over the build plan's generic table.
- The PDS has no grain lines, no per-point grade rules and no explicit allowance numbers, and the shirt has no POM chart. These go through Missing Information or a question to the user. Never guess them.

## Architecture

The backend (`backend/app/`) uses ports/adapters layering. Dependencies point inward.

- `api/`: `main.py:create_app(database_url, *, ai_provider)` wires `Repository` → `Service` → routers. It also maps exceptions to a uniform `{code, message, details, correlation_id}` error body:
  - `NotReady` → 409
  - `ValueError` → 400 (the message text picks the code)
  - `KeyError` → 404
  - `AssistantFailure` → its own status

  `routes.py` composes the per-area routers under `/api/v1`. Built `frontend/dist` is mounted at `/`.
- `application/`: use cases. `service.py:Service` is the facade the routes call. Each project is one JSON document with `measurements`, `documents`, `resolutions`, `pattern`, `grades`, `marker`, `audit`, `state`, `transitions` and undo/redo. `pattern_workflow.py` handles generate, grade (full per-size regeneration, not delta grading) and nest. `requirements.py` and `readiness.py` gate every operation. `state.py:ALLOWED` is the explicit project state machine (`CREATED → … → EXPORT_READY → DEMO_COMPLETE`). Every transition is recorded.
- `domain/`: pure geometry and drafting. `drafting.draft(values, size, profile)`, the shirt piece set, the drafting profiles (`demo_v1`) and centralized `tolerances.py`.
- `infrastructure/`: adapters:
  - Parsers: `openpyxl` for XLSX (with formula provenance) and `pdfplumber` for PDF.
  - Geometry: `shapely`-based validation and seam allowance.
  - Marker: nesting and search.
  - Exports: `reportlab` for PDF, plus SVG.
  - `repository.py` and `migrations.py`: SQLite. It keeps a `projects` JSON snapshot table plus additive normalized projection tables and the V6 `styles` table (schema v4, `LATEST_VERSION` in `migrations.py`). Foreign keys are on.
  - The local offline AI provider.
- V6 CAD layer (`application/cad/`, `domain/pattern/`): the new typed model, separate from the V5 dict pieces.
  - `domain/pattern/`: a `Style` holds sizes → lazily decoded `SizePieces` of typed `Piece`s (points, Line/CubicBezier/Arc segments referencing point ids; Bézier handles are offsets from their end point, arcs use a DXF bulge). Coordinates quantize to 1e-6; JSON is canonical (`canonical.py`) and digested.
  - Every edit is a `Command` built by a `Registry` and run by `CommandBus.dispatch` (`bus.py`), which records a content-addressed `History` (100 steps across undo+redo). Draft tools live in `tools_draft/`, modify tools in `tools_modify/`, wired in `style_commands.py`; geometry stays in pure `domain/pattern/` functions.
  - `guard.py` re-validates only changed pieces (outline, then Shapely cut outline) and raises `GeometryInvalid` → 422 `GEOMETRY_INVALID`. `StyleRepository` uses optimistic concurrency → 409 `STYLE_CONFLICT`.
  - Routes: `api/cad_routes.py` under `/api/v1/styles` (create from project, get, piece detail, piece/style commands, undo, redo). V5 project undo/redo also runs through the bus (`legacy_commands.py`).
- `ports/`: protocols (`AIProvider`, `DocumentClassifier`, `AttributeExtractor`). AI proposals are validated action envelopes that need explicit confirmation before a deterministic service dispatches them. Invalid provider output → `AI_OUTPUT_INVALID` (502); provider failure → `AI_UNAVAILABLE` (503).

The frontend (`frontend/src/`) is a flat component directory with no router. `useAppController.ts` holds app state and the current `page`. `App.tsx` switches the page panels: Project Dashboard, Measurements, Pattern Studio, Grading, Marker Nesting, Validation Center and Export. `api.ts` is the single fetch wrapper to `/api/v1`. Unsaved measurement drafts go to sessionStorage; the server is authoritative once saved.

## AI providers

All AI work uses **Google Gemini** and **Groq** (decided 2026-10-01), plugged in behind the `ports/` `AIProvider` protocol (selected in `infrastructure/provider_factory.py`).
- The keys are read from the environment: `GEMINI_API_KEY` and `GROQ_API_KEY`.
- Locally they live in the repo-root `.env`, which is gitignored and is not copied into the Docker image.
- Never write key values into `CLAUDE.md`, source, tests, fixtures, logs or commits. Deployments set them as platform secrets.

## Hard-won rules (from `.cursor/rules/`)

- **Marker downloads** (`api.ts`, `MarkerPanel.tsx`, `nestAndExport.ts`, `state.py`, `artifact_routes.py`):
  - Every browser download goes through `saveBlobAsFile`: the anchor is appended to `document.body` and removed about 1.5s later, never synchronously.
  - Never add `?size=` to marker export URLs.
  - A forbidden workflow transition must never fail an export response. `DEMO_COMPLETE` and `PATTERN_READY` must be able to reach `EXPORT_READY` / `MARKER_READY`.
- **Source upload Browse** (`SourceDropzone.tsx`, `Measurements.tsx`, `styles.css`):
  - Use a `<label class="browse-files">` that contains a transparent `<input type="file" class="browse-files-input">` stretched over it (`position:absolute; inset:0; opacity:0`).
  - Never hide the file input off-screen, with `clip`, or with `.sr-only`. Never set `pointer-events:none` on it, and never add a bare native file control.

## Specification pack (`markdown/`)

Read the START HERE section of `markdown/MASTER.md` first, then `docs/127_MASTER_BUILD_SPEC.md` and the active task's docs. Each spec file has dated update sections. The "Master build spec update (2026-10-11)" and "PDS scan findings (2026-10-11)" sections override the older "Build-plan update (2026-10-08)" sections, which in turn override older V5/V6 text. Every task follows MASTER START HERE §4:
1. RED tests first, using the spec's §7 numbers.
2. The backend and frontend gates above, plus `python scripts/check_lines.py`.
3. Review.
4. One commit per task.
5. Mark the task COMPLETE in MASTER, with evidence and a session-log line.
6. If a value is not in the sources, stop and ask.
- Frontend work: **our own clean design** (`markdown/UI_MASTER.md`, docs 54–75, the doc 99 checklist, axe). REF-004 (`references/ui/…png`, doc 106, `UI_REFERENCE_TARGET.md`) is a historical reference, not a target. Its pixel test is not a COMPLETE gate.
- Task states are only `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`, `COMPLETE` and `DEFERRED`. `COMPLETE` needs the gates in `docs/44_DEFINITION_OF_DONE.md`. Bug fixes need a regression test that fails first.
- File length: every source and test file is ≤100 lines (hook-enforced; supersedes the spec pack's old 200/230).
