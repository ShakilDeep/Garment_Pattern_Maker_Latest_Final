import {fields,type Project} from './types';

export function displayedValues(project:Project,size:string,unit:string){
 return Object.fromEntries(fields.map(([key,,factor])=>{
  const v=project.measurements.find(r=>r.key===key)?.values[size]?.value;
  if(v==null)return [key,''];
  const shown=v*factor/(unit==='inch'?2.54:1);
  return [key,Number(shown.toFixed(1)).toFixed(1)];
 }));
}
export function changedValues(values:Record<string,string>,dirty:string[],unit:string){
 const changes:Record<string,number>={};
 for(const key of dirty){
  if(!values[key]?.trim()||!Number.isFinite(Number(values[key]))||Number(values[key])<=0)
   throw new Error('Enter a positive number for every edited measurement.');
  const factor=fields.find(f=>f[0]===key)?.[2]||1;
  changes[key]=Number(values[key])*(unit==='inch'?2.54:1)/factor;
 }
 return changes;
}
