import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import Measurements from './Measurements';
import {projectWithChest} from './measurementsFixture';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('Measurements Reset clears server state', () => {
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
