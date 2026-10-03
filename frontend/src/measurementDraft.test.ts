import {describe,it,expect} from 'vitest';
import {changedValues,displayedValues} from './measurementDraft';
import type {Project} from './types';
describe('measurement edits',()=>{
 it('does not write rounded inch display values unless edited',()=>{
  expect(changedValues({half_chest:'45.6693'},[],'inch')).toEqual({});
 });
 it('converts edited circumference to canonical half-width cm',()=>{
  expect(changedValues({half_chest:'40'},['half_chest'],'inch').half_chest).toBeCloseTo(50.8);
 });
 it('preserves small intentional edits',()=>{
  expect(changedValues({shoulder_point_to_point:'48.51'},['shoulder_point_to_point'],'cm')).toEqual({shoulder_point_to_point:48.51});
 });
 it('rejects blank and non-finite edits',()=>{
  for(const value of ['', 'NaN','Infinity','-3'])expect(()=>changedValues({half_chest:value},['half_chest'],'cm')).toThrow();
 });
 it('shows two decimals so inch values and 0.01 cm edits are not hidden',()=>{
  const p={measurements:[{key:'half_chest',values:{L:{value:56}}},{key:'shoulder_point_to_point',values:{L:{value:48.51}}},
   {key:'sleeve_length',values:{L:{value:65}}}]} as unknown as Project;
  const cm=displayedValues(p,'L','cm'),inch=displayedValues(p,'L','inch');
  expect([cm.half_chest,cm.shoulder_point_to_point,cm.sleeve_length]).toEqual(['112.0','48.51','65.0']);
  expect([inch.half_chest,inch.sleeve_length]).toEqual(['44.09','25.59']);
 });
});
