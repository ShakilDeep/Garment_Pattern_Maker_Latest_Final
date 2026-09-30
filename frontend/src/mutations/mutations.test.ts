import {describe, expect, it, vi} from 'vitest';
import {projectMutations} from '../projectMutations';
import {lifecycleMutations} from './lifecycle';
import {MAX_UPLOAD_BYTES, measurementMutations} from './measurement';
import {patternMutations} from './pattern';
import type {MutationContext} from './context';

function context(overrides: Partial<MutationContext> = {}): MutationContext {
  return {
    project: null, size: 'M', allowance: 1, requirements: null,
    go: vi.fn(), refresh: vi.fn(), run: vi.fn(async () => true),
    setDialog: vi.fn(), setProject: vi.fn(), setProjects: vi.fn(),
    setRequirements: vi.fn(), setError: vi.fn(), ...overrides,
  };
}

describe('project mutations composition', () => {
  it('groups mutations by responsibility and composes every action', () => {
    const ctx = context();
    expect(Object.keys(lifecycleMutations(ctx)).sort()).toEqual(['archive', 'create', 'remove', 'rename', 'restore']);
    expect(Object.keys(measurementMutations(ctx)).sort()).toEqual(['clearSources', 'resolve', 'save', 'upload']);
    expect(Object.keys(patternMutations(ctx)).sort()).toEqual(['clearPattern', 'generate', 'grade']);
    expect(Object.keys(projectMutations(ctx)).sort()).toEqual([
      'archive', 'clearPattern', 'clearSources', 'create', 'exportFile', 'generate', 'grade', 'nest',
      'remove', 'rename', 'resolve', 'restore', 'save', 'upload',
    ]);
  });

  it('does nothing for project-scoped actions without an open project', async () => {
    const ctx = context();
    await patternMutations(ctx).grade();
    expect(await measurementMutations(ctx).save({half_chest: 60})).toBe(false);
    expect(ctx.run).not.toHaveBeenCalled();
  });

  it('rejects uploads over the size limit without calling the server', async () => {
    const setError = vi.fn();
    const ctx = context({project: {id: 'p1', documents: []} as never, setError});
    const file = new File(['x'], 'big.xlsx');
    Object.defineProperty(file, 'size', {value: MAX_UPLOAD_BYTES + 1});
    await measurementMutations(ctx).upload(file);
    expect(setError).toHaveBeenCalledWith('Maximum upload size is 10 MB');
    expect(ctx.run).not.toHaveBeenCalled();
  });
});
