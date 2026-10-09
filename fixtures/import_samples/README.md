# Import samples

Small workbooks built for tests (not buyer data).

- `unmapped_pom.xlsx`: a two-size POM chart. One row maps through the synonym table (`1/2 SEAT`). One is
  a near-synonym that only the suggester can propose (`INSEAM ALONG SEAM`). One matches nothing
  (`MYSTERY POINT`). The mapping-screen e2e test (`frontend/e2e/mapping.spec.ts`) uses it.
