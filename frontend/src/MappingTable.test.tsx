import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import MappingTable from './MappingTable';
import {api} from './api';
import type {ChartView, Project} from './types';

vi.mock('./api', () => ({api: vi.fn()}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const row = (n: number, label: string, key: string, status: string) => ({
  row: n, code: `C${n}`, label, alt_label: null, key, status, mapped_from: null, half: false,
  tolerance: null, base_value: 40 + n, suggestion: null,
});
const chart: ChartView = {
  sizes: ['S', 'M'], base_size: 'S', value_size: 'S', unit_hint: null, canonical_keys: ['half_seat', 'half_waist'],
  rows: [row(2, '1/2 WAIST', 'half_waist', 'synonym'), row(3, '1/2 HIPS', 'C3', 'unmapped')],
};
const suggested = {...chart, rows: [chart.rows[0], {...chart.rows[1], suggestion:
  {row: 3, key: 'half_seat', confidence: 0.9, provider: 'gemini', reason: 'hips = seat', at: 'now'}}]};
const project = {id: 'p1'} as Project;

function setup(confirm = vi.fn().mockResolvedValue(true)) {
  render(<MappingTable project={project} busy={false} confirm={confirm}/>);
  return confirm;
}

it('lists only unmapped rows until asked to show all', async () => {
  vi.mocked(api).mockResolvedValue(chart);
  setup();
  expect(await screen.findByText('1/2 HIPS')).toBeTruthy();
  expect(screen.getByText(/1 row needs a canonical measurement/)).toBeTruthy();
  expect(screen.queryByText('1/2 WAIST')).toBeNull();
  fireEvent.click(screen.getByLabelText('Show all 2 rows'));
  expect(screen.getByText('1/2 WAIST')).toBeTruthy();
  expect(api).toHaveBeenCalledWith('/projects/p1/chart');
});

it('pre-fills an AI suggestion but changes nothing until Confirm', async () => {
  vi.mocked(api).mockResolvedValueOnce(chart).mockResolvedValueOnce([]).mockResolvedValueOnce(suggested);
  const confirm = setup();
  fireEvent.click(await screen.findByRole('button', {name: 'Suggest mappings'}));
  expect(await screen.findByText(/Suggested by gemini · 90%/)).toBeTruthy();
  expect(api).toHaveBeenCalledWith('/projects/p1/mappings/suggest', 'POST');
  const select = screen.getByLabelText('Canonical key for 1/2 HIPS') as HTMLSelectElement;
  expect(select.value).toBe('half_seat');
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', {name: 'Confirm 1/2 HIPS'}));
  await waitFor(() => expect(confirm).toHaveBeenCalledWith(3, {key: 'half_seat'}));
});

it('confirms a manual choice and can mark a row not used', async () => {
  vi.mocked(api).mockResolvedValue(chart);
  const confirm = setup();
  const confirmButton = await screen.findByRole('button', {name: 'Confirm 1/2 HIPS'});
  expect((confirmButton as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Canonical key for 1/2 HIPS'), {target: {value: 'half_seat'}});
  fireEvent.click(confirmButton);
  fireEvent.click(screen.getByRole('button', {name: 'Mark 1/2 HIPS not used'}));
  await waitFor(() => expect(confirm).toHaveBeenCalledTimes(2));
  expect(confirm.mock.calls).toEqual([[3, {key: 'half_seat'}], [3, {not_used: true}]]);
});

it('shows a failed suggestion as an alert', async () => {
  vi.mocked(api).mockResolvedValueOnce(chart).mockRejectedValueOnce(new Error('The assistant is unavailable.'));
  setup();
  fireEvent.click(await screen.findByRole('button', {name: 'Suggest mappings'}));
  expect((await screen.findByRole('alert')).textContent).toContain('unavailable');
});

it('says so when every row is mapped', async () => {
  vi.mocked(api).mockResolvedValue({...chart, rows: [chart.rows[0]]});
  setup();
  expect(await screen.findByText(/Every row is mapped/)).toBeTruthy();
  expect((screen.getByRole('button', {name: 'Suggest mappings'}) as HTMLButtonElement).disabled).toBe(true);
});
