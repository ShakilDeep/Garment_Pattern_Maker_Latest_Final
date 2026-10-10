import type {StylePiece, StyleSegment, XY} from './styleTypes';

// SVG path syntax for the backend's typed segments: drawing only, no geometry decisions.
// A cubic's handles are offsets from their own end point; an arc is a DXF bulge (tan of a quarter angle).
const fmt = (v: number) => Number(v.toFixed(4));

function arcCommand(start: XY, end: XY, bulge: number): string {
  const chord = Math.hypot(end[0] - start[0], end[1] - start[1]);
  const radius = (chord * (1 + bulge * bulge)) / (4 * Math.abs(bulge));
  const large = Math.abs(bulge) > 1 ? 1 : 0;
  const sweep = bulge > 0 ? 1 : 0;
  return `A ${fmt(radius)} ${fmt(radius)} 0 ${large} ${sweep} ${fmt(end[0])} ${fmt(end[1])}`;
}

export function segmentCommand(segment: StyleSegment, at: Record<string, XY>): string {
  const [start, end] = [at[segment.start], at[segment.end]];
  if (segment.type === 'cubic') {
    const c1: XY = [start[0] + segment.start_handle[0], start[1] + segment.start_handle[1]];
    const c2: XY = [end[0] + segment.end_handle[0], end[1] + segment.end_handle[1]];
    return `C ${fmt(c1[0])} ${fmt(c1[1])} ${fmt(c2[0])} ${fmt(c2[1])} ${fmt(end[0])} ${fmt(end[1])}`;
  }
  if (segment.type === 'arc') return arcCommand(start, end, segment.bulge);
  return `L ${fmt(end[0])} ${fmt(end[1])}`;
}

export function pointMap(piece: StylePiece): Record<string, XY> {
  return Object.fromEntries(piece.points.map((p) => [p.id, [p.x, p.y] as XY]));
}

export function sewPath(piece: StylePiece): string {
  const at = pointMap(piece);
  const first = at[piece.outline[0].start];
  return `M ${fmt(first[0])} ${fmt(first[1])} ${piece.outline.map((s) => segmentCommand(s, at)).join(' ')} Z`;
}

export function ringPath(ring: XY[]): string {
  return `M ${ring.map(([x, y]) => `${fmt(x)} ${fmt(y)}`).join(' L ')} Z`;
}

// The drawing frame: the cut outline (or the points) with a margin, for the SVG viewBox (y is flipped).
export function frame(piece: StylePiece, margin = 2): {x: number; y: number; width: number; height: number} {
  const all: XY[] = piece.cut_outline ?? piece.points.map((p) => [p.x, p.y] as XY);
  const xs = all.map((p) => p[0]);
  const ys = all.map((p) => p[1]);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  return {x: minX - margin, y: -maxY - margin, width: maxX - minX + 2 * margin, height: maxY - minY + 2 * margin};
}
