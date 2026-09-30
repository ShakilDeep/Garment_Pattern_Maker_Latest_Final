import {afterEach, expect, it} from 'vitest';
import {cleanup, render, screen} from '@testing-library/react';
import PieceInspector from './PieceInspector';
import type {Piece} from './types';

afterEach(cleanup);

it('shows selected piece dimensions and empty guidance', () => {
  render(<PieceInspector piece={null} />);
  expect(screen.getByText(/Select a piece/)).toBeTruthy();
  const piece = {
    id: 'front', name: 'Front', width: 40.5, height: 70.25, area: 2000, perimeter: 220,
    quantity: 1, cut_on_fold: false, points: [], cut_points: [], grainline: [], notches: [],
  } as Piece;
  cleanup();
  render(<PieceInspector piece={piece} />);
  expect(screen.getByText('Front')).toBeTruthy();
  expect(screen.getByText('40.50 cm')).toBeTruthy();
  expect(screen.getByText('70.25 cm')).toBeTruthy();
});
