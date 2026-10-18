import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GeoPiece, PatternT, V2 } from "../types";
import { layout, nearestOnPolyline, signedArea } from "../util";

export interface Selection { piece: string | null; node: number | null }
export type EditAction = Record<string, unknown>;

export interface Overlay { label: string; color: string; geo: GeoPiece[] }

interface Props {
  pattern: PatternT;
  geo: GeoPiece[];
  selection: Selection;
  onSelect: (s: Selection) => void;
  onEditBegin: () => void;
  onEdit: (a: EditAction, live: boolean) => void;
  showCut: boolean;
  showNodes: boolean;
  showSeamTags: boolean;
  overlays?: Overlay[];
  onlyPiece?: string | null;
}

interface View { x: number; y: number; w: number; h: number }
type Drag =
  | { kind: "node" | "in" | "out"; piece: string; idx: number; ox: number }
  | { kind: "pan"; sx: number; sy: number; v: View; scale: number }
  | null;

export default function PatternCanvas({ pattern, geo, selection, onSelect, onEditBegin, onEdit, showCut, showNodes, showSeamTags, overlays, onlyPiece }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [view, setView] = useState<View>({ x: -10, y: -60, w: 200, h: 120 });
  const drag = useRef<Drag>(null);
  const visible = useMemo(() => geo.filter((g) => !onlyPiece || g.name === onlyPiece), [geo, onlyPiece]);
  const offsets = useMemo(() => layout(visible), [visible]);

  const fit = useCallback(() => {
    if (!visible.length) return;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    visible.forEach((g, i) => {
      for (const p of g.cut) {
        x0 = Math.min(x0, p[0] + offsets[i]); x1 = Math.max(x1, p[0] + offsets[i]);
        y0 = Math.min(y0, -p[1]); y1 = Math.max(y1, -p[1]);
      }
    });
    const pad = 8;
    const el = svgRef.current;
    const aspect = el && el.clientHeight > 0 ? el.clientWidth / el.clientHeight : 1.6;
    let w = x1 - x0 + 2 * pad, h = y1 - y0 + 2 * pad;
    if (w / h < aspect) w = h * aspect; else h = w / aspect;
    setView({ x: (x0 + x1) / 2 - w / 2, y: (y0 + y1) / 2 - h / 2, w, h });
  }, [visible, offsets]);

  const fitKey = visible.map((g) => g.name).join("|") + pattern.garment + (onlyPiece ?? "");
  useEffect(() => { fit(); /* refit when the set of pieces changes, not on every edit */ // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey]);

  const scaleOf = () => {
    const el = svgRef.current;
    return el && el.clientWidth ? view.w / el.clientWidth : 0.2;
  };

  function toUser(clientX: number, clientY: number): V2 {
    const el = svgRef.current!;
    const m = el.getScreenCTM();
    if (!m) return [0, 0];
    const pt = new DOMPoint(clientX, clientY).matrixTransform(m.inverse());
    return [pt.x, pt.y];
  }
  const toLocal = (clientX: number, clientY: number, ox: number): V2 => {
    const [ux, uy] = toUser(clientX, clientY);
    return [ux - ox, -uy];
  };

  function onWheel(e: React.WheelEvent) {
    const [ux, uy] = toUser(e.clientX, e.clientY);
    const k = Math.exp(e.deltaY * 0.0015);
    setView((v) => {
      const w = Math.max(10, Math.min(2000, v.w * k)), h = v.h * (w / v.w);
      return { x: ux - (ux - v.x) * (w / v.w), y: uy - (uy - v.y) * (h / v.h), w, h };
    });
  }

  function onBgDown(e: React.PointerEvent) {
    if ((e.target as Element).closest("[data-hit]")) return;
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    drag.current = { kind: "pan", sx: e.clientX, sy: e.clientY, v: view, scale: scaleOf() };
    onSelect({ piece: selection.piece, node: null });
  }

  function onMove(e: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    if (d.kind === "pan") {
      setView({ ...d.v, x: d.v.x - (e.clientX - d.sx) * d.scale, y: d.v.y - (e.clientY - d.sy) * d.scale });
      return;
    }
    let [x, y] = toLocal(e.clientX, e.clientY, d.ox);
    if (e.shiftKey) { x = Math.round(x * 2) / 2; y = Math.round(y * 2) / 2; }
    if (d.kind === "node") onEdit({ type: "move_node", piece: d.piece, index: d.idx, x, y }, true);
    else onEdit({ type: "move_handle", piece: d.piece, index: d.idx, out: d.kind === "out", x, y }, true);
  }
  const endDrag = (e: React.PointerEvent) => {
    if (drag.current) { try { (e.currentTarget as Element).releasePointerCapture(e.pointerId); } catch { /* not captured */ } }
    drag.current = null;
  };

  const r = Math.max(0.45, scaleOf() * 5);
  const sw = Math.max(0.12, scaleOf() * 1.4);
  const P = (p: V2) => `${p[0]},${-p[1]}`;
  const pts = (a: V2[]) => a.map(P).join(" ");

  return (
    <div className="canvas-wrap">
      <svg
        ref={svgRef} className="canvas" viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`} role="img" aria-label="2D pattern editor"
        onWheel={onWheel} onPointerDown={onBgDown} onPointerMove={onMove} onPointerUp={endDrag} onPointerCancel={endDrag}
        data-testid="canvas"
      >
        <defs>
          <pattern id="g1" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M1 0H0V1" fill="none" stroke="var(--grid-minor)" strokeWidth={0.04} /></pattern>
          <pattern id="g10" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="var(--grid-major)" strokeWidth={0.08} /></pattern>
        </defs>
        <rect x={view.x - 5} y={view.y - 5} width={view.w + 10} height={view.h + 10} fill="url(#g10)" />
        {view.w < 90 && <rect x={view.x - 5} y={view.y - 5} width={view.w + 10} height={view.h + 10} fill="url(#g1)" />}

        {visible.map((g, gi) => {
          const pc = pattern.pieces.find((p) => p.name === g.name);
          if (!pc) return null;
          const ox = offsets[gi];
          const sel = selection.piece === g.name;
          const ccw = signedArea(g.sew) > 0;
          return (
            <g key={g.name} transform={`translate(${ox},0)`} data-piece={g.name}>
              {showCut && <polygon points={pts(g.cut)} fill="none" stroke="var(--cut)" strokeWidth={sw} strokeDasharray={`${sw * 6} ${sw * 3}`} />}
              <polygon
                points={pts(g.sew)} fill={sel ? "var(--piece-sel)" : "var(--piece)"} stroke="none" data-hit
                onPointerDown={(e) => { e.stopPropagation(); onSelect({ piece: g.name, node: null }); }}
              />
              {overlays?.map((o) => {
                const og = o.geo.find((x) => x.name === g.name);
                return og ? <polygon key={o.label} points={pts(og.sew)} fill="none" stroke={o.color} strokeWidth={sw * 1.2} opacity={0.9} /> : null;
              })}
              {g.edges.map((e, ei) => (
                <g key={ei}>
                  <polyline points={pts(e.pts)} fill="none" stroke={sel ? "var(--ink)" : "var(--ink-soft)"} strokeWidth={sw * 1.4} strokeLinejoin="round" />
                  <polyline
                    points={pts(e.pts)} fill="none" stroke="transparent" strokeWidth={Math.max(r * 2, 1.4)} data-hit data-edge={ei}
                    onPointerDown={(ev) => { ev.stopPropagation(); onSelect({ piece: g.name, node: null }); }}
                    onDoubleClick={(ev) => {
                      const q = toLocal(ev.clientX, ev.clientY, ox);
                      const { t } = nearestOnPolyline(e.pts, q);
                      onEditBegin();
                      onEdit({ type: "split_edge", piece: g.name, edge: ei, t }, false);
                    }}
                  >
                    <title>Edge “{e.tag}” — {e.len.toFixed(1)} cm (double-click to add a point)</title>
                  </polyline>
                  {showSeamTags && e.pts.length > 1 && (
                    <text x={e.pts[Math.floor(e.pts.length / 2)][0]} y={-e.pts[Math.floor(e.pts.length / 2)][1]} fontSize={r * 1.7} fill="var(--accent)" textAnchor="middle" pointerEvents="none">{e.tag}</text>
                  )}
                </g>
              ))}
              {pc.internal.map((l, i) => <polyline key={`i${i}`} points={pts(l)} fill="none" stroke="var(--dart)" strokeWidth={sw} />)}
              {pc.drills.map((d, i) => <circle key={`d${i}`} cx={d[0]} cy={-d[1]} r={r * 0.4} fill="var(--dart)" />)}
              <line x1={pc.grain[0][0]} y1={-pc.grain[0][1]} x2={pc.grain[1][0]} y2={-pc.grain[1][1]} stroke="var(--ink-soft)" strokeWidth={sw} markerEnd="url(#arrow)" />
              {g.notches.map((n, i) => {
                const inward: V2 = ccw ? [-n.tan[1], n.tan[0]] : [n.tan[1], -n.tan[0]];
                return <line key={`n${i}`} x1={n.p[0]} y1={-n.p[1]} x2={n.p[0] + inward[0] * 0.9} y2={-(n.p[1] + inward[1] * 0.9)} stroke="var(--ink)" strokeWidth={sw * 1.6} />;
              })}
              <text x={(g.min[0] + g.max[0]) / 2} y={-(g.min[1] + g.max[1]) / 2 + 3} fontSize={Math.max(1.8, r * 2.4)} textAnchor="middle" fill="var(--ink-soft)" pointerEvents="none" style={{ userSelect: "none" }}>
                {g.name}{pc.mirror ? " ×2" : ""}
              </text>

              {showNodes && sel && pc.nodes.map((n, i) => {
                const isSel = selection.node === i;
                const hin: V2 | null = n.hin ? [n.p[0] + n.hin[0], n.p[1] + n.hin[1]] : null;
                const hout: V2 | null = n.hout ? [n.p[0] + n.hout[0], n.p[1] + n.hout[1]] : null;
                return (
                  <g key={i}>
                    {isSel && hin && <line x1={n.p[0]} y1={-n.p[1]} x2={hin[0]} y2={-hin[1]} stroke="var(--accent)" strokeWidth={sw} />}
                    {isSel && hout && <line x1={n.p[0]} y1={-n.p[1]} x2={hout[0]} y2={-hout[1]} stroke="var(--accent)" strokeWidth={sw} />}
                    {isSel && hin && <rect x={hin[0] - r * 0.7} y={-hin[1] - r * 0.7} width={r * 1.4} height={r * 1.4} fill="var(--bg)" stroke="var(--accent)" strokeWidth={sw} data-hit style={{ cursor: "move" }}
                      onPointerDown={(e) => { e.stopPropagation(); (e.currentTarget.ownerSVGElement as SVGSVGElement).setPointerCapture?.(e.pointerId); onEditBegin(); drag.current = { kind: "in", piece: g.name, idx: i, ox }; }} />}
                    {isSel && hout && <rect x={hout[0] - r * 0.7} y={-hout[1] - r * 0.7} width={r * 1.4} height={r * 1.4} fill="var(--bg)" stroke="var(--accent)" strokeWidth={sw} data-hit style={{ cursor: "move" }}
                      onPointerDown={(e) => { e.stopPropagation(); (e.currentTarget.ownerSVGElement as SVGSVGElement).setPointerCapture?.(e.pointerId); onEditBegin(); drag.current = { kind: "out", piece: g.name, idx: i, ox }; }} />}
                    <circle
                      cx={n.p[0]} cy={-n.p[1]} r={isSel ? r * 1.25 : r} fill={isSel ? "var(--accent)" : "var(--bg)"} stroke="var(--accent)" strokeWidth={sw * 1.2}
                      data-hit data-node={i} style={{ cursor: "grab" }}
                      onPointerDown={(e) => {
                        e.stopPropagation();
                        (e.currentTarget.ownerSVGElement as SVGSVGElement).setPointerCapture?.(e.pointerId);
                        onSelect({ piece: g.name, node: i });
                        onEditBegin();
                        drag.current = { kind: "node", piece: g.name, idx: i, ox };
                      }}
                    ><title>Point {i} — drag to move</title></circle>
                  </g>
                );
              })}
            </g>
          );
        })}
        <defs>
          <marker id="arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L6 3L0 6z" fill="var(--ink-soft)" /></marker>
        </defs>
      </svg>
      <div className="canvas-tools">
        <button className="btn ghost" onClick={fit} title="Fit to window">Fit</button>
        <span className="legend">
          <i style={{ background: "var(--cut)" }} />cut line <i style={{ background: "var(--ink)" }} />sew line <i style={{ background: "var(--dart)" }} />darts
        </span>
      </div>
      {!visible.length && <div className="empty">No pieces yet.</div>}
    </div>
  );
}
