import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import ProjectPatternView, {resetProjectStyles} from './ProjectPatternView';
import * as styleApi from './styleApi';
import {yoke} from './blockViewerFixture';
import type {StyleSummary} from './styleTypes';

vi.mock('./styleApi');
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); resetProjectStyles(); });

const front = {...yoke, id: 'front', name: 'Front', cut: {single: 2, mirrored_pairs: 0, on_fold: 0}};
const summary: StyleSummary = {id: 'style-p', name: 'Book2', sizes: ['M', 'L'], base_size: 'L',
  graded_sizes: ['L'], piece_ids: ['front']};
const layer = (name: string) => document.querySelectorAll(`[data-layer="${name}"]`).length;

const view = (props: Partial<Parameters<typeof ProjectPatternView>[0]> = {}) =>
  <ProjectPatternView projectId="p1" version="v1" size="L" busy={false} select={vi.fn()} download={vi.fn()} {...props} />;

async function shown(size = 'L', version = 'v1', select = vi.fn(), style = summary) {
  vi.mocked(styleApi.styleFromProject).mockResolvedValue(style);
  vi.mocked(styleApi.stylePiece).mockResolvedValue(front);
  render(view({size, version, select}));
  await screen.findAllByRole('button', {name: 'Select Front'});
  return select;
}

it("draws the project's own pieces with every layer, as the block viewer does", async () => {
  await shown();
  expect(styleApi.styleFromProject).toHaveBeenCalledWith('p1');
  expect(styleApi.stylePiece).toHaveBeenCalledWith('style-p', 'front', 'L');
  expect(['cut', 'sew', 'notches', 'grain', 'labels'].map(layer)).toEqual([1, 1, 1, 1, 1]);
  expect(screen.getByText('Front · cut 2')).toBeTruthy();
  fireEvent.click(screen.getByLabelText('Cut line'));
  expect(layer('cut')).toBe(0);
});

it('reports the selected piece by name and opens its measure tool', async () => {
  const select = await shown();
  fireEvent.click(screen.getByRole('button', {name: 'Select Front'}));
  expect(select).toHaveBeenCalledWith('Front');
  expect(screen.getByRole('region', {name: 'Measure Front'})).toBeTruthy();
});

it('shows an ungraded size at the base size and says so', async () => {
  await shown('M');
  expect(styleApi.stylePiece).toHaveBeenCalledWith('style-p', 'front', 'L');
  expect(screen.getByText('Size M is not graded yet; showing base size L.')).toBeTruthy();
});

it('reuses the style of an unchanged project instead of creating another', async () => {
  await shown();
  cleanup();
  await shown();
  expect(styleApi.styleFromProject).toHaveBeenCalledTimes(1);
  cleanup();
  await shown('L', 'v2');
  expect(styleApi.styleFromProject).toHaveBeenCalledTimes(2);
});

it('shows the backend error when the style cannot be made', async () => {
  vi.mocked(styleApi.styleFromProject).mockRejectedValue(new Error('Generate a current pattern first'));
  render(view());
  expect((await screen.findByRole('alert')).textContent).toBe('Generate a current pattern first');
});

it("downloads the project's graded DXF-AAMA + RUL through the project export", async () => {
  const download = vi.fn();
  vi.mocked(styleApi.styleFromProject).mockResolvedValue(summary);
  vi.mocked(styleApi.stylePiece).mockResolvedValue(front);
  render(view({download}));
  fireEvent.click(await screen.findByRole('button', {name: 'Download graded DXF-AAMA + RUL'}));
  expect(download).toHaveBeenCalledTimes(1);
});

it('walks the sleeve cap only when the style has the 1078375 pieces it reads', async () => {
  await shown();
  expect(screen.queryByRole('region', {name: 'Sleeve cap walk'})).toBeNull();
  cleanup();
  await shown('L', 'v3', vi.fn(), {...summary, piece_ids: ['FRT', 'back', 'back_YK', 'Sleeve']});
  expect(screen.getByRole('region', {name: 'Sleeve cap walk'})).toBeTruthy();
});
