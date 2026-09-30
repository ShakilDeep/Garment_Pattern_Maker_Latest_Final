import {describe, expect, it} from 'vitest';
import {paletteCommands} from './commands';

describe('command palette catalog', () => {
  it('filters by query and includes discovery hints', () => {
    const rows = paletteCommands('mark', {canGenerate: true, hasPattern: true});
    expect(rows.map((row) => row.label)).toEqual(['Marker Nesting']);
    expect(rows[0].hint).toMatch(/utilization/i);
    expect(rows[0].disabled).toBeUndefined();
  });

  it('explains why generate is unavailable without inventing geometry', () => {
    const rows = paletteCommands('generate', {canGenerate: false, hasPattern: false});
    const generate = rows.find((row) => row.id === 'generate');
    expect(generate?.disabled).toMatch(/requirements/i);
  });
});
