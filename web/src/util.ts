import type { GeoPiece, Measurements, V2 } from "./types";

export const MEASURE_GROUPS: { title: string; keys: [string, string][] }[] = [
  { title: "Torso", keys: [["bust", "Bust"], ["waist", "Waist"], ["hip", "Hip"], ["back_length", "Back length (nape→waist)"], ["shoulder_width", "Shoulder width"], ["neck", "Neck girth"]] },
  { title: "Arm", keys: [["bicep", "Bicep"], ["wrist", "Wrist"], ["sleeve_length", "Sleeve length"]] },
  { title: "Lower body", keys: [["waist_to_hip", "Waist→hip"], ["skirt_length", "Skirt length"], ["rise", "Rise (waist→crotch)"], ["inseam", "Inseam"], ["thigh", "Thigh"], ["knee", "Knee"], ["ankle", "Ankle"]] },
  { title: "General", keys: [["height", "Height"]] },
];

export const SIZE_TEMPLATE_CSV =
  "measurement,value_cm\nbust,92\nwaist,74\nhip,98\nback_length,41\nshoulder_width,38\nneck,37\nbicep,29\nwrist,16\nsleeve_length,60\nwaist_to_hip,20\nskirt_length,60\nrise,27\ninseam,78\nthigh,57\nknee,38\nankle,23\nheight,168\n";

export function download(name: string, data: string | Blob, type = "text/plain") {
  const blob = typeof data === "string" ? new Blob([data], { type }) : data;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const CM_PER_IN = 2.54;
export const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : "–");

/** Horizontal layout: x offset per piece so pieces sit side by side. */
export function layout(geo: GeoPiece[], gap = 10): number[] {
  const out: number[] = [];
  let x = 0;
  for (const g of geo) {
    let lo = Infinity, hi = -Infinity;
    for (const p of g.cut) { lo = Math.min(lo, p[0]); hi = Math.max(hi, p[0]); }
    out.push(x - lo);
    x += hi - lo + gap;
  }
  return out;
}

export function signedArea(p: V2[]): number {
  let s = 0;
  for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; s += a[0] * b[1] - b[0] * a[1]; }
  return s / 2;
}

export function nearestOnPolyline(pts: V2[], q: V2): { t: number; d: number } {
  let best = { t: 0, d: Infinity };
  let total = 0;
  const lens: number[] = [];
  for (let i = 0; i + 1 < pts.length; i++) { const l = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]); lens.push(l); total += l; }
  let acc = 0;
  for (let i = 0; i + 1 < pts.length; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    const dx = bx - ax, dy = by - ay;
    const l2 = dx * dx + dy * dy || 1e-12;
    const u = Math.max(0, Math.min(1, ((q[0] - ax) * dx + (q[1] - ay) * dy) / l2));
    const d = Math.hypot(ax + dx * u - q[0], ay + dy * u - q[1]);
    if (d < best.d) best = { d, t: total > 0 ? (acc + lens[i] * u) / total : 0 };
    acc += lens[i];
  }
  return best;
}

export function measurementsToDisplay(m: Measurements, inches: boolean): Measurements {
  if (!inches) return m;
  return Object.fromEntries(Object.entries(m).map(([k, v]) => [k, v / CM_PER_IN]));
}

export const PIECE_COLORS = ["#2f7d6d", "#c46a3a", "#4b6fb5", "#9c5ba0", "#b99a2c", "#3a8fa3", "#a34f57", "#6b8e3d"];
export function pieceColor(name: string): string {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PIECE_COLORS[h % PIECE_COLORS.length];
}
