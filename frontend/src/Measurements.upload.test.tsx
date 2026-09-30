import {cleanup, fireEvent, render, screen} from '@testing-library/react';
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

describe('Measurements upload browse', () => {
  it('shows Facade Browse control with on-label file input', () => {
    render(
      <Measurements
        project={projectWithChest(56)}
        size="M"
        setSize={vi.fn()}
        save={vi.fn(async () => true)}
        upload={vi.fn()}
        open={vi.fn()}
        busy={false}
      />,
    );
    fireEvent.click(screen.getByRole('button', {name: 'Upload XLSX'}));
    const input = screen.getByLabelText('Browse files') as HTMLInputElement;
    expect(input.type).toBe('file');
    expect(input.className).toMatch(/browse-files-input/);
    expect(input.closest('label')?.className).toMatch(/browse-files/);
  });
});
