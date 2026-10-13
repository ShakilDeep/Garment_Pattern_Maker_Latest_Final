import {afterEach, expect, it, vi} from 'vitest';
import {nestAndExport} from './nestAndExport';
import type {Project} from './types';

vi.mock('./api', () => ({api: vi.fn(), download: vi.fn(async () => undefined)}));
afterEach(() => vi.clearAllMocks());

const ALL = ['S', 'M', 'L', 'XL', 'XXL', '3XL'];
const graded = (sizes: string[]) => sizes.map((size) => ({size}));

function exporter(grades = graded(ALL.filter((s) => s !== 'L')), refresh = vi.fn()) {
  const project = {id: 'p1', pattern: {size: 'L'}, grades, marker: {size: 'M'},
    resolutions: {profile: 'shirt_1078375'}} as unknown as Project;
  const run = vi.fn(async (task: () => Promise<unknown>) => { await task(); return true; });
  return nestAndExport({project, size: 'L', refresh, run}).exportFile;
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

it('requests DXF-AAMA in its unit with an _aama.dxf name', async () => {
  const {download} = await import('./api');
  await exporter()('dxf-aama', 'mm');
  expect(download).toHaveBeenCalledWith('/projects/p1/exports/dxf-aama?size=L&unit=mm', '1078983_L_pattern_demo_aama.dxf');
});

it('requests every size for Optitex as one zip named after the block', async () => {
  const {api, download} = await import('./api');
  await exporter()('aama-graded', 'mm');
  expect(api).not.toHaveBeenCalled();
  expect(download).toHaveBeenCalledWith('/projects/p1/exports/aama-graded?unit=mm', 'shirt_1078375_graded_aama.zip');
});

it('grades every size first when some are missing or stale, then downloads the zip', async () => {
  const {api, download} = await import('./api');
  const refresh = vi.fn();
  await exporter([...graded(['M']), {size: 'S', stale: true}] as never, refresh)('aama-graded', 'mm');
  expect(api).toHaveBeenCalledWith('/projects/p1/grade', 'POST', {sizes: ALL});
  expect(refresh).toHaveBeenCalledWith('p1');
  expect(download).toHaveBeenCalledWith('/projects/p1/exports/aama-graded?unit=mm', 'shirt_1078375_graded_aama.zip');
});

it('does not download when grading fails', async () => {
  const {api, download} = await import('./api');
  vi.mocked(api).mockRejectedValueOnce(new Error('Generate a current pattern first'));
  await expect(exporter(graded(['M']))('aama-graded', 'mm')).rejects.toThrow('Generate a current pattern first');
  expect(download).not.toHaveBeenCalled();
});
