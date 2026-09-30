import {expect, it} from 'vitest';
import {
  REF004_COLOR_THRESHOLD,
  REF004_MAX_DIFF_PIXELS,
  acceptsVisualDiff,
  visualAcceptancePolicy,
} from './visualAcceptance';

it('records an approved REF-004 pixel tolerance above the last measured baseline', () => {
  const policy = visualAcceptancePolicy();
  expect(policy.allowedDifferentPixels).toBe(REF004_MAX_DIFF_PIXELS);
  expect(policy.colorThreshold).toBe(REF004_COLOR_THRESHOLD);
  expect(policy.allowedDifferentPixels).toBeGreaterThanOrEqual(106_696);
  expect(policy.accepted).toBe(true);
  expect(policy.rationale).toMatch(/demo geometry|pocket|marketing/i);
});

it('accepts diffs within the approved allowance and rejects above it', () => {
  expect(acceptsVisualDiff(100_571)).toBe(true);
  expect(acceptsVisualDiff(REF004_MAX_DIFF_PIXELS)).toBe(true);
  expect(acceptsVisualDiff(REF004_MAX_DIFF_PIXELS + 1)).toBe(false);
});
