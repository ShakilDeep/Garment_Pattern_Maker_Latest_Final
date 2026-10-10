// V6 style DTOs (backend api/models/cad_*.py). Geometry is decided by the backend; the viewer only draws it.
export type XY = [number, number];

export type StylePoint = {id: string; x: number; y: number};

type Ends = {id: string; start: string; end: string};
export type StyleSegment =
  | (Ends & {type: 'line'})
  | (Ends & {type: 'cubic'; start_handle: XY; end_handle: XY})
  | (Ends & {type: 'arc'; bulge: number});

export type NotchMark = {id: string; at: XY; tip: XY};

export type StylePiece = {
  id: string;
  name: string;
  points: StylePoint[];
  outline: StyleSegment[];
  cut: {single: number; mirrored_pairs: number; on_fold: number};
  grainline: [XY, XY] | null;
  fold: string | null;
  notch_marks: NotchMark[];
  cut_outline: XY[] | null;
};

export type StyleSummary = {id: string; name: string; sizes: string[]; base_size: string; piece_ids: string[]};

export type MeasureKind = 'distance' | 'path' | 'angle' | 'area' | 'perimeter';
export type MeasureBody = {
  size: string; piece_id: string; kind: MeasureKind;
  points?: string[]; edges?: string[]; point?: string; outline?: 'sew' | 'cut';
};
export type Measurement = {kind: MeasureKind; value: number; unit: 'cm' | 'deg' | 'cm2'};

export type WalkPart = {piece_id: string; points: string[]};
export type WalkResult = {first_cm: number; second_cm: number; difference_cm: number};

export type Layer = 'cut' | 'sew' | 'notches' | 'grain' | 'labels';
export const LAYERS: Layer[] = ['cut', 'sew', 'notches', 'grain', 'labels'];
