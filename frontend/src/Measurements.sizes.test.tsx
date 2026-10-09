import {cleanup, screen} from '@testing-library/react';
import {afterEach, describe, expect, it} from 'vitest';
import {projectWithChest, setup} from './measurementsFixture';

afterEach(() => { cleanup(); sessionStorage.clear(); });

const options = () => Array.from(screen.getByLabelText('Size').querySelectorAll('option')).map(o => o.value);

describe('Measurements size selector', () => {
  it('lists the sizes of the imported chart', () => {
    setup({...projectWithChest(56), chart: {sizes: ['XS', 'S', 'M', 'L', 'XL', 'XXL'], base_size: 'S', unit_hint: null}});
    expect(options()).toEqual(['XS', 'S', 'M', 'L', 'XL', 'XXL']);
  });

  it('keeps the demo sizes for a project without a chart', () => {
    setup(projectWithChest(56));
    expect(options()).toEqual(['S', 'M', 'L', 'XL', 'XXL', '3XL']);
  });
});

describe('Measurements mapping screen', () => {
  it('opens on the upload tab when the chart has unmapped rows', () => {
    const base = projectWithChest(56);
    const measurements = [...base.measurements, {...base.measurements[0], key: 'Z9', mapping_status: 'unmapped'}];
    setup({...base, measurements});
    expect(screen.getByRole('button', {name: /Upload XLSX/}).className).toContain('selected');
  });
});
