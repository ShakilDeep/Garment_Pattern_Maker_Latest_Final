import type {StylePiece, StyleSummary} from './styleTypes';

// A small V6 piece as the backend sends it: a line, a cubic, a notch slit, grain and a cut outline.
export const yoke: StylePiece = {
  id: 'back_YK', name: 'back YK',
  points: [{id: 'CB_neck', x: 12, y: 0}, {id: 'HPS', x: 17, y: 9}, {id: 'SP', x: 12.5, y: 26}, {id: 'CB_yoke', x: 0, y: 0}],
  outline: [
    {id: 'CB_neck:HPS', type: 'cubic', start: 'CB_neck', end: 'HPS', start_handle: [0.1, 6], end_handle: [-5, -1.6]},
    {id: 'HPS:SP', type: 'line', start: 'HPS', end: 'SP'},
    {id: 'SP:CB_yoke', type: 'line', start: 'SP', end: 'CB_yoke'},
    {id: 'CB_yoke:CB_neck', type: 'line', start: 'CB_yoke', end: 'CB_neck'},
  ],
  cut: {single: 0, mirrored_pairs: 0, on_fold: 2},
  grainline: [[3, 10], [9, 10]], fold: 'CB_yoke:CB_neck',
  notch_marks: [{id: 'shoulder_notch', at: [16.6, 10.4], tip: [15.9, 10.6]}],
  cut_outline: [[-1, -1], [18, -1], [18, 27], [-1, 27]],
};

export const summary: StyleSummary = {id: 'style-1', name: 'shirt_1078375 L', sizes: ['L'], base_size: 'L',
  piece_ids: ['back_YK']};
