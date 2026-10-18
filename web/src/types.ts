export type V2 = [number, number];

export interface NodeT { p: V2; hin?: V2; hout?: V2; edge: string; sa?: number }
export interface NotchT { node: number; t: number; kind: string }
export interface DartT { apex: V2; a: V2; b: V2 }
export interface PieceT {
  name: string; zone: string; nodes: NodeT[]; grain: [V2, V2]; notches: NotchT[]; darts: DartT[];
  internal: V2[][]; drills: V2[]; sa: number; mirror: boolean; qty: number; material: string;
}
export interface SeamT { a: string; at: string; b: string; bt: string; rev: boolean }
export interface PatternT { style: string; size: string; garment: string; pieces: PieceT[]; seams: SeamT[] }

export interface EdgeGeo { tag: string; len: number; pts: V2[] }
export interface GeoPiece {
  name: string; sew: V2[]; cut: V2[]; min: V2; max: V2; area: number;
  notches: { p: V2; tan: V2; kind: string }[]; edges: EdgeGeo[];
}

export type Measurements = Record<string, number>;
export interface Check { name: string; value: number; expected: number; tol: number; ok: boolean }
export interface GradedSize {
  label: string; step: number; measurements: Measurements; pattern: PatternT;
  table: { piece: string; deltas: V2[] }[];
  fit?: unknown[]; max_abs_error?: number; converged?: boolean;
}
export interface Column { cx: number; cz: number; ys: number[]; a: number[]; b: number[] }
export interface DrapeMesh { name: string; zone: string; side: number; tris: number[]; frames: number[][] }
export interface DrapeResult {
  meshes: DrapeMesh[];
  body: { torso: Column; skirt_core: Column; legs: Column[]; arms: Column[] };
  stats: { particles: number; max_penetration: number; stitch_mean_final: number; stitch_max_final: number; max_stretch_ratio: number; stretch_p95: number; max_drift: number; max_sag: number; finite: boolean };
}
