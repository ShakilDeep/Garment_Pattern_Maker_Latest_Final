import type { FitReport } from "./ImportView";

export interface ValIssueT { severity: "error" | "warn" | "info" | string; rule: string; detail: string; pieces?: string[] }
export interface AuditEntry { time: string; action: string; file: string; status: "ok" | "override" | "blocked"; reason?: string; worst?: number; note?: string }

interface Props {
  fit: FitReport | null;
  issues: ValIssueT[];
  audit: AuditEntry[];
}

/** Accuracy dashboard: spec-vs-measured per size and POM, validation findings, export audit log. */
export default function AccuracyView({ fit, issues, audit }: Props) {
  const worst = fit ? Math.max(0, ...fit.perSize.map((z) => z.max_abs_error)) : 0;
  const out = fit ? fit.rows.filter((r) => !r.ok) : [];
  const errs = issues.filter((i) => String(i.severity).toLowerCase() === "error");
  const warns = issues.filter((i) => String(i.severity).toLowerCase() === "warn");
  return (
    <div className="accuracy-view" data-testid="accuracy-view">
      <section className="card">
        <h3>Spec accuracy</h3>
        {!fit && <p className="hint">Import a spec sheet to see how closely the drawn pattern matches each measurement. (PDS imports have no spec to compare against.)</p>}
        {fit && (
          <>
            <p className={out.length === 0 && fit.converged ? "ok" : "warn-text"} data-testid="acc-summary">
              {out.length === 0 && fit.converged ? "Every measurement is within tolerance" : `${out.length} measurement(s) outside tolerance`} · worst error over all sizes {worst.toFixed(3)} cm
            </p>
            <div className="table-wrap"><table className="spec-table">
              <thead><tr><th>Size</th><th>Worst error (cm)</th><th>Status</th></tr></thead>
              <tbody>{fit.perSize.map((z) => (
                <tr key={z.label} className={z.converged ? "" : "bad"} data-testid={`acc-size-${z.label}`}>
                  <td>{z.label}{z.label === fit.size ? " (shown)" : ""}</td><td>{z.max_abs_error.toFixed(3)}</td><td>{z.converged ? "OK" : "OUT"}</td>
                </tr>))}</tbody>
            </table></div>
            <p className="hint">Accuracy is by our documented measurement definitions (docs/POM-DEFINITIONS.md). Please confirm one size against Optitex's Measure tool before production.</p>
          </>
        )}
      </section>

      <section className="card">
        <h3>Pattern validation</h3>
        {issues.length === 0 && <p className="hint">No findings (or no pattern checked yet).</p>}
        {issues.length > 0 && <p className={errs.length ? "warn-text" : "ok"}>{errs.length} error(s), {warns.length} warning(s)</p>}
        <ul className="warnlist">{issues.slice(0, 40).map((i, k) => <li key={k} className={String(i.severity).toLowerCase() === "error" ? "bad" : ""}><b>{String(i.severity).toUpperCase()}</b> {i.rule}: {i.detail}</li>)}</ul>
      </section>

      <section className="card">
        <h3>Export audit log</h3>
        {audit.length === 0 && <p className="hint">No exports yet. Every export is recorded here, including overrides.</p>}
        {audit.length > 0 && (
          <div className="table-wrap"><table className="spec-table" data-testid="audit-table">
            <thead><tr><th>Time</th><th>Action</th><th>File</th><th>Result</th><th>Worst err</th><th>Reason</th></tr></thead>
            <tbody>{audit.slice().reverse().map((a, i) => (
              <tr key={i} className={a.status === "override" ? "bad" : ""}><td>{a.time.replace("T", " ").slice(0, 19)}</td><td>{a.action}</td><td>{a.file}</td><td>{a.status}</td><td>{a.worst != null ? a.worst.toFixed(3) : ""}</td><td>{a.reason ?? ""}</td></tr>))}</tbody>
          </table></div>
        )}
      </section>
    </div>
  );
}
