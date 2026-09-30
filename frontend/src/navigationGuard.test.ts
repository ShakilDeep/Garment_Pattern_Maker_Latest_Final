import {expect, it, vi} from 'vitest';
import {confirmLeaveIfDirty, guardedGo} from './navigationGuard';

it('allows navigation when the draft is clean', () => {
  const confirmFn = vi.fn();
  expect(confirmLeaveIfDirty(false, confirmFn)).toBe(true);
  expect(confirmFn).not.toHaveBeenCalled();
});

it('blocks navigation when the user declines the dirty-draft prompt', () => {
  const go = vi.fn();
  const confirmFn = vi.fn(() => false);
  expect(guardedGo(true, 'Export', go, confirmFn)).toBe(false);
  expect(go).not.toHaveBeenCalled();
});

it('navigates after the user confirms leaving a dirty draft', () => {
  const go = vi.fn();
  expect(guardedGo(true, 'Export', go, () => true)).toBe(true);
  expect(go).toHaveBeenCalledWith('Export');
});
