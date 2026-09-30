import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import PatternCanvas from './PatternCanvas';
import ValidationCenter from './ValidationCenter';
import type {Pattern, Project} from './types';

afterEach(cleanup);
const piece = {id:'front', name:'Front', width:30, height:70, quantity:2,
  points:[[0,0],[30,0],[30,70],[0,70]], cut_points:[], grainline:[[15,10],[15,60]], notches:[]};
const pattern = {id:'pattern', size:'L', seam_allowance:0, pieces:[piece], validation:[]} as unknown as Pattern;

it('announces selection, zoom and pan, without stealing arrow keys from inputs', () => {
  render(<><input aria-label="Measurement"/><PatternCanvas pattern={pattern} selected="front" select={vi.fn()}/></>);
  const status = screen.getByRole('status', {name:'Canvas status'});
  expect(status.textContent).toContain('Front selected');
  const front = screen.getByRole('button', {name:'Select Front'});
  expect(front.getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByRole('table', {name:'Pattern pieces and construction quantities'})).toBeTruthy();
  fireEvent.keyDown(front, {key:'ArrowRight'});
  expect(status.textContent).toContain('Pan 20, 0');
  fireEvent.keyDown(screen.getByLabelText('Measurement'), {key:'ArrowRight'});
  expect(status.textContent).toContain('Pan 20, 0');
  fireEvent.click(screen.getByRole('button', {name:'Zoom in'}));
  expect(status.textContent).toContain('110%');
});

it('announces validation counts after validation changes', () => {
  const project = {pattern, state:'PATTERN_READY'} as Project;
  const view = render(<ValidationCenter project={project} requirements={null} go={vi.fn()}/>);
  expect(screen.getByRole('status', {name:'Validation status'}).textContent).toContain('0 errors');
  view.rerender(<ValidationCenter project={{...project, pattern:{...pattern,
    validation:[{code:'SEAM', severity:'ERROR', message:'Check seam'}]}}} requirements={null} go={vi.fn()}/>);
  expect(screen.getByRole('status', {name:'Validation status'}).textContent).toContain('1 errors');
});
