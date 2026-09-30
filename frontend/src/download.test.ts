import {afterEach, expect, it, vi} from 'vitest';
import {download} from './api';

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it('appends a temporary link so marker downloads trigger after fetch', async () => {
  vi.useFakeTimers();
  const click = vi.fn();
  const remove = vi.fn();
  const appendChild = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
    Object.assign(node as HTMLAnchorElement, {click, remove});
    return node;
  });
  const revoke = vi.fn();
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    blob: async () => new Blob(['<svg/>'], {type: 'image/svg+xml'}),
  })));
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:marker'),
    revokeObjectURL: revoke,
  });

  await download('/projects/x/exports/marker-svg', '1078983_L_marker_demo.svg');

  expect(fetch).toHaveBeenCalledWith('/api/v1/projects/x/exports/marker-svg');
  expect(appendChild).toHaveBeenCalled();
  expect(click).toHaveBeenCalled();
  // Immediate remove cancels saves in Safari/Chromium — cleanup must be deferred.
  expect(remove).not.toHaveBeenCalled();
  expect(revoke).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1500);
  expect(remove).toHaveBeenCalled();
  expect(revoke).toHaveBeenCalledWith('blob:marker');
});
