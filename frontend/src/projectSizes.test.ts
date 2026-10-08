import {describe, expect, it} from 'vitest';
import {defaultSize, projectSizes} from './projectSizes';
import type {Project} from './types';

const withChart = (chart: Project['chart'], resolutions: Record<string, string> = {}) =>
  ({chart, resolutions} as unknown as Project);

describe('project sizes come from the imported chart', () => {
  it('uses the chart size list in order', () => {
    expect(projectSizes(withChart({sizes: ['XS', 'S', 'M'], base_size: 'S', unit_hint: null}))).toEqual(['XS', 'S', 'M']);
  });

  it('falls back to the demo sizes without a chart', () => {
    expect(projectSizes(withChart(null))).toEqual(['S', 'M', 'L', 'XL', 'XXL', '3XL']);
    expect(projectSizes(null)).toEqual(['S', 'M', 'L', 'XL', 'XXL', '3XL']);
  });

  it('defaults to the detected base size, then the chosen one, then the first size', () => {
    expect(defaultSize(withChart({sizes: ['4', '4½', '5'], base_size: '4½', unit_hint: null}))).toBe('4½');
    expect(defaultSize(withChart({sizes: ['4', '5'], base_size: null, unit_hint: null}, {base_size: '5'}))).toBe('5');
    expect(defaultSize(withChart({sizes: ['4', '5'], base_size: null, unit_hint: null}))).toBe('4');
  });
});
