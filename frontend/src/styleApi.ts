import {api} from './api';
import type {MeasureBody, Measurement, StylePiece, StyleSummary, WalkPart, WalkResult} from './styleTypes';

// The V6 style routes (backend api/cad_routes.py) used by the block viewer.
export const draftBlock = (blockId: string) =>
  api<StyleSummary>('/styles/from-block', 'POST', {block_id: blockId});

export const stylePiece = (styleId: string, pieceId: string, size: string) =>
  api<StylePiece>(`/styles/${styleId}/pieces/${encodeURIComponent(pieceId)}?size=${encodeURIComponent(size)}`);

export const measure = (styleId: string, body: MeasureBody) =>
  api<Measurement>(`/styles/${styleId}/measure`, 'POST', body);

export const walk = (styleId: string, size: string, first: WalkPart[], second: WalkPart[]) =>
  api<WalkResult>(`/styles/${styleId}/walk`, 'POST', {size, first, second});
