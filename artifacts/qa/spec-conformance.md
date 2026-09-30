# Specification conformance audit — 2026-09-09

The Markdown pack defines both a demo MVP and explicit non-goals. The implementation conforms to the deterministic demo workflow and its tested contracts, but it is not 100% conformant to every aspirational or production-gated item.

Implemented and verified in this audit:

- source upload validation, parser projections, provenance, confidence and parse status;
- confidence values are now persisted in normalized measurement and tech-attribute projections, with parser regression coverage;
- requirements discovery, source evidence review, operation readiness and structured error envelopes;
- deterministic eight-piece drafting, registered geometry/seam/grading validators and corrective diagnostics;
- six-size regeneration, mixed-size marker metadata and deterministic placement checks;
- versioned JSON export/import validation, SVG/PDF previews and export persistence;
- project/source parse, list, archive/compare, version-scoped pattern retrieval and validation routes;
- source replacement can be explicitly requested and prior measurement/tech-pack versions are retained for comparison;
- the Measurements upload flow exposes an explicit replacement checkbox and sends the versioning request to the API;
- project archive/restore controls are now available from the dashboard and API;
- archived projects are prevented from running generation, grading, measurement edits, or marker operations until restored;
- request correlation/use-case logging, configurable CORS and parser resource limits;
- frontend workflow, keyboard/focus behavior, loading/error recovery, automated accessibility scans and production build.
- the pattern canvas now provides a keyboard-reachable accessible piece summary table with dimensions and cut quantities as a non-visual structural alternative.
- Source Review now displays persisted parse status, extraction counts, recoverable parser issues, and a visible error/retry-on-reopen state.
- OpenAPI contract inspection now reports 33 paths, including every endpoint listed in docs/09; export route prefixes and the absence of duplicated `/api/v1/api/v1` paths are covered by regression checks.
- JSON API routes now declare Pydantic object/list response contracts; binary export routes intentionally return documented file responses.

Open items required for a release claim:

- REF-004 zero-difference visual acceptance;
- complete source replacement/versioning UI and guided Missing Information Center;
- complete domain-specific response schemas and pagination beyond the compatibility object/list contracts;
- advanced CAD inspector features (dimensions, rulers, snapping, layers, editable properties);
- authenticated deployment, rate/resource limits, retention policy and complete security release evidence;
- expanded manual accessibility and mobile/touch audit;
- clean-machine install and customer rehearsal evidence;
- isolated Playwright execution in this sandbox could not complete its web-server health check; the server process starts, but the sandbox does not expose its loopback listener to the test process;
- Playwright MCP can reach the user-started frontend at 1536×1024; initial load is clean, but the currently running backend returned 404 for `/api/v1/projects/{id}/parse`, indicating it predates the current route implementation and needs restart for end-to-end parse-status verification;
- production drafting, grading, marker and export certification. The supplied references do not contain the client rules needed to implement these safely.

DXF/AAMA/ASTM, OCR, 3D draping, enterprise IAM and production certification remain explicitly out of MVP scope in the Markdown specifications.
