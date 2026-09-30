import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import MissingInfoCenter from './MissingInfoCenter';
import type {Requirements} from './types';

afterEach(cleanup);

const blockers = [
  {
    key: 'units', name: 'Workbook units', why: 'No unit column.', status: 'MISSING',
    source: 'sheet.xlsx', accepted_units: ['cm'], fallback_policy: 'No automatic default', blocking: true,
  },
  {
    key: 'calibration:block', name: 'Base block', why: 'Needs client block.', status: 'MISSING',
    source: 'calibration', accepted_units: [], fallback_policy: 'External evidence', blocking: false,
  },
] as unknown as Requirements['blockers'];

it('filters blockers and keeps a guided next item', () => {
  const go = vi.fn();
  render(<MissingInfoCenter blockers={blockers} go={go} />);
  expect(screen.getByText(/Next: Workbook units/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText(/Missing info filter/), {target: {value: 'nonblocking'}});
  expect(screen.getByText(/Next: Base block/)).toBeTruthy();
  expect(screen.queryByText(/Workbook units/)).toBeNull();
  fireEvent.click(screen.getByRole('button', {name: /Resolve/}));
  expect(go).toHaveBeenCalledWith('Requirements');
});
