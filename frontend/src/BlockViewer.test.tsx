import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import BlockViewer from './BlockViewer';
import * as styleApi from './styleApi';
import * as api from './api';
import {summary, yoke} from './blockViewerFixture';

vi.mock('./styleApi');
vi.mock('./api');
afterEach(cleanup);
beforeEach(() => vi.resetAllMocks());

const layer = (name: string) => document.querySelectorAll(`[data-layer="${name}"]`).length;

async function drafted() {
  vi.mocked(styleApi.draftBlock).mockResolvedValue(summary);
  vi.mocked(styleApi.stylePiece).mockResolvedValue(yoke);
  render(<BlockViewer />);
  fireEvent.click(screen.getByRole('button', {name: 'Draft 1078375 block'}));
  await screen.findByRole('button', {name: 'Select back YK'});
}

it('drafts the block and draws every layer of its pieces', async () => {
  await drafted();
  expect(styleApi.draftBlock).toHaveBeenCalledWith('shirt_1078375');
  expect(styleApi.stylePiece).toHaveBeenCalledWith('style-1', 'back_YK', 'L');
  expect(['cut', 'sew', 'notches', 'grain', 'labels'].map(layer)).toEqual([1, 1, 1, 1, 1]);
  expect(screen.getByText('back YK · cut 2, on fold')).toBeTruthy();
});

it('hides and shows each layer from its toggle', async () => {
  await drafted();
  for (const [label, name] of [['Cut line', 'cut'], ['Sew line', 'sew'], ['Notches', 'notches'],
    ['Grain', 'grain'], ['Labels', 'labels']]) {
    fireEvent.click(screen.getByLabelText(label));
    expect(layer(name)).toBe(0);
    fireEvent.click(screen.getByLabelText(label));
    expect(layer(name)).toBe(1);
  }
});

it('shows the backend error when drafting fails', async () => {
  vi.mocked(styleApi.draftBlock).mockRejectedValue(new Error('Drafting block is not installed: shirt_1078375'));
  render(<BlockViewer />);
  fireEvent.click(screen.getByRole('button', {name: 'Draft 1078375 block'}));
  expect((await screen.findByRole('alert')).textContent).toBe('Drafting block is not installed: shirt_1078375');
});

it('downloads the graded DXF-AAMA zip and shows a failed download', async () => {
  await drafted();
  vi.mocked(api.download).mockResolvedValue(undefined);
  fireEvent.click(screen.getByRole('button', {name: 'Download graded DXF-AAMA + RUL'}));
  expect(api.download).toHaveBeenCalledWith('/styles/style-1/export/aama?unit=mm', 'shirt_1078375_graded_aama.zip');
  vi.mocked(api.download).mockRejectedValue(new Error('Grade rules need every size drafted; missing S'));
  await waitFor(() => expect((screen.getByRole('button', {name: 'Download graded DXF-AAMA + RUL'}) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(screen.getByRole('button', {name: 'Download graded DXF-AAMA + RUL'}));
  expect((await screen.findByRole('alert')).textContent).toBe('Grade rules need every size drafted; missing S');
});
