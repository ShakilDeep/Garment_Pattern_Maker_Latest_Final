import {api} from './api';
import type {MeasureBody, Measurement, StylePiece, StyleSummary, WalkPart, WalkResult} from './styleTypes';

// The V6 style routes (backend api/cad_routes.py) used by the project pattern view.
export const styleFromProject = (projectId: string) =>
  api<StyleSummary>('/styles', 'POST', {project_id: projectId});

export const stylePiece = (styleId: string, pieceId: string, size: string) =>
  api<StylePiece>(`/styles/${styleId}/pieces/${encodeURIComponent(pieceId)}?size=${encodeURIComponent(size)}`);

export const measure = (styleId: string, body: MeasureBody) =>
  api<Measurement>(`/styles/${styleId}/measure`, 'POST', body);

export const walk = (styleId: string, size: string, first: WalkPart[], second: WalkPart[]) =>
  api<WalkResult>(`/styles/${styleId}/walk`, 'POST', {size, first, second});
