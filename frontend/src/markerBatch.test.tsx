import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import Workflow from './Workflow';
import type {Pattern, Project} from './types';

afterEach(cleanup);
const pattern = (size:string) => ({id:size, size, stale:false, validation:[], pieces:[]} as unknown as Pattern);
function setup(stale=false) {
 const nest=vi.fn();
 const p={id:'test', pattern:{...pattern('L'),stale}, grades:[pattern('S'),pattern('L')], marker:null, previous_marker:null} as Project;
 render(<Workflow page="Marker Nesting" project={p} requirements={null} resolve={vi.fn()} generate={vi.fn()} grade={vi.fn()} nest={nest} download={vi.fn()} busy={false} size="L" setSize={vi.fn()} open={vi.fn()}/>);
 return nest;
}
describe('marker batch controls',()=>{
 it('submits explicit quantities for two generated sizes',()=>{
  const nest=setup();
  fireEvent.click(screen.getByLabelText('Combine sizes'));
  fireEvent.change(screen.getByLabelText('S garment quantity'),{target:{value:'2'}});
  fireEvent.change(screen.getByLabelText('L garment quantity'),{target:{value:'1'}});
  expect((screen.getByLabelText('M garment quantity') as HTMLInputElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Optimize marker'}));
  expect(nest).toHaveBeenCalledWith(150,{S:2,L:1},0.5);
 });
 it('blocks an empty batch and a batch over the garment limit',()=>{
  setup();fireEvent.click(screen.getByLabelText('Combine sizes'));
  fireEvent.change(screen.getByLabelText('L garment quantity'),{target:{value:'0'}});
  expect((screen.getByRole('button',{name:'Optimize marker'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('L garment quantity'),{target:{value:'20'}});
  fireEvent.change(screen.getByLabelText('S garment quantity'),{target:{value:'1'}});
  expect((screen.getByRole('button',{name:'Optimize marker'}) as HTMLButtonElement).disabled).toBe(true);
 });
 it('blocks fractional quantities and empty numeric inputs',()=>{
  setup();fireEvent.change(screen.getByLabelText('Garment quantity'),{target:{value:'1.5'}});
  expect((screen.getByRole('button',{name:'Optimize marker'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Garment quantity'),{target:{value:'1'}});
  fireEvent.change(screen.getByLabelText('Fabric width'),{target:{value:''}});
  expect((screen.getByRole('button',{name:'Optimize marker'}) as HTMLButtonElement).disabled).toBe(true);
 });
 it('overlays previous marker placements for visual comparison',()=>{
  const nest=vi.fn();
  const piece={name:'Front',points:[[0,0],[4,0],[4,4],[0,4]] as [number,number][],x:1,y:1,width:4,height:4};
  const marker={placements:[piece],width:20,length:20,utilization:50,waste:50,quantity:1,size:'L',strategy:'first-fit',gap:0.5};
  const p={id:'test',pattern:pattern('L'),grades:[],marker,previous_marker:{...marker,utilization:40,length:22}} as unknown as Project;
  render(<Workflow page="Marker Nesting" project={p} requirements={null} resolve={vi.fn()} generate={vi.fn()} grade={vi.fn()} nest={nest} download={vi.fn()} busy={false} size="L" setSize={vi.fn()} open={vi.fn()}/>);
  expect(screen.getByLabelText('Previous marker layout')).toBeTruthy();
  expect(screen.getByText(/Previous marker: 40.0% utilization/)).toBeTruthy();
 });
 it('downloads marker SVG and PDF from the nesting results',()=>{
  const download=vi.fn();
  const piece={name:'Front',points:[[0,0],[4,0],[4,4],[0,4]] as [number,number][],x:1,y:1,width:4,height:4};
  const marker={placements:[piece],width:20,length:20,utilization:50,waste:50,quantity:1,size:'L',strategy:'first-fit',gap:0.5};
  const p={id:'test',pattern:pattern('L'),grades:[],marker,previous_marker:null} as unknown as Project;
  render(<Workflow page="Marker Nesting" project={p} requirements={null} resolve={vi.fn()} generate={vi.fn()} grade={vi.fn()} nest={vi.fn()} download={download} busy={false} size="L" setSize={vi.fn()} open={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:/Download marker SVG/i}));
  fireEvent.click(screen.getByRole('button',{name:/Download marker PDF/i}));
  expect(download).toHaveBeenCalledWith('marker-svg');
  expect(download).toHaveBeenCalledWith('marker-pdf');
 });
 it('blocks nesting when the current pattern is stale',()=>{
  setup(true);
  expect((screen.getByRole('button',{name:'Optimize marker'}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Generate a current pattern/)).toBeTruthy();
 });
});
