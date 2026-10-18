import type { Check, GeoPiece, PatternT } from "../types";
import type { EditAction, Selection } from "./PatternCanvas";
import { fmt } from "../util";

interface Props {
  pattern: PatternT;
  geo: GeoPiece[];
  checks: Check[];
  edited: boolean;
  selection: Selection;
  onSelect: (s: Selection) => void;
  onEdit: (a: EditAction) => void;
}

export default function Inspector({ pattern, geo, checks, edited, selection, onSelect, onEdit }: Props) {
  const pc = pattern.pieces.find((p) => p.name === selection.piece) ?? null;
  const g = geo.find((x) => x.name === selection.piece);
  const node = pc && selection.node !== null ? pc.nodes[selection.node] : null;
  const num = (v: string) => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };

  return (
    <aside className="panel inspector" aria-label="Inspector">
      <h2>Pieces</h2>
      <ul className="piece-list">
        {pattern.pieces.map((p) => {
          const gg = geo.find((x) => x.name === p.name);
          return (
            <li key={p.name}>
              <button className={selection.piece === p.name ? "row on" : "row"} onClick={() => onSelect({ piece: p.name, node: null })} data-testid={`piece-${p.name}`}>
                <span>{p.name}</span>
                <em>{gg ? `${fmt(gg.max[0] - gg.min[0])}×${fmt(gg.max[1] - gg.min[1])} cm` : ""}</em>
              </button>
            </li>
          );
        })}
      </ul>

      {pc && g ? (
        <>
          <h3>{pc.name}</h3>
          <dl className="kv">
            <dt>Area</dt><dd>{fmt(g.area, 0)} cm²</dd>
            <dt>Cut</dt><dd>{pc.mirror ? (pc.nodes.some((n) => n.edge === "cf" || n.edge === "cb") ? "1 on fold" : "2 (mirrored pair)") : `${pc.qty}`}</dd>
          </dl>
          <label className="field">
            <span>Seam allowance</span>
            <input type="number" min={0} max={10} step={0.25} value={pc.sa} data-testid="sa-input"
              onChange={(e) => { const v = num(e.target.value); if (v !== null && v >= 0 && v <= 10) onEdit({ type: "set_sa", piece: pc.name, sa: v }); }} />
            <em>cm</em>
          </label>

          {pc.darts.length > 0 && (
            <>
              <h4>Darts</h4>
              {pc.darts.map((d, i) => {
                const w = Math.hypot(d.b[0] - d.a[0], d.b[1] - d.a[1]);
                return (
                  <label className="field" key={i}>
                    <span>Dart {i + 1} intake</span>
                    <input type="number" min={0} max={15} step={0.25} value={Number(w.toFixed(2))} data-testid={`dart-${i}`}
                      onChange={(e) => { const v = num(e.target.value); if (v !== null && v >= 0 && v <= 15) onEdit({ type: "set_dart", piece: pc.name, dart: i, width: v }); }} />
                    <em>cm</em>
                  </label>
                );
              })}
            </>
          )}

          <h4>Point {node ? `#${selection.node}` : ""}</h4>
          {node && selection.node !== null ? (
            <>
              <div className="xy">
                <label className="field"><span>X</span><input type="number" step={0.1} value={Number(node.p[0].toFixed(2))} data-testid="node-x"
                  onChange={(e) => { const v = num(e.target.value); if (v !== null) onEdit({ type: "move_node", piece: pc.name, index: selection.node, x: v, y: node.p[1] }); }} /></label>
                <label className="field"><span>Y</span><input type="number" step={0.1} value={Number(node.p[1].toFixed(2))} data-testid="node-y"
                  onChange={(e) => { const v = num(e.target.value); if (v !== null) onEdit({ type: "move_node", piece: pc.name, index: selection.node, x: node.p[0], y: v }); }} /></label>
              </div>
              <p className="hint">Edge “{node.edge}” starts here.</p>
              <div className="btn-row">
                <button className="btn" onClick={() => onEdit({ type: "set_smooth", piece: pc.name, index: selection.node })}>Smooth</button>
                <button className="btn" onClick={() => onEdit({ type: "set_corner", piece: pc.name, index: selection.node })}>Corner</button>
                <button className="btn danger" data-testid="delete-node" onClick={() => { onEdit({ type: "delete_node", piece: pc.name, index: selection.node }); onSelect({ piece: pc.name, node: null }); }}>Delete</button>
              </div>
            </>
          ) : (
            <p className="hint">Select a piece, then click a point to edit it. Drag points or handles; double-click an edge to add a point. Hold Shift to snap to 0.5 cm.</p>
          )}

          {pc.notches.length > 0 && (
            <>
              <h4>Notches</h4>
              <ul className="chips">
                {pc.notches.map((n, i) => (
                  <li key={i}>
                    {pc.nodes[n.node]?.edge ?? "?"} @ {Math.round(n.t * 100)}%
                    <button aria-label="Remove notch" onClick={() => onEdit({ type: "remove_notch", piece: pc.name, index: i })}>×</button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      ) : (
        <p className="hint">Select a piece to see its details.</p>
      )}

      <h3>Fit checks</h3>
      {edited && <p className="hint warn">Checks describe the generated block; manual edits are not re-checked.</p>}
      <ul className="checks">
        {checks.map((c) => (
          <li key={c.name} className={c.ok ? "ok" : "bad"} data-testid="check">
            <span aria-hidden>{c.ok ? "✓" : "!"}</span>
            <div><b>{c.name}</b><small>{fmt(c.value, 2)} vs {fmt(c.expected, 2)} cm (±{c.tol})</small></div>
          </li>
        ))}
        {!checks.length && <li className="hint">No checks for this garment.</li>}
      </ul>
    </aside>
  );
}
