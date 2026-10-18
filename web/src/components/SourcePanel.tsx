import type { FitReport, SpecResult } from "./ImportView";
import type { GeoPiece, PatternT } from "../types";
import { CM_PER_IN, fmt } from "../util";

export interface PdsSource { style: string; sizes: string[]; size: string; source: string }

interface Props {
  mode: "spec" | "pds";
  units: "cm" | "in";
  spec: SpecResult | null;
  specSize: string;
  fit: FitReport | null;
  onSpecSize: (z: string) => void;
  onSpecEdit: (row: number, sizeIdx: number, cm: number) => void;
  kind: "pant" | "shirt";
  onKind: (k: "pant" | "shirt") => void;
  targets: { key: string; label: string }[];
  onMap: (row: number, key: string) => void;
  pds: PdsSource | null;
  onPdsSize: (z: string) => void;
  geo: GeoPiece[];
  pattern: PatternT | null;
}

function perimeter(poly: { x: number; y: number }[] | [number, number][]): number {
  const pts = (poly as any[]).map((q) => (Array.isArray(q) ? { x: q[0], y: q[1] } : q));
  let s = 0;
  for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; s += Math.hypot(b.x - a.x, b.y - a.y); }
  return s;
}

/** Left-hand panel shown instead of the body-measurement form once a spec sheet or a PDS file is imported. */
export default function SourcePanel({ mode, units, spec, specSize, fit, onSpecSize, onSpecEdit, kind, onKind, targets, onMap, pds, onPdsSize, geo, pattern }: Props) {
  const f = units === "in" ? 1 / CM_PER_IN : 1;
  const u = units;
  if (mode === "spec" && spec) {
    const s = spec.spec;
    const si = Math.max(0, s.sizes.findIndex((z) => z === specSize));
    const measured = new Map((fit?.rows ?? []).map((r) => [r.code, r]));
    const valid = new Set(targets.map((t) => t.key));
    const chosen = (r: (typeof s.rows)[number]) => { const k = r.map_to ?? r.canonical ?? ""; return valid.has(k) ? k : ""; };
    const unused = s.rows.filter((r) => !chosen(r)).length;
    return (
      <div data-testid="source-panel">
        <div className="panel-head"><h2>Spec measurements</h2></div>
        <p className="hint"><b>{s.style || "(no style #)"}</b> {s.description} · {s.brand}<br />Imported from your spec sheet. Edit a value and the pattern is re-drawn to match.</p>
        <label className="field"><span>Size</span>
          <select value={specSize} onChange={(e) => onSpecSize(e.target.value)} data-testid="spec-size">{s.sizes.map((z) => <option key={z}>{z}</option>)}</select><em />
        </label>
        <label className="field"><span>Garment</span>
          <select value={kind} onChange={(e) => onKind(e.target.value as "pant" | "shirt")} data-testid="panel-kind"><option value="pant">Pant</option><option value="shirt">Shirt</option></select><em />
        </label>
        <p className={unused ? "warn-text" : "ok"} data-testid="map-summary">
          {s.rows.length - unused === 0 && <b>None of these measurements are recognised, so editing them cannot change the drawing. </b>}
          {s.rows.length - unused} of {s.rows.length} measurements drive the drawing{unused ? ` · ${unused} not recognised: pick what each one controls below (or leave unused)` : ""}.
        </p>
        {fit && <p className={fit.converged ? "ok" : "warn-text"} data-testid="panel-fit">{fit.converged ? "Pattern matches every spec value" : "Some values are outside tolerance"} · worst {fit.max_abs_error.toFixed(3)} cm</p>}
        <fieldset>
          <legend>POM · size {specSize} ({u})</legend>
          {s.rows.map((r, ri) => {
            const v = r.values[si];
            const m = measured.get(r.code);
            return (
              <label key={r.code + r.name} className={"field spec-field" + (chosen(r) ? "" : " unmapped")} title={`${r.name_local ?? ""}${m ? ` · measured ${fmt(m.measured * f, 2)}` : ""}`}>
                <span>{r.name}<small className="pomcode"> {r.code}{r.tol_plus != null ? ` ±${fmt(r.tol_plus, 1)}` : ""}</small>
                  {m && !m.input_only && <small className={m.ok ? "ok" : "warn-text"}> drawn {fmt(m.measured * f, 2)}</small>}
                  <select className="map-select" value={chosen(r)} onChange={(e) => onMap(ri, e.target.value)} data-testid={`map-${r.code}`} aria-label={`What ${r.code} controls`}>
                    <option value="">{chosen(r) ? "— not used —" : "— not used (pick…) —"}</option>
                    {targets.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
                  </select>
                </span>
                <input type="number" step={0.1} data-testid={`pom-${r.code}`}
                  value={v == null ? "" : Number((v * f).toFixed(2))}
                  onChange={(e) => { const x = parseFloat(e.target.value); if (Number.isFinite(x) && x > 0) onSpecEdit(ri, si, x / f); }} />
                <em>{u}</em>
              </label>
            );
          })}
        </fieldset>
      </div>
    );
  }
  if (mode === "pds" && pds) {
    const qty = new Map((pattern?.pieces ?? []).map((p: any) => [p.name, p.qty ?? 1]));
    return (
      <div data-testid="source-panel">
        <div className="panel-head"><h2>PDS measurements</h2></div>
        <p className="hint"><b>{pds.style}</b> · {pds.source === "pds_binary" ? "read from the file's binary geometry" : "read from the marker preview (base size only)"}.<br />Piece sizes measured on the sew line, in {u}.</p>
        {pds.sizes.length > 1 && (
          <label className="field"><span>Size</span>
            <select value={pds.size} onChange={(e) => onPdsSize(e.target.value)} data-testid="pds-size">{pds.sizes.map((z) => <option key={z}>{z}</option>)}</select><em />
          </label>
        )}
        <div className="table-wrap"><table className="spec-table pds-table" data-testid="pds-pieces">
          <thead><tr><th>Piece</th><th>W</th><th>H</th><th>Perim.</th><th>Area</th><th>Qty</th></tr></thead>
          <tbody>
            {geo.map((g) => (
              <tr key={g.name}>
                <td>{g.name}</td><td>{fmt((g.max[0] - g.min[0]) * f, 2)}</td><td>{fmt((g.max[1] - g.min[1]) * f, 2)}</td>
                <td>{fmt(perimeter(g.sew as any) * f, 1)}</td><td>{fmt(g.area * f * f, 0)}</td><td>{qty.get(g.name) ?? 1}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        <p className="hint">W/H = sew-line width and height; area in {u}².</p>
      </div>
    );
  }
  return null;
}
