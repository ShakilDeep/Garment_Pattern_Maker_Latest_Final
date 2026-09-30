import {render} from '@testing-library/react';
import {vi} from 'vitest';
import Measurements from './Measurements';
import type {Project} from './types';

/** Shared Measurements test fixtures: a one-measurement project and a default render. */
export function projectWithChest(value: number): Project {
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

export function setup(p = projectWithChest(56)) {
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
