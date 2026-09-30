import {describe,it,expect} from 'vitest';
import {changedValues} from './measurementDraft';
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
});
