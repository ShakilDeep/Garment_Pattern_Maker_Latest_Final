# Garment Pattern Maker V6: implementation plan

> This file is the working plan. The source requirements are in `Follow/AI-implemented.pdf` (the V6 PRD, 26 pages, 2026-09-30).

## Context

**What we're building.** The PRD turns the V5 single-shirt demo into a full apparel CAD suite with parity to the published Tukatech product line:
- pattern CAD
- automatic pattern making (APM)
- grading
- made-to-measure (MTM)
- digitizing
- markers, nesting and cut planning
- machine output
- a collaboration hub
- 3D fit
- a print studio
- multiple languages

It stays on Python 3.12 / FastAPI and TypeScript / React. The PRD's roadmap runs from P0 (fix-first) to P5 (3D and print studio).

**What the scan found in the current code:**
- **P0 defects.** Of the five defects in the 2026-09-10 gap audit, three (a–c) are fixed and already have regression tests in `backend/tests/test_integrity.py`. Defect (d), grading an older version, is only partly fixed. Defect (e), which version the assistant context picks, is still open.
- **Loose typing.** 29 routes return `ObjectResponse` and 9 return `ListResponse` (`backend/app/api/schemas.py:13-18`).
- **Files over 100 lines:**
  - Backend: `domain/geometry.py` 201, `application/service.py` 147, `api/main.py` 129, `infrastructure/exports.py` 116, `domain/catalog.py` 115, `infrastructure/projections.py` 106.
  - Frontend: `useAppController.ts` 102, `projectMutations.ts` 105, `Measurements.test.tsx` 115.
- **Pattern data.** Pieces are plain dicts: `points` is a closed `[x,y]` list in cm, plus `cut_points`, `grainline`, `notches` and `seams`. They are hard-wired to eight shirt pieces (`domain/drafting.py`, `pattern_checks.REQUIRED_PIECES`). Typed primitives that nothing uses yet already exist in `domain/geometry.py:10-155`: `Point2D`, `CubicBezier`, `Arc`, `ClosedPath`, `Transform2D`.
- **Grading.** Each size is drafted independently with `pattern_workflow.build()`. `validate_grades` (`infrastructure/validation.py:44`) is never wired into the grade workflow.
- **Marker.**
  - It is a bounding-box shelf packer: `marker_pack.pack_instances`, driven by `marker_search.search_marker(instances, width, gap, quantities, ordered_sizes, patterns, seed, time_budget_ms, iterations, grain_policy)`.
  - `marker_batch` caps it at 20 garments, and the `Nest` schema caps width at 500 cm.
- **CAD commands.** `application/commands.py` only supports allowance, fold, notch, undo and redo, with 20 undo snapshots.
- **Persistence.** One JSON snapshot per project in `projects`, with additive projections (schema v3, `infrastructure/migrations.py`). There is no migration framework and no tenant or user columns.
- **Frontend.**
  - No router: the page name lives in `location.hash`.
  - No i18n: about 360 English literals, and the e2e tests assert on English text.
  - `PatternCanvas` is a viewer only, with no vertex handles and no world↔screen transform.
- **Tooling.**
  - Not a git repo.
  - The Stop hook finds no test command at the root.
  - There are about 191 source files, over the hook's 100-file budget.
  - Context7 hit its monthly quota ("Monthly quota exceeded") during planning, so a fallback rule is needed.

**Decisions from you:**
- Detail every phase at step level.
- Keep SQLite until P4, behind ports.
- Review every step with an Opus reviewer, then run the `code-reviewer-haiku` pass that the hook requires.

---

## 0. Per-step protocol (applies to every step below)

Each step is one small change set, usually 3–8 files. Run it as a loop:

1. **Open the step.**
   - MASTER rows are pre-created: T039 = S00, T040–T122 = P0-01…P5-09 in order (P2-02–06 is split into one row per template family). Set the step's row to `IN_PROGRESS`.
   - Columns: `ID | Task | Status | Depends on | Required Docs | Evidence`.
   - Set the status to `IN_PROGRESS`.
2. **Sequential Thinking MCP.** Break the step down: invariants, edge cases, which design pattern, and the file split.
3. **Context7 MCP.** Before any external API is used, run `resolve-library-id` then `query-docs` for each library the step touches. Record the library, version, question and decision in the MASTER evidence column.
   - **If Context7 is unavailable or over quota:** use WebFetch on the library's official docs. Record `Context7 unavailable; verified via <url>`. Never fabricate Context7 output. This rule comes from `docs/104`.
4. **RED.** Write the failing tests first, drawn from the PRD acceptance column: a happy path, a boundary case and a failure path with a specific error code. Run them and confirm they fail.
5. **GREEN.** Implement the change.
   - Every source and test file stays ≤100 lines. Split files by responsibility; never cram code to fit.
   - Use the design pattern named in the step.
   - The domain layer never imports FastAPI, SQLAlchemy, React or AI SDKs.
   - No geometry decisions in TypeScript (CAD-07).
6. **Gate A (automated).** All of these must pass:
   - `conda run -n patter-codex python -m pytest backend/tests -c backend/pyproject.toml`
   - `ruff check app tests` and `mypy app`, run from `backend/`
   - `npm test` and `npm run build`, run from `frontend/`
   - `python scripts/check_lines.py` (created in S00)
   - For steps that touch the UI or a user workflow, also run `npm run test:e2e`.
7. **Gate B: same-model review.** Spawn an Opus reviewer: `Agent`, `general-purpose`, `model: "opus"`. Give it the diff, the PRD IDs, this protocol and the CLAUDE.md standards. It reports Blocker, Major and Minor findings.
8. **Fix loop.**
   - Fix any Blocker or Major finding yourself, or with `code-fixer-sonnet`, then rerun Gates A and B.
   - After **3 failed iterations**, stop, set the step to `BLOCKED`, and ask the user.
9. **Gate C: harness.** Run a clean `code-reviewer-haiku` pass to clear `.claude/.validation-pending`.
   - Paths matching `auth|payment|billing|secret|credential|migration` need two consecutive clean passes.
10. **Close the step.**
    - Run `graphify update .` (if graphify is installed) and `git commit` (one commit per step, ending with the Co-Authored-By line).
    - Set the MASTER row to `COMPLETE` with evidence: test counts, reviewer verdicts and Context7 notes.

**Phase gate (end of every phase):**
- Full regression: pytest, vitest, Playwright, and the performance budgets in `tests/test_performance_budgets.py`.
- V5 golden tests stay green: `test_demo_goldens.py`.
- An Opus review of the whole phase diff.
- A demo walkthrough recorded under `artifacts/qa/v6-P<n>.md`.

**Design-pattern vocabulary** (from `docs/06` and `docs/41`):
- Strategy: drafting, grading, nesting, export.
- Command: CAD edits.
- Repository and Unit of Work: persistence.
- Adapter: parsers, DXF, legacy V5 dicts, providers.
- Factory and Registry: templates, tools, exporters.
- Template Method: silhouette drafting.
- Chain of Responsibility: validators.
- Observer: job progress.
- Facade: package re-exports.
- Strangler Fig: V5 to V6 model migration.
- Rule: prefer pure functions and avoid pattern cargo culting.

---

**Constraints found while running S00:**
- **Planning cadence.** `protect-validation-gate.js` blocks the 4th and later edit made without a sequential-thinking call. Call Sequential Thinking at least every 3 edits, not just once per step.
- **Ruff scope.** Gate A runs `ruff check app tests` from `backend/`. The old `scripts/inspect_references.py` and `scripts/verify_artifacts.py` have I001 import-order issues; they are out of scope and are only fixed if a step touches them.
- **Baseline.** 192 pytest tests (about 114 s) and 44 vitest tests (about 73 s). The hook's test command takes about 3 minutes, inside its 5-minute timeout. If the suite grows past about 4 minutes, split fast and slow markers.
- **Git.** Baseline commit `3404e86`. The local git identity is set. `.claude/.*` hook state and `*.egg-info/` are gitignored.

## S00: Tooling prerequisites ✅ DONE (commit 5dd23c6)

- `git init` and a first baseline commit, so each step can be rolled back. `.gitignore` already exists.
- Create `.claude/test-command`. It runs pytest, then `npm --prefix frontend test`, and exits non-zero if either fails, so the Stop hook actually runs the tests.
- `scripts/check_lines.py` (≤100 lines):
  - Fails when any `.py/.ts/.tsx` file under `backend/app`, `backend/tests`, `frontend/src`, `frontend/e2e` or `scripts/` is over 100 lines.
  - Test: `backend/tests/test_check_lines.py`.
- **File-budget override.** Write `.claude/.file-budget-override` with a justification: V6 has about 5 products and 41 capabilities, and sticking to ≤100-line files means more files. Target about 450 source files, reported at each phase gate.
- Record the baseline in MASTER: current test counts, and confirm that `test_integrity.py` passes.

## Phase P0: Fix-first integrity and hygiene

| Step | Goal | Files (new → / modified ~) | Pattern | Done when |
|---|---|---|---|---|
| P0-01 ✅ DONE (3c65c64) | Split `domain/geometry.py` (201 lines) | → `domain/geom/{primitives,curves,paths,transform,polyline_ops,piece_builder}.py`; ~`domain/geometry.py` becomes a re-export Facade. Its current importers (`shirt_set`, `drafting`, `marker_pack`, `pattern_checks`, `placement_checks`, and 4 tests) must not change | Facade | Every import still works; geometry tests green |
| P0-02 ✅ DONE (b98f1eb) | Split `service.py`, `main.py`, `exports.py`, `catalog.py`, `projections.py`, and the oversized tests `test_ai_context.py` (176), `test_ai_trust.py` (129), `test_demo_goldens.py` (112), `test_tolerance_boundaries.py` (112) | → `api/error_handlers.py`, `api/middleware.py`, `application/project_import.py`, `infrastructure/export_{svg,pdf,json}.py`, `domain/catalog_{sizes,mapping}.py`, `infrastructure/projection_{pattern,source}.py`; tests split by behaviour, with no test removed or weakened | Facade | Behaviour unchanged; test count unchanged or higher; `check_lines` clean for the backend |
| P0-03 ✅ DONE (62ff762) | Split the frontend files | → `useProjectState.ts`, `useKeyboard.ts`, `mutations/{measurement,source,lifecycle}.ts`, `Measurements.edit.test.tsx` | Custom hooks | vitest and e2e green |
| P0-04 ✅ DONE (4df0eee) | Defect d: grading an older version | ~`pattern_workflow.build`, which takes an explicit `inputs` bundle (measurements, resolutions, allowance) taken from the stored version; ~`pattern_routes.grade_version` calls `check_operation` and rejects grade ids | Parameter object | New test: grading v1 after measurements change reproduces v1 inputs, and `input_hash` matches |
| P0-05 ✅ DONE (dfdca78) | Defect e: version selection | → `application/version_select.py` `select_for_size(project, size)` (grade first); used by `assistant_context.py`; the frontend mirrors it in `versionSelect.ts` and `App.tsx` | Single rule | Parity test: backend and frontend pick the same id when grades include the base size |
| P0-06 ✅ DONE (e8980ab) | Harden the import and archive lifecycle | ~`import_geometry.py` (checks placements, unique grade sizes, schema_version, marker `pattern_ids`, and stops importing FastAPI's `HTTPException` in infrastructure: raise a domain `ImportInvalid` error that `api/error_handlers.py` maps to 422); ~`lifecycle_routes` (archive calls `_ensure_active`, restore calls `invalidate`); ~`readiness.py` (checks source blockers) | Chain of Responsibility validators | Failure-path tests return 422, 409 and 400 with specific codes |
| P0-07 ✅ DONE (b9bf485) | Per-measurement ranges | ~`measurement_write.bound_changes` uses per-code min/max from the catalog; the bulk route rejects unknown keys | Table-driven | A −3 cm sleeve is rejected; an unknown key returns 422 |
| P0-08 ✅ DONE (897bfc7) | Typed responses | → `api/models/{project,pattern,marker,source,requirement,review}.py` replace `ObjectResponse`/`ListResponse`; → `api/pagination.py` `Page[T]` | DTO | OpenAPI has no `RootModel[dict]`; e2e green |
| P0-09 ✅ DONE (484d38e) | **Phase gate P0** | `artifacts/qa/v6-P0.md`; fix the stale e2e helper `frontend/e2e/demo.ts` (it restores the project via localStorage, but `startup.ts` deliberately always opens the Projects picker, so all 9 Playwright tests fail at setup — pre-existing since V5 baseline 3404e86, found during T042) | | Everything green incl. Playwright; `check_lines` passes on the whole repo |

## Phase P1: Pattern model, CAD editor, grading, chart, DXF, languages

**Pattern model** (`backend/app/domain/pattern/`). The existing `domain/geom` primitives are reused.

| Step | PRD | Goal and files | Pattern | Acceptance test |
|---|---|---|---|---|
| P1-01 ✅ DONE (ba55793) | PM-01, PM-02 | → `pattern/{ids,point,segment,annotation,piece}.py`: frozen dataclasses; segments are Line, CubicBezier and Arc; points have stable ids and an optional `grade_rule` ref; annotations cover internal lines, notches, drills, grainline, fold, labels and cut quantity (self, pair, fold) | Value objects | Invariants: ids are unique, and the outline is closed |
| P1-02 | PM-01 | → `pattern/serialize.py` (JSON), `pattern/hashing.py` (stable geometry hash) | Memento | JSON round-trip within 0.01 cm; hash is stable |
| P1-03 | Strangler | → `infrastructure/legacy_pattern_adapter.py`: V5 piece dict ↔ `Piece`. `draft()` output is wrapped so the old dict API stays available for the SVG/PDF/marker code | Adapter | V5 goldens unchanged; adapter round-trip is exact |
| P1-04 | PM-03 | → `pattern/seam.py` plus `pattern/corners.py`: allowance per edge, with mitre, square, reverse and fold-back corners (Shapely offsets; confirm `pyclipper` vs Shapely `offset_curve` with Context7) | Strategy per corner | Cut outline `is_valid` for all four corner styles |
| P1-05 | PM-04 | → `pattern/style.py`: Style aggregate with unlimited pieces and sizes; lazy per-size views | Aggregate | 200 pieces × 30 sizes load and serialize in under 3 s (perf test) |
| P1-06 | PM-05 | → `application/cad/{command,bus,history,registry}.py`: `Command.apply(style) → style`, a 100-step history keyed by geometry hash, persisted. ~`commands.py` delegates to the bus (legacy commands registered) | Command + Registry | 100 undos restore identical hashes |
| P1-07 | CAD-07 | → `api/cad_routes.py`: `POST /pieces/{id}/commands`, `GET /pieces/{id}` (typed models); → `application/cad/guard.py` validates the result before saving | Chain of Responsibility | An invalid result returns 422 `GEOMETRY_INVALID` and nothing is saved |
| P1-08 | CAD-01 | → `application/cad/tools_draft/{point,line,curve,shape,construct}.py`: point, line, curve, rectangle, circle, offset, parallel, perpendicular, intersection | Command per tool | One unit test per tool |
| P1-09 | CAD-02 | → `tools_modify/{transform,split_join,trim_extend,smooth}.py`: move, rotate, mirror, split, join, trim, extend, smooth | Command | Self-intersection is blocked with a message |
| P1-10 | CAD-03 | → `tools_garment/{dart,pleat_tuck,slash_spread,fold}.py` | Command | Dart rotation keeps seam length within 0.01 cm |
| P1-11 | CAD-04, CAD-05 | → `domain/pattern/measure.py` (distance, curve length, angle, area, perimeter); → `application/cad/walk.py` (walk and true seams, notch while walking); query endpoints | Pure functions | Sleeve cap vs armhole ease matches hand calculation within 0.01 cm |

**Frontend foundation and CAD editor** (`frontend/src/`). Check react-router, TanStack Query, react-i18next and SVG pointer handling with Context7 first.

| Step | PRD | Goal and files | Pattern | Acceptance |
|---|---|---|---|---|
| P1-12 | infra | Add React Router and TanStack Query. → `routes/`, `queries/{project,pattern}.ts`; keep the `#Page` hash URLs through a redirect | Adapter | Existing e2e green |
| P1-13 | I18N-01 | Add react-i18next. → `i18n/{index.ts,en.json,bn.json}` and a language switcher; migrate strings one component group per commit (Shell, Measurements, Workflow, Dialogs…). Add a Bangla font (Noto Sans Bengali). E2E keeps `en` | Catalog | Lint script finds no hard-coded JSX text; `bn` renders |
| P1-14 | I18N-02 | → `units/format.ts`: cm or inch with fractions, display only | Pure function | Switching units never changes stored values (test) |
| P1-15 | CAD-06 | → `cad/{CadCanvas,viewport,rulers,grid,layers}.tsx/.ts`: world↔screen transform and 1:1 calibration dialog | Composition | Viewport math tests; after calibration, 10 cm renders as 10 cm ± 1 mm |
| P1-16 | CAD-01 to 05 UI | → `cad/tools/{registry,*.ts}`: one Strategy per tool with a shortcut and snap hints (points, midpoints, edges), sending commands to P1-07 | Strategy + Registry | Keyboard access to every tool (axe + e2e) |
| P1-17 | CAD-04/05 UI | → `cad/panels/{Measure,Walk}.tsx`: live ease readout from the backend | | Displayed values match the backend |

**Grading, chart, interchange, digitizing, AI.**

| Step | PRD | Goal and files | Pattern | Acceptance |
|---|---|---|---|---|
| P1-18 | GR-03, CPE | → `domain/grading/size_range.py` (any labels, including half sizes like 4½) and `domain/chart/{pom,chart}.py` (editable POM × size chart, tolerances, units); an adapter replaces the 35-code MAPPING with per-template POM lists | Value objects + Adapter | Grading 4, 4½, 5 raises no errors; V5 shirt requirements unchanged |
| P1-19 | GR-01, GR-02 | → `domain/grading/{rule_table,strategy,delta_grade,regenerate}.py`: brand rule library; `RegeneratePerSize` wraps V5 `build`; `DeltaGrade` applies dx/dy by point id | Strategy | A table built on one style applies to another that shares point names; both modes selectable per style |
| P1-20 | GR-04 | → `domain/grading/angle.py`: deltas along a local axis defined by two points | Strategy | Curve shape preserved (curvature invariant) |
| P1-21 | GR-05, GR-06 | ~`validation.validate_grades` gains non-monotonic growth and seam-mismatch checks, wired into grade routes; nest view endpoint plus UI stacked on a chosen point | Chain of Responsibility | Per-size report; existing V5 overlay test green |
| P1-22 | OUT-03 | → `infrastructure/interchange/{dxf_writer,dxf_reader,aama_layers,astm_layers}.py` (ezdxf; confirm the API with Context7): notches, grain, drill holes, grade rules; `/imports/dxf`, `/exports/dxf-aama`, `/exports/dxf-astm` | Adapter + Strategy per dialect | 10-file round-trip corpus in `fixtures/dxf/` within 0.01 cm |
| P1-23 | DIG-01, DIG-02 | → `infrastructure/digitize/{board_detect,trace}.py` (scikit-image: calibration board, contour extraction) and a manual trace command | Adapter | Reference board scale error under 0.3%; traced pieces are editable |
| P1-24 | AI-04, AI-05, AI-06 | Extend `assistant_policy.POLICY`: measurement outlier warnings; plain-language requests turned into CAD Commands, previewed and undoable; grade-rule suggestions. All go through the `AIProvider` port and are logged (model, prompt version, confidence, decision) | Command + Proposal | The app works with AI off; no geometry is written without confirmation |
| P1-25 | **Phase gate P1** | | | Everything green; perf: editor command round-trip p95 under 150 ms |

## Phase P2: APM templates, MTM, help

| Step | PRD | Goal and files | Pattern |
|---|---|---|---|
| P2-01 | APM-02 | → `domain/templates/{base,registry}.py`: `SilhouetteTemplate.draft(chart, size)` template method; the shirt template wraps V5 `draft` | Template Method + Registry |
| P2-02–06 | APM-02 | One step per family: t-shirt, polo, woven shirt (men's and women's), trousers, basic blocks (bodice, skirt, sleeve, pant). Each lives in `domain/templates/<family>/` and has golden tests | Template Method |
| P2-07 | APM-03 | POM visual guide: SVG sketch hotspots per template (`frontend/src/apm/PomGuide.tsx`) | |
| P2-08 | APM-04, APM-05, custom size range | Four-step wizard: size range → template → POM values (import from the V5 XLSX/PDF parsers) → graded pattern, opened directly in the marker | State machine |
| P2-09 | MTM-01 | → `application/mtm/{import,nearest_size}.py`: CSV/XLSX import, weighted POM distance. Body measurements are encrypted at rest (Fernet; Context7) and deletable | Strategy |
| P2-10 | MTM-02 | → `mtm/alterations.py`: alteration rules applied as Commands; the rules used are recorded | Command |
| P2-11 | block library | Fitted 2D block templates saved and reused per brand | Repository |
| P2-12 | HELP-01 | `help/` catalog with a clip per tool and a searchable panel | Registry |
| P2-13 | AI-01, 02, 03, 11 | OCR and language-model chart extraction behind the `AttributeExtractor` port (low-confidence values block generation); per-buyer label mapping; sketch → template detection; explain-in-user-language | Adapter + Proposal |
| P2-14 | **Phase gate P2** | Every template generates valid pieces for every size in its sample chart | |

## Phase P3: Markers, nesting, cut planning, machine output, editions

| Step | PRD | Goal and files | Pattern |
|---|---|---|---|
| P3-01 | MK-01 | → `domain/marker/{setup,rules}.py`: width, length limit, selvage, face-up/down, one-way or two-way, tubular; per-piece rotations, flip, tilt, buffers (MK-03) | Value objects |
| P3-02 | NS-02 | → `ports/job_queue.py`, `infrastructure/jobs/{sqlite_queue,worker,checkpoint}.py`: persistent in-process worker that survives a restart; WebSocket `/nest-jobs/{id}/progress` | Port + Observer |
| P3-03 | NS-01, NS-06 | → `infrastructure/nesting/{strategy,registry,nfp,bottom_left}.py`: no-fit polygon by Minkowski sum (pyclipper; Context7), seeded; the V5 row packer is registered as "quick" | Strategy + Registry |
| P3-04 | NS-03, NS-05 | Half-run, nesting blocks, garment and size grouping constraints | Specification |
| P3-05 | NS-04 | Plaid and stripe matching: repeat x/y, match points, snap to repeat lines | Strategy |
| P3-06 | MK-02 | Interactive marker: `frontend/src/marker/{PieceBin,MarkerBoard}.tsx`; the backend validates each placement (overlap and bounds) | Command |
| P3-07 | MK-04, editions | → `application/entitlements.py`: edition limits enforced server-side (Learning: 14 pieces, 4 sizes, 59×120 in); caps lifted for Professional | Policy |
| P3-08 | OUT-01, AI-08 | Yield and costing report (fabric per garment, utilization, waste, cost); a pre-pattern AI estimate, labelled as an estimate | |
| P3-09 | OUT-02 | → `interchange/{hpgl_writer,pdf_tiled}.py`: HPGL/2 and 1:1 tiled PDF (A4, Letter, full width) | Strategy per format |
| P3-10 | OUT-04, OUT-05 | Cut-path export (drill and notch commands, travel optimized with nearest-neighbour + 2-opt) and spreader data per lay | Strategy |
| P3-11 | OUT-06 | Device job queue API: send, pause, resume from checkpoint, status; survives a restart | State machine |
| P3-12 | CP-01 to 05 | → `domain/cutplan/{order,lay_planner,material,dye_lots,queue}.py`: cut orders, lay generation (greedy first; OR-Tools optional), material requirements, dye lots and rolls, sortable marker queue | Strategy |
| P3-13 | AI-09 | Nesting seed from past markers, used only inside jobs | Strategy |
| P3-14 | **Phase gate P3** | On the demo shirt at 150 cm, NFP beats the row packer by at least 8 utilization points; a 200-garment marker opens in under 5 s; 10 cm test square plots within ±0.5 mm | |

## Phase P4: Collaboration hub, multi-user, PostgreSQL

| Step | PRD | Goal and files | Pattern |
|---|---|---|---|
| P4-01 | §8 | Adopt Alembic (Context7). Schema v4 migration: normalized tables become the source of truth, and snapshots stay readable for rollback. Two clean reviews (migration path) | Unit of Work |
| P4-02 | §4 | PostgreSQL adapter behind `Repository`; SQLite kept for single-user local mode | Repository + Adapter |
| P4-03 | Security | OIDC login (FastAPI security; Context7), `Organization/User/Role/Membership`, tenant id on every query, role checks in the application layer. Two clean reviews (auth path) | Policy |
| P4-04 | HUB-01 | Style folders: brand, season, category, gender, type, fit; search and filter | Repository + Specification |
| P4-05 | HUB-02, 03 | Stage workflow generalizing V5 reviews: concept → pattern → sample → fit → costing → final, with an owner per stage; approval metrics | State machine |
| P4-06 | HUB-04 | Every version downloadable, with a first-class change log | Event log |
| P4-07 | HUB-05, AI-12 | Comments per version, email and in-app notifications, thread summaries that link back to each comment | Observer |
| P4-08 | HUB-06 | Dashboards with Excel and CSV export over any date window | Query objects |
| P4-09 | HUB-07 | Vendor accounts scoped to shared styles; company admin | Policy |
| P4-10 | HUB-08 | Redis/RQ adapter for the `job_queue` port; shared cross-site marker queue | Adapter |
| P4-11 | NFR | Rate limits on uploads and nest jobs; metrics for queue length and nest duration | Middleware |
| P4-12 | **Phase gate P4** | Two users on different sites see the same queue; a vendor sees only shared styles | |

## Phase P5: 3D fit and print studio

| Step | PRD | Goal and files | Pattern |
|---|---|---|---|
| P5-01 | 3D-08 | `frontend/src/three/` viewer (three.js; Context7), browser-only | |
| P5-02 | 3D-01 | Six parametric avatars with walk and arm-raise animations; girths within 0.5 cm | Factory |
| P5-03 | 3D-02 | Seam pairing from pattern data; unsewn seams listed before simulation (backend) | |
| P5-04 | 3D-03 | Versioned fabric library; fabrics added from swatch test values | Repository |
| P5-05 | 3D-04 | Cloth solver in a Web Worker (TypeScript) plus fit maps with a shared legend | Strategy |
| P5-06 | 3D-05, AI-07 | 2D↔3D link (refit under 10 s); fit-correction proposals as previewed Commands | Observer + Command |
| P5-07 | 3D-06, 07 | Trims and materials; virtual photo shoot with PNG and MP4 export | |
| P5-08 | ST-01 to 04, AI-10 | → `infrastructure/studio/{color_sep,repeats,colorways}.py` (Pillow, scikit-image k-means); repeat size feeds NS-04 | Strategy |
| P5-09 | **Phase gate P5** | Final regression; accessibility (WCAG 2.2 AA for non-canvas UI); release-readiness update | |

---

## Verification (end to end)

- **Every step:** Gates A, B and C (§0), plus RED tests written before implementation.
- **Every phase:** the full suite, `npm run test:e2e` at 1536×1024, V5 golden and performance tests, an Opus review of the phase diff, and a demo walkthrough under `artifacts/qa/v6-P<n>.md`.
- **Standing invariants:**
  - The V5 demo shirt workflow keeps passing.
  - Same inputs and seed give identical geometry and marker hashes.
  - The app works fully with AI switched off.
  - Every file stays ≤100 lines (`scripts/check_lines.py`).

## Open questions carried from PRD §11 (not blocking P0–P1)

- Which templates come after the shirt?
- Hosted SaaS, or also on-premise?
- Which plotter and cutter models must be supported at launch?
- Are client drafting blocks and grade rules available for calibration?
