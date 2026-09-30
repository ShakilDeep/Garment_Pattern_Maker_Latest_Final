# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Garment Pattern Maker V5: a local **demo** app (FastAPI + SQLite backend, React 19 + Vite frontend) that takes a shirt measurement workbook (XLSX) and tech pack (PDF). It drafts an eight-piece shirt pattern, regenerates it for sizes S–3XL, nests a fabric marker, and exports SVG/PDF/JSON. It is not production-certified CAD. Never invent drafting, grading or manufacturing rules that the sources don't supply. Missing inputs must go through the requirements / Missing Information flow and must never be guessed.

## Environment & commands

The Python env is Conda `patter-codex` (Python 3.12), created from `environment.yml`, which installs `-e ./backend[dev]`. Frontend dependencies live in `frontend/` and need Node 20+.

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
  - `repository.py` and `migrations.py`: SQLite. It keeps a `projects` JSON snapshot table plus additive normalized projection tables (schema v3). Foreign keys are on.
  - The local offline AI provider.
- `ports/`: protocols (`AIProvider`, `DocumentClassifier`, `AttributeExtractor`). AI proposals are validated action envelopes that need explicit confirmation before a deterministic service dispatches them. Invalid provider output → `AI_OUTPUT_INVALID` (502); provider failure → `AI_UNAVAILABLE` (503).

The frontend (`frontend/src/`) is a flat component directory with no router. `useAppController.ts` holds app state and the current `page`. `App.tsx` switches the page panels: Project Dashboard, Measurements, Pattern Studio, Grading, Marker Nesting, Validation Center and Export. `api.ts` is the single fetch wrapper to `/api/v1`. Unsaved measurement drafts go to sessionStorage; the server is authoritative once saved.

## Hard-won rules (from `.cursor/rules/`)

- **Marker downloads** (`api.ts`, `MarkerPanel.tsx`, `nestAndExport.ts`, `state.py`, `artifact_routes.py`):
  - Every browser download goes through `saveBlobAsFile`: the anchor is appended to `document.body` and removed about 1.5s later, never synchronously.
  - Never add `?size=` to marker export URLs.
  - A forbidden workflow transition must never fail an export response. `DEMO_COMPLETE` and `PATTERN_READY` must be able to reach `EXPORT_READY` / `MARKER_READY`.
- **Source upload Browse** (`SourceDropzone.tsx`, `Measurements.tsx`, `styles.css`):
  - Use a `<label class="browse-files">` that contains a transparent `<input type="file" class="browse-files-input">` stretched over it (`position:absolute; inset:0; opacity:0`).
  - Never hide the file input off-screen, with `clip`, or with `.sr-only`. Never set `pointer-events:none` on it, and never add a bare native file control.

## Specification pack (`markdown/`)

`markdown/MASTER.md` (the task table and session log), `AGENTS.md`, `REQUIREMENTS.md` and `docs/01–106` are the governing specs. Update `MASTER.md` at the end of a task.
- Frontend work: read `markdown/UI_REFERENCE_TARGET.md` and `markdown/docs/106_PIXEL_EXACT_UI_REFERENCE.md`, and inspect `references/ui/garment-pattern-maker-v5-ui-reference-1536x1024.png` (REF-004). Reproduce the reference instead of redesigning. The strict REF-004 pixel test is a known open failure (see `artifacts/qa/release-readiness.md`).
- Task states are only `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`, `COMPLETE` and `DEFERRED`. `COMPLETE` needs the gates in `docs/44_DEFINITION_OF_DONE.md`. Bug fixes need a regression test that fails first.
- File length: the spec pack allows up to 200 lines, with 230 as a hard ceiling. The user's global standards are stricter (100 lines, enforced by a hook), so apply 100. A few existing files (`domain/geometry.py`, `application/service.py`, `api/main.py`) are already over that limit.
