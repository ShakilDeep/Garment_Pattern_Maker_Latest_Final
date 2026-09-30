import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import ValidationCenter from './ValidationCenter';
import type {Project, Requirements} from './types';

afterEach(cleanup);

it('tells what is missing, why, source, units, default, and what is blocked', () => {
  const project = {pattern: null, state: 'DRAFT'} as Project;
  const requirements = {
    blockers: [{
      key: 'units', name: 'Workbook units', why: 'The workbook has no explicit unit column.',
      source: 'sheet.xlsx', accepted_units: ['cm'], fallback_policy: 'No automatic default', blocking: true,
    }],
  } as unknown as Requirements;
  const go = vi.fn();
  render(<ValidationCenter project={project} requirements={requirements} go={go}/>);
  expect(screen.getAllByText(/Workbook units/).length).toBeGreaterThan(0);
  expect(screen.getByText(/no explicit unit column/)).toBeTruthy();
  expect(screen.getByText(/From: sheet.xlsx/)).toBeTruthy();
  expect(screen.getByText(/Accepted: cm/)).toBeTruthy();
  expect(screen.getByText(/Default: No automatic default/)).toBeTruthy();
  expect(screen.getByText(/Blocks generation/)).toBeTruthy();
  fireEvent.click(screen.getAllByRole('button', {name: /Resolve/})[0]);
  expect(go).toHaveBeenCalledWith('Requirements');
});
