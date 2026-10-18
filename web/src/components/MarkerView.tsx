import { useEffect, useMemo, useState } from "react";
import type { PatternT } from "../types";
import { download, fmt } from "../util";

interface NestOut { svg: string; dxf: string; length: number; width: number; efficiency: number; verified: boolean; warnings: string[]; unplaced: unknown[] }
interface Props {
  call: <T = any>(req: Record<string, unknown>) => Promise<T>;
  pattern: PatternT | null;
  sizes?: { label: string; pattern: PatternT }[];
  onError: (m: string) => void;
}

export default function MarkerView({ call, pattern, sizes, onError }: Props) {
  const [width, setWidth] = useState(150);
  const [gap, setGap] = useState(0.5);
  const [iters, setIters] = useState(200);
  const [mirror, setMirror] = useState(true);
  const [nap, setNap] = useState(false);
  const [which, setWhich] = useState("current");
  const [qty, setQty] = useState<Record<string, number>>({});
  const [out, setOut] = useState<NestOut | null>(null);
  const [busy, setBusy] = useState(false);

  const target = useMemo(() => (which === "current" ? pattern : sizes?.find((s) => s.label === which)?.pattern ?? pattern), [which, pattern, sizes]);
  useEffect(() => { setOut(null); }, [target]);
  const svgUrl = useMemo(() => (out ? URL.createObjectURL(new Blob([out.svg], { type: "image/svg+xml" })) : null), [out]);
  useEffect(() => () => { if (svgUrl) URL.revokeObjectURL(svgUrl); }, [svgUrl]);

  async function run() {
    if (!target) return;
    setBusy(true);
    try {
      const q: Record<string, number> = {};
      for (const p of target.pieces) if (qty[p.name] != null) q[p.name] = qty[p.name];
      const r = await call<NestOut>({ op: "nest", pattern: target, qty: q, style: target.style || "MARKER", opts: { fabric_width: width, gap, iters, pair_mirroring: mirror, one_way_nap: nap } });
      setOut(r);
    } catch (e) { onError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }

  return (
    <div className="marker-view" data-testid="marker-view">
      <div className="marker-controls">
        {sizes && sizes.length > 0 && (
          <label>Size <select value={which} onChange={(e) => setWhich(e.target.value)}><option value="current">current pattern</option>{sizes.map((s) => <option key={s.label}>{s.label}</option>)}</select></label>
        )}
        <label>Fabric width (cm) <input type="number" min={20} max={400} value={width} onChange={(e) => setWidth(+e.target.value)} data-testid="marker-width" /></label>
        <label>Gap (cm) <input type="number" min={0} max={5} step={0.1} value={gap} onChange={(e) => setGap(+e.target.value)} /></label>
        <label>Effort <input type="number" min={0} max={1000} step={50} value={iters} onChange={(e) => setIters(+e.target.value)} /></label>
        <label className="inline"><input type="checkbox" checked={mirror} onChange={(e) => setMirror(e.target.checked)} /> Mirror pairs</label>
        <label className="inline"><input type="checkbox" checked={nap} onChange={(e) => setNap(e.target.checked)} /> One-way fabric</label>
        <button className="btn primary" disabled={busy || !target} onClick={() => void run()} data-testid="run-nest">{busy ? "Nesting…" : "Make marker"}</button>
      </div>
      {target && (
        <details className="qty">
          <summary>Pieces per garment</summary>
          <div className="qty-grid">
            {target.pieces.map((p) => (
              <label key={p.name}>{p.name} <input type="number" min={0} max={20} value={qty[p.name] ?? p.qty} onChange={(e) => setQty((q) => ({ ...q, [p.name]: +e.target.value }))} /></label>
            ))}
          </div>
        </details>
      )}
      {out && (
        <div className="marker-result" data-testid="marker-result">
          <div className="stats">
            Length <b>{fmt(out.length, 1)} cm</b> · Width {fmt(out.width, 1)} cm · Efficiency <b>{fmt(out.efficiency * 100, 1)}%</b> · {out.verified ? <span className="ok">overlap check passed</span> : <span className="warn-text">overlap check FAILED</span>}
            <span className="grow" />
            <button className="btn" onClick={() => download(`${target?.style || "marker"}_marker.svg`, out.svg, "image/svg+xml")}>SVG</button>
            <button className="btn" onClick={() => download(`${target?.style || "marker"}_marker.dxf`, out.dxf)}>DXF</button>
          </div>
          {out.warnings.length > 0 && <ul className="warnlist">{out.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>}
          {svgUrl && <img className="marker-img" src={svgUrl} alt="Marker layout" />}
        </div>
      )}
      {!out && <p className="hint pad">Lays every piece (× quantity, mirrored pairs) on the fabric width to minimise the length used. Heuristic nesting; the independent checker guarantees no overlaps, gap and grain rules.</p>}
    </div>
  );
}
