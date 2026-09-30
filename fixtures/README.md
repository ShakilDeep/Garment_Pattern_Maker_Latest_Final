# Demo v1 golden fixtures

`demo_v1_metrics.json` freezes the local demo profile's numerical behavior against REF-003 and REF-002 as of 2026-09-10, including the T011 forward-shoulder revision. It is regression evidence, not an approved production block.

The fixture contains source hashes, parsed workbook cells/formulas/provenance (including explicit `mapping_status`/`mapped_from`; unknown codes stay unmapped), normalized S–3XL measurements, parsed tech-pack metadata and source candidates, requirement statuses before and after explicit demo review, and dimensions/area/perimeter/seam lengths/cut quantities for all eight pieces in each size. Marker metrics use the recorded first-fit configuration: 150 cm fabric, S×2 + L×1, 0.5 cm gap, no allowance, vertical grain, seed 0. The expected 48 placements occupy 381.25 cm at approximately 68.700109% utilization after T011 demo forward-shoulder geometry (back/yoke half-shoulder shortened by max(0, forward_shoulder_armhole − forward_shoulder_neck)).

The initial numerical metrics were captured from the versioned deterministic demo engine. Independent tests check source-derived component dimensions, Shapely area/perimeter, simple closed geometry, fabric containment and inter-piece spacing; recorded metrics alone do not establish physical fit. The source metadata is also covered by direct source-detail assertions in `test_source_details.py`.

Run from backend:

```bash
python -m pytest tests/test_demo_goldens.py tests/test_tolerance_boundaries.py
```

Do not regenerate this file to silence a regression. Changes require a documented requirement or bug fix, a test explanation, and an ADR when geometry behavior changes. Review source hashes, source data and metric changes explicitly. No auto-update command is installed.

The fixture preserves production-calibration requirements even after demo readiness. It does not supply missing pocket dimensions, industrial drafting/grading rules, or manufacturing certification.
