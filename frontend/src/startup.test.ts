import {describe, expect, it} from 'vitest';
import {bootProjectsDialog, shouldRestoreLastProject} from './startup';

describe('app startup', () => {
  it('opens the Projects dialog on load', () => {
    expect(bootProjectsDialog()).toBe('projects');
  });

  it('does not auto-restore a remembered project', () => {
    expect(shouldRestoreLastProject()).toBe(false);
  });
});
