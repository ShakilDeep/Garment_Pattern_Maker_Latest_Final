# Garment Pattern Maker V5

Local React + FastAPI application built from the 118 Markdown specifications, two source PDFs, measurement workbook, and desktop UI reference in this workspace.

## Run the app

### First-time setup

Install [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) and Node.js 20 or later, then run these commands in PowerShell from the workspace root:

```powershell
conda env create -f environment.yml
conda activate patter-codex
python -m pip install -e "./backend[dev]"
cd frontend
npm ci
npm run build
cd ..
```

This creates the Python 3.12 environment named `patter-codex`, explicitly installs all backend dependencies, and builds the React frontend. If the environment already exists, skip `conda env create` and run the remaining commands.

### Start the built app

From the workspace root, start the local server:

```powershell
.\scripts\start.ps1
```

Keep that terminal open, then open http://127.0.0.1:8000 in a browser. The API documentation is available at http://127.0.0.1:8000/docs.

If PowerShell blocks the script, run the server command directly:

```powershell
conda activate patter-codex
cd backend
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

### Frontend development

Use two terminals. In the first, start the backend with `./scripts/start.ps1` (or the direct command above). In the second:

```powershell
conda activate patter-codex
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` requests to the backend at port 8000.

### WSL frontend dependency recovery

If Vite reports that `@rollup/rollup-linux-x64-gnu` is missing, rebuild the Linux dependency tree from the `frontend` directory:

```bash
rm -rf node_modules
npm ci --include=optional
npm install
```

Then run `npm run dev` again. Do not reuse a `node_modules` directory installed from Windows.

## Try the workflow

1. Choose **Open demo project**, or create a project and upload `Book2(4).xlsx` and `1078983(5).pdf`.
2. Review source measurements and PDF details. Confirm centimeters, the demo profile, measurement review, and the placket source choice under **Requirements**.
3. Generate a size, inspect the eight pattern pieces, and review seam warnings in **Pattern Studio**.
4. Generate all six sizes under **Grading**.
5. Set fabric width, per-size quantities and spacing in **Marker Nesting** and calculate a layout.
6. Review all checks in **Validation Center**, then download pattern or marker SVG/PDF and traceable JSON from **Export**.

Saved projects, measurement overrides, requirement resolutions, generated versions and audit events persist in the local `backend/garment.db` SQLite database. Keep that file to retain your work. Unsaved main-form drafts are held in browser session storage; saved measurements are authoritative on the server.

## Implemented scope

- Local PDF text extraction and XLSX parsing with numeric/formula provenance.
- Explicit missing-input gates and workbook-versus-tech-pack placket resolution.
- Manual entry, table edits, unit display conversion and saved-edit undo/redo.
- Deterministic demo drafting, uniform seam offset, geometric validation and source comparison warnings.
- Per-size regeneration for S, M, L, XL, XXL and 3XL; visual overlays.
- Deterministic fabric placement using cut quantities, calculated utilization, bounds and spacing validation.
- Project dashboard, six persistent review gates, state-transition history and normalized SQLite projections.
- Local provider-neutral AI action proposals with explicit confirmation and deterministic service dispatch.
- SVG/PDF pattern and marker previews plus JSON geometry/project exports.
- Keyboard navigation, pan/zoom/fit, piece selection, source details, activity and mobile review.

## Boundaries

This is a working **demo application**, not a production-certified garment CAD system. The supplied files do not establish a calibrated drafting block. Sleeve and collar comparisons can report warnings; physical fit and client manufacturing validation remain necessary. Cloud AI providers, OCR, 3D draping, industry-certified DXF, freehand curve editing, and production certification are outside the implemented local demo.

The UI follows the reference composition and colors; generated geometry and actual source values differ from the illustration. Pixel-identical acceptance is not claimed. SQLite retains compatibility snapshots and additive normalized records for sources, measurements, requirements, patterns, validation, markers, exports, reviews, and audit history.

## Checks

```powershell
conda run -n patter-codex python -m pytest backend/tests -c backend/pyproject.toml
cd backend
conda run -n patter-codex python -m ruff check app tests
conda run -n patter-codex python -m mypy app
cd ../frontend
npm test
npm run build
npm run test:e2e
```

The Playwright configuration starts an isolated test server and test database. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` if Chromium is installed outside Playwright's default cache. Screenshots are saved under `artifacts/qa`. API documentation is at http://127.0.0.1:8000/docs.


Calibration evidence is available under Requirements → Production calibration. Select a supporting project document, reviewer and note to record evidence for a specific request. The download includes only unresolved calibration requests and project context; evidence review does not certify production or change demo geometry.

The API uses `POST /api/v1/projects/{id}/requirements/calibration:{key}/resolve` with `value: "reviewed"`, `resolution_type: "source"`, `source_id`, `actor`, and `note`. Supported keys and current status are returned by the project's requirements endpoint. `GET /api/v1/projects/{id}/calibration-request` downloads the current checklist.

Current acceptance evidence and open gates are recorded in [release-readiness.md](artifacts/qa/release-readiness.md). The strict REF-004 browser test remains failing; the full audit is not complete.

Assistant adapters can be supplied through `create_app(database_url, ai_provider=provider)` using the `AIProvider` protocol. The default remains offline. Proposals are validated before saving; invalid provider output returns `AI_OUTPUT_INVALID` (502), and provider failures return `AI_UNAVAILABLE` (503), with manual controls still available. Mutating proposals require confirmation and cannot be replayed. Database startup applies additive schema v3, including measurement-confidence projections for existing projects.

Providers implement `propose(prompt, size, *, context=None)`. Context contains a detached projection of unresolved requirements, extraction-review issues, selected-size validation, and optional piece metadata; it excludes project names, audit history, and geometry coordinates. Assistant requests may include `piece_id` for a piece in the requested size. Unknown or wrong-size selections return 404. The local provider explains current blockers and source issues; `Map measurement label "sleev length"` returns a terminology suggestion for manual review without remapping source data. These heuristic matches are not calibrated confidence or measurement conversions.

Select a pattern piece and open **Ask AI → Explain selected piece** for dimensions and seam information. Changing project, size, selection, or saved project version clears the assistant draft and proposal; submit a new request for the current context.
