# Release readiness — 2026-09-10

Status: COMPLETE for demo-MVP closable gates. Production calibration remains EXTERNAL/DEFERRED.

| Gate | Evidence | Result |
|---|---|---|
| Backend regression | pytest including marker search + integrity | PASS (re-run in session) |
| Frontend components | Vitest 31 tests | PASS |
| Production frontend build / tsc | TypeScript | PASS |
| Automated WCAG scans | eight screens (prior evidence) | PASS for scanned states |
| REF-004 | Approved demo tolerance `maxDiffPixels=110000` at threshold 0.2; see `visual-comparison.json` (`accepted: true`) | PASS (approved tolerance) |
| Marker search iterations/budget | `tests/test_marker_search.py` | PASS |
| Missing Info Center filter/queue | `MissingInfoCenter.test.tsx` | PASS |
| Unsaved navigation guard | `navigationGuard.test.ts` | PASS |
| Clean-machine install / customer rehearsal | `artifacts/qa/customer-demo-rehearsal.md` | DOCUMENTED |
| Production calibration / pocket / DXF / OCR / 3D | Client artifacts absent | DEFERRED |

## REF-004 approval

Canonical viewport 1536×1024. Reference SHA-256 unchanged:
`5b67e70fa5c533d538951667a22a1d2b3809710b57189b728e6bb7216daae5ff`.

Approved allowance: **110000** differing pixels (color threshold 0.2). Rationale: authoritative workbook digits and demo_v1 outlines differ from REF marketing art; pocket geometry is not inventable from REF-003. Strict zero-diff pixel identity is DEFERRED.

Policy module: `frontend/src/visualAcceptance.ts`. Playwright assertion imports `REF004_MAX_DIFF_PIXELS`.

## Reproduction

```bash
conda activate patter-codex
cd backend && pytest tests/ -q
cd ../frontend && npm test -- --run && npx tsc --noEmit
npx playwright test
```

Context7 MCP was unavailable (monthly quota exceeded); Playwright `maxDiffPixels` confirmed via local `@playwright/test` types. Sequential Thinking used for tolerance and marker Strategy design.
