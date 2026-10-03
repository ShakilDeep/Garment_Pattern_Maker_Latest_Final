import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import Workflow from './Workflow';
import type {Project, Requirements} from './types';

afterEach(cleanup);
const marker = {placements:[], width:20, length:20, utilization:50, waste:50, quantity:1, size:'L', strategy:'first-fit', gap:0.5};
const project = (stale=false) => ({id:'test', pattern:{id:'L', size:'L', stale, validation:[], pieces:[]}, grades:[], marker, previous_marker:null, documents:[], measurements:[], techpack:null, audit:[]} as unknown as Project);
function show(page:string, p=project(), requirements:Requirements|null=null) {
 const download = vi.fn();
 render(<Workflow page={page} project={p} requirements={requirements} resolve={vi.fn()} generate={vi.fn()} grade={vi.fn()} nest={vi.fn()} download={download} busy={false} size="L" setSize={vi.fn()} open={vi.fn()}/>);
 return download;
}

describe('export center',()=>{
 it('shows no artifact download cards even when pattern and marker are ready',()=>{
  show('Export');
  for (const name of ['Download SVG','Download PDF','Download JSON','Download MARKER-SVG','Download MARKER-PDF'])
   expect(screen.queryByRole('button',{name})).toBeNull();
  expect(screen.getByRole('button',{name:'Prepare production-calibration request'})).toBeTruthy();
 });
 it('downloads the AutoCAD DXF in the selected unit',()=>{
  const download = show('Export');
  expect((screen.getByLabelText('DXF unit') as HTMLSelectElement).value).toBe('cm');
  fireEvent.change(screen.getByLabelText('DXF unit'),{target:{value:'mm'}});
  fireEvent.click(screen.getByRole('button',{name:'Download DXF (AutoCAD)'}));
  expect(download).toHaveBeenCalledWith('dxf','mm');
 });
 it('blocks the DXF download while the pattern is stale',()=>{
  show('Export', project(true));
  expect((screen.getByRole('button',{name:'Download DXF (AutoCAD)'}) as HTMLButtonElement).disabled).toBe(true);
 });
 it('lets the user confirm an inch workbook',()=>{
  const units = {key:'units', name:'Workbook units', status:'AMBIGUOUS', blocking:true, why:'Confirm units.', options:['cm','inch'], resolved:false, value:null, source:''};
  show('Requirements', project(), {ready:false, items:[units], blockers:[units]});
  expect(screen.getByRole('button',{name:'Values are in inches'})).toBeTruthy();
  expect(screen.getByRole('button',{name:'Values are in cm'})).toBeTruthy();
 });
});
