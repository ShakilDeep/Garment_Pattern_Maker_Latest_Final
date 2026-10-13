import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import StylePieceSvg from './StylePieceSvg';
import {yoke} from './blockViewerFixture';
import {LAYERS} from './styleTypes';
import ValidationCenter from './ValidationCenter';
import type {Pattern, Project} from './types';

afterEach(cleanup);
const pattern = {id:'pattern', size:'L', seam_allowance:0, pieces:[], validation:[]} as unknown as Pattern;

it('pieces are buttons that report their selection and keep keyboard focus order', () => {
  const select = vi.fn();
  render(<StylePieceSvg piece={yoke} shown={new Set(LAYERS)} selected select={select}/>);
  const card = screen.getByRole('button', {name:'Select back YK'});
  expect(card.getAttribute('aria-pressed')).toBe('true');
  expect(screen.getByRole('img', {name:'back YK pattern piece'})).toBeTruthy();
  fireEvent.click(card);
  expect(select).toHaveBeenCalledWith('back_YK');
});

it('announces validation counts after validation changes', () => {
  const project = {pattern, state:'PATTERN_READY'} as Project;
  const view = render(<ValidationCenter project={project} requirements={null} go={vi.fn()}/>);
  expect(screen.getByRole('status', {name:'Validation status'}).textContent).toContain('0 errors');
  view.rerender(<ValidationCenter project={{...project, pattern:{...pattern,
    validation:[{code:'SEAM', severity:'ERROR', message:'Check seam'}]}}} requirements={null} go={vi.fn()}/>);
  expect(screen.getByRole('status', {name:'Validation status'}).textContent).toContain('1 errors');
});
