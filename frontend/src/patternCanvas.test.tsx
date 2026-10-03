import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, render, screen} from '@testing-library/react';
import PatternCanvas from './PatternCanvas';
import type {Pattern} from './types';

afterEach(cleanup);
const NAMES = ['Front','Back','Yoke','Sleeve','Collar','Collar Stand','Cuff','Sleeve Placket'];
const pieces = NAMES.map(name => ({id:name, name, width:30, height:40, quantity:2,
  points:[[0,0],[30,0],[30,40],[0,40]], cut_points:[], grainline:[[15,5],[15,35]], notches:[]}));
const pattern = {id:'pattern', size:'M', seam_allowance:0, pieces, validation:[]} as unknown as Pattern;

it('draws nine shapes for the eight pieces, the sleeve twice, as the DXF export does', () => {
  render(<PatternCanvas pattern={pattern} selected="" select={vi.fn()}/>);
  expect(screen.getAllByRole('button', {name:/^Select /})).toHaveLength(9);
  expect(screen.getAllByRole('button', {name:'Select Sleeve'})).toHaveLength(2);
});
