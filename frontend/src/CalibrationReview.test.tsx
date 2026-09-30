import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import CalibrationReview from './CalibrationReview';
import type {Project, Requirement} from './types';

afterEach(cleanup);
it('requires supporting evidence and submits the reviewer and note', () => {
  const resolve = vi.fn();
  render(<CalibrationReview project={{documents:[{id:'source',filename:'rules.pdf'}]} as Project}
    items={[{key:'calibration:base_pattern',name:'Approved base pattern',status:'MISSING',why:'Provide the approved block'} as Requirement]}
    busy={false} resolve={resolve} download={vi.fn()}/>);
  fireEvent.click(screen.getByText('Production calibration · 1 evidence requests'));
  const submit=screen.getByRole('button',{name:'Record evidence for approved base pattern'}) as HTMLButtonElement;
  expect(submit.disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Supporting source'),{target:{value:'source'}});
  fireEvent.change(screen.getByLabelText('Evidence reviewer'),{target:{value:'Client'}});
  fireEvent.change(screen.getByLabelText('Evidence review note'),{target:{value:'Approved block on page 2'}});
  fireEvent.click(submit);
  expect(resolve).toHaveBeenCalledWith('calibration:base_pattern','reviewed',{
    source_id:'source',actor:'Client',note:'Approved block on page 2',resolution_type:'source'});
});
