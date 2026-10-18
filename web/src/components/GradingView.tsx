import type { GradedSize, GeoPiece } from "../types";
import { fmt } from "../util";

export const SIZE_COLORS = ["#4b6fb5", "#2f7d6d", "#c46a3a", "#9c5ba0", "#b99a2c", "#3a8fa3", "#a34f57", "#6b8e3d", "#555"];

export const STEP_CHOICES: { step: number; label: string }[] = [
  { step: -3, label: "XXS" }, { step: -2, label: "XS" }, { step: -1, label: "S" }, { step: 0, label: "M" },
  { step: 1, label: "L" }, { step: 2, label: "XL" }, { step: 3, label: "XXL" },
];

interface Props {
  steps: number[];
  onSteps: (s: number[]) => void;
  sizes: GradedSize[];
  geos: Record<string, GeoPiece[]>;
  pieceName: string | null;
  busy: boolean;
  onRun: () => void;
}

export default function GradingView({ steps, onSteps, sizes, geos, pieceName, busy, onRun }: Props) {
  const toggle = (s: number) => {
    const next = steps.includes(s) ? steps.filter((x) => x !== s) : [...steps, s].sort((a, b) => a - b);
    if (next.length) onSteps(next);
  };
  const piece = pieceName ?? sizes[0]?.table[0]?.piece ?? null;
  return (
    <div className="grading">
      <div className="grading-head">
        <fieldset className="steps">
          <legend>Size range (the current measurements are size M)</legend>
          {STEP_CHOICES.map((c) => (
            <label key={c.step} className="chip-check">
              <input type="checkbox" checked={steps.includes(c.step)} onChange={() => toggle(c.step)} data-testid={`step-${c.step}`} />
              <span>{c.label}</span>
            </label>
          ))}
        </fieldset>
        <button className="btn primary" disabled={busy} onClick={onRun} data-testid="run-grade">{busy ? "Grading…" : "Grade sizes"}</button>
      </div>
      <p className="hint">Sizes are re-drafted from the measurement increments below, so every size keeps the block's construction rules. The overlay on the 2D tab shows all graded sizes nested on a common origin.</p>

      {sizes.length > 0 && (
        <div className="table-wrap">
          <table data-testid="grade-table">
            <thead>
              <tr><th>Size</th><th>Bust</th><th>Waist</th><th>Hip</th>{piece && <th>{piece}: width × height</th>}</tr>
            </thead>
            <tbody>
              {sizes.map((s, i) => {
                const g = geos[s.label]?.find((x) => x.name === piece);
                return (
                  <tr key={s.label}>
                    <td><i className="swatch" style={{ background: SIZE_COLORS[i % SIZE_COLORS.length] }} />{s.label}{s.step === 0 ? " (base)" : ""}</td>
                    <td>{fmt(s.measurements.bust)}</td><td>{fmt(s.measurements.waist)}</td><td>{fmt(s.measurements.hip)}</td>
                    {piece && <td>{g ? `${fmt(g.max[0] - g.min[0])} × ${fmt(g.max[1] - g.min[1])}` : "–"}</td>}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {sizes.length > 0 && piece && (
        <details>
          <summary>Per-point grade rules for {piece} (Δx, Δy in cm vs. base)</summary>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Pt</th>{sizes.map((s) => <th key={s.label}>{s.label}</th>)}</tr></thead>
              <tbody>
                {(sizes[0].table.find((t) => t.piece === piece)?.deltas ?? []).map((_, pi) => (
                  <tr key={pi}>
                    <td>{pi}</td>
                    {sizes.map((s) => {
                      const d = s.table.find((t) => t.piece === piece)?.deltas[pi];
                      return <td key={s.label}>{d ? `${fmt(d[0], 2)}, ${fmt(d[1], 2)}` : "–"}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
