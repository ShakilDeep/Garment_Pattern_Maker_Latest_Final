import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import MeasureTool from './MeasureTool';
import WalkReadout, {ARMHOLE, CAP} from './WalkReadout';
import * as styleApi from './styleApi';
import {yoke} from './blockViewerFixture';

vi.mock('./styleApi');
afterEach(cleanup);
beforeEach(() => vi.resetAllMocks());

const choose = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), {target: {value}});

it('measures a distance, an edge, an angle and an area with the backend values', async () => {
  vi.mocked(styleApi.measure).mockResolvedValue({kind: 'distance', value: 17.4281, unit: 'cm'});
  render(<MeasureTool styleId="style-1" size="L" piece={yoke} />);
  choose('From point', 'HPS'); choose('To point', 'SP');
  fireEvent.click(screen.getByRole('button', {name: 'Measure'}));
  expect((await screen.findByLabelText('Measurement result')).textContent).toBe('17.43 cm');
  expect(styleApi.measure).toHaveBeenLastCalledWith('style-1',
    {size: 'L', piece_id: 'back_YK', kind: 'distance', points: ['HPS', 'SP']});
  for (const [kind, extra] of [['path', {edges: ['CB_neck:HPS']}], ['angle', {point: 'HPS'}],
    ['area', {outline: 'sew'}]] as const) {
    choose('Measurement', kind);
    if (kind === 'angle') choose('Point', 'HPS');
    fireEvent.click(screen.getByRole('button', {name: 'Measure'}));
    expect(styleApi.measure).toHaveBeenLastCalledWith('style-1', {size: 'L', piece_id: 'back_YK', kind, ...extra});
  }
});

it('shows a refused measurement as an alert', async () => {
  vi.mocked(styleApi.measure).mockRejectedValue(new Error('back YK has no seam allowance, so it has no cut outline'));
  render(<MeasureTool styleId="style-1" size="L" piece={yoke} />);
  fireEvent.click(screen.getByRole('button', {name: 'Measure'}));
  expect((await screen.findByRole('alert')).textContent).toBe('back YK has no seam allowance, so it has no cut outline');
});

it('walks the sleeve cap against the armhole and shows the ease', async () => {
  vi.mocked(styleApi.walk).mockResolvedValue({first_cm: 57.2077, second_cm: 53.2742, difference_cm: 3.9335});
  render(<WalkReadout styleId="style-1" size="L" />);
  fireEvent.click(screen.getByRole('button', {name: 'Walk sleeve cap'}));
  expect(await screen.findByText('3.93 cm')).toBeTruthy();
  expect(screen.getByText('57.21 cm')).toBeTruthy();
  expect(screen.getByText('53.27 cm')).toBeTruthy();
  expect(styleApi.walk).toHaveBeenCalledWith('style-1', 'L', CAP, ARMHOLE);
});

it('shows a refused walk as an alert', async () => {
  vi.mocked(styleApi.walk).mockRejectedValue(new Error('FRT has no edge from UA to SP'));
  render(<WalkReadout styleId="style-1" size="L" />);
  fireEvent.click(screen.getByRole('button', {name: 'Walk sleeve cap'}));
  expect((await screen.findByRole('alert')).textContent).toBe('FRT has no edge from UA to SP');
});
