import {afterEach, expect, it, vi} from 'vitest';
import {nestAndExport} from './nestAndExport';
import type {Project} from './types';

vi.mock('./api', () => ({api: vi.fn(), download: vi.fn(async () => undefined)}));
afterEach(() => vi.clearAllMocks());

function exporter() {
  const project = {id: 'p1', pattern: {size: 'L'}, marker: {size: 'M'}} as unknown as Project;
  const run = vi.fn(async (task: () => Promise<unknown>) => { await task(); return true; });
  return nestAndExport({project, size: 'L', refresh: vi.fn(), run}).exportFile;
}

it('requests the DXF in the chosen unit with a .dxf name', async () => {
  const {download} = await import('./api');
  await exporter()('dxf', 'mm');
  expect(download).toHaveBeenCalledWith('/projects/p1/exports/dxf?size=L&unit=mm', '1078983_L_pattern_demo.dxf');
});

it('keeps marker exports free of size and unit parameters', async () => {
  const {download} = await import('./api');
  await exporter()('marker-svg', 'mm');
  expect(download).toHaveBeenCalledWith('/projects/p1/exports/marker-svg', '1078983_M_marker_demo.svg');
});
