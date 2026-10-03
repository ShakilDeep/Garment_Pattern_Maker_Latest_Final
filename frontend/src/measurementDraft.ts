import {fields,type Project} from './types';

const CM_PER_INCH=2.54; // exact by definition; mirrors backend domain/units.py

export function displayedValues(project:Project,size:string,unit:string){
 return Object.fromEntries(fields.map(([key,,factor])=>{
  const v=project.measurements.find(r=>r.key===key)?.values[size]?.value;
  if(v==null)return [key,''];
  const shown=v*factor/(unit==='inch'?CM_PER_INCH:1);
  // Two decimals (0.01 in = 0.254 mm) so the display matches what is stored; one when the second is zero.
  const text=shown.toFixed(2);
  return [key,text.endsWith('0')?text.slice(0,-1):text];
 }));
}
export function changedValues(values:Record<string,string>,dirty:string[],unit:string){
 const changes:Record<string,number>={};
 for(const key of dirty){
  if(!values[key]?.trim()||!Number.isFinite(Number(values[key]))||Number(values[key])<=0)
   throw new Error('Enter a positive number for every edited measurement.');
  const factor=fields.find(f=>f[0]===key)?.[2]||1;
  changes[key]=Number(values[key])*(unit==='inch'?CM_PER_INCH:1)/factor;
 }
 return changes;
}
