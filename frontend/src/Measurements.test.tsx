import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import Measurements from './Measurements';
import type {Project} from './types';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

function projectWithChest(value: number): Project {
  return {
    id: 'p1',
    name: 'Shirt',
    state: 'open',
    measurements: [{
      key: 'half_chest',
      code: 'A',
      label: 'Chest',
      unit: 'cm',
      tolerance: null,
      source: 'demo',
      sheet: 's',
      row: 1,
      values: {M: {value, raw: value, formula: null, cell: 'A1', issue: null, override: false}},
    }],
    resolutions: {units: 'cm'},
    pattern: null,
    grades: [],
    marker: null,
    previous_marker: null,
    documents: [],
    techpack: null,
    audit: [],
    undo: [],
    redo: [],
  } as Project;
}

function setup(p = projectWithChest(56)) {
  const save = vi.fn(async () => true);
  render(
    <Measurements
      project={p}
      size="M"
      setSize={vi.fn()}
      save={save}
      upload={vi.fn()}
      open={vi.fn()}
      busy={false}
    />,
  );
  return {save};
}

describe('Measurements Reset', () => {
  it('discards unsaved edits and restores source values', () => {
    setup();
    const input = screen.getByLabelText('Chest Circumference') as HTMLInputElement;
    expect(input.value).toBe('112.0');
    fireEvent.change(input, {target: {value: '999'}});
    expect(input.value).toBe('999');
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    expect(input.value).toBe('112.0');
    expect(sessionStorage.getItem('measurement-draft:p1:M:cm')).toBeNull();
  });

  it('clears fields when there are no unsaved edits', async () => {
    setup();
    const input = screen.getByLabelText('Chest Circumference') as HTMLInputElement;
    expect(input.value).toBe('112.0');
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(input.value).toBe(''));
  });

  it('resets unit display to cm', async () => {
    setup();
    fireEvent.click(screen.getByRole('button', {name: 'inch'}));
    expect(screen.getAllByText('inch').length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'cm'}).className).toMatch(/selected/));
    expect(screen.getAllByText('cm').length).toBeGreaterThan(1);
  });

  it('clears imported sources so the same workbook can be re-imported', async () => {
    const clearSources = vi.fn(async () => {});
    const p = projectWithChest(56);
    p.documents = [{id: 'd1', filename: 'Book2.xlsx', sha256: 'abc', bytes: 1}];
    render(
      <Measurements
        project={p} size="M" setSize={vi.fn()} save={vi.fn(async () => true)}
        upload={vi.fn()} open={vi.fn()} busy={false} clearSources={clearSources}
      />,
    );
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(clearSources).toHaveBeenCalled());
  });

  it('clears the pattern preview when a generated pattern exists', async () => {
    const clearSources = vi.fn(async () => {});
    const p = projectWithChest(56);
    p.pattern = {
      id: 'pat', size: 'M', profile: 'demo_v1', pieces: [], validation: [], assumptions: [],
      input_hash: 'x', stale: false, seam_allowance: 1,
    };
    render(
      <Measurements
        project={p} size="M" setSize={vi.fn()} save={vi.fn(async () => true)}
        upload={vi.fn()} open={vi.fn()} busy={false} clearSources={clearSources}
      />,
    );
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(clearSources).toHaveBeenCalled());
  });
});
