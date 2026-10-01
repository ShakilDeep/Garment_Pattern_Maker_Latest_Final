import {afterEach, expect, it, vi} from 'vitest';
import {listProjects} from './projectList';
import {api} from './api';

vi.mock('./api', () => ({api: vi.fn()}));
afterEach(() => vi.resetAllMocks());

it('unwraps the paginated project list', async () => {
  const items = [{id: 'a', name: 'Alpha'}, {id: 'b', name: 'Beta', archived: true}];
  vi.mocked(api).mockResolvedValue({items, total: 2, limit: 100, offset: 0});
  await expect(listProjects()).resolves.toEqual(items);
  expect(api).toHaveBeenCalledWith('/projects');
});

it('propagates request failures', async () => {
  vi.mocked(api).mockRejectedValue(new Error('Request failed'));
  await expect(listProjects()).rejects.toThrow('Request failed');
});
