import {expect, it} from 'vitest';
import table from './versionSelect.cases.json';
import {selectForSize} from './versionSelect';
import type {Project} from './types';

it.each(table.cases)('$name', ({project, size, expected}) => {
  expect(selectForSize(project as unknown as Project, size)?.id ?? null).toBe(expected);
});

it('returns null when there is no project', () => {
  expect(selectForSize(null, 'L')).toBeNull();
});
