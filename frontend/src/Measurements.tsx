import {useEffect,useState} from 'react';
import {Upload,Pencil} from 'lucide-react';
import {fields,sizeLabels,sizes,type Project} from './types';
import {displayedValues,changedValues} from './measurementDraft';
import SourceDropzone from './SourceDropzone';
type Props={project:Project;size:string;setSize:(s:string)=>void;save:(changes:Record<string,number>)=>Promise<boolean>;upload:(f:File,replace?:boolean)=>void;open:()=>void;busy:boolean;onDirtyChange?:(dirty:boolean)=>void;clearSources?:()=>Promise<void>|void};
export default function Measurements({project,size,setSize,save,upload,open,busy,onDirtyChange,clearSources}:Props){
 const [tab,setTab]=useState('manual');const [replaceSource,setReplaceSource]=useState(false);const [unit,setUnit]=useState('cm');const [values,setValues]=useState<Record<string,string>>({});
 const [dirty,setDirty]=useState<string[]>([]);const [error,setError]=useState('');
 const draftKey=`measurement-draft:${project.id}:${size}:${unit}`;
 const clearedKey=`measurement-cleared:${project.id}:${size}`;
 useEffect(()=>{
  const snap=sessionStorage.getItem(clearedKey);
  if(snap){
   const prev=JSON.parse(snap) as {docs:string;count:number};
   const docs=project.documents.map(d=>d.id).join(',');
   if(docs===prev.docs&&project.measurements.length===prev.count){
    setValues(Object.fromEntries(fields.map(([key])=>[key,''])));
    setDirty([]);
    return;
   }
   sessionStorage.removeItem(clearedKey);
  }
  const stored=sessionStorage.getItem(draftKey);const restored=stored?JSON.parse(stored):{};
  setValues({...displayedValues(project,size,unit),...restored});setDirty(Object.keys(restored));
 },[project,size,unit,draftKey,clearedKey]);
 useEffect(()=>{onDirtyChange?.(dirty.length>0)},[dirty,onDirtyChange]);
 function edit(key:string,value:string){
  sessionStorage.removeItem(clearedKey);
  const next={...values,[key]:value};const keys=[...new Set([...dirty,key])];
  setValues(next);setDirty(keys);
  sessionStorage.setItem(draftKey,JSON.stringify(Object.fromEntries(keys.map(k=>[k,next[k]]))));
 }
 async function submit(){try{setError('');const changes=changedValues(values,dirty,unit);if(await save(changes)){sessionStorage.removeItem(draftKey);sessionStorage.removeItem(clearedKey);setDirty([])}}catch(e){setError((e as Error).message)}}
 async function reset(){
  const hadEdits=dirty.length>0;
  setError('');
  sessionStorage.removeItem(draftKey);
  sessionStorage.removeItem(`measurement-draft:${project.id}:${size}:inch`);
  sessionStorage.removeItem(`measurement-draft:${project.id}:${size}:cm`);
  setDirty([]);
  setUnit('cm');
  if(hadEdits){
   sessionStorage.removeItem(clearedKey);
   setValues(displayedValues(project,size,'cm'));
   return;
  }
  const snapshot={docs:project.documents.map(d=>d.id).join(','),count:project.measurements.length};
  const hasSources=project.documents.length>0||project.measurements.length>0||Boolean(project.techpack)
    ||Boolean(project.pattern)||project.grades.length>0||Boolean(project.marker);
  if(hasSources&&clearSources)await clearSources();
  sessionStorage.setItem(clearedKey,JSON.stringify(snapshot));
  setValues(Object.fromEntries(fields.map(([key])=>[key,''])));
 }
 return <section className="measurement-panel card"><h2>Measurements</h2><p>Upload your measurement file or enter values manually</p><div className="tabs import-tabs"><button className={tab==='upload'?'selected':''} onClick={()=>setTab('upload')}><Upload size={18}/>Upload XLSX</button><button className={tab==='manual'?'selected':''} onClick={()=>setTab('manual')}><Pencil size={18}/>Manual Entry</button></div>
 {tab==='upload'&&<SourceDropzone upload={upload} busy={busy} documents={project.documents} replaceSource={replaceSource} setReplaceSource={setReplaceSource}/>}
 <label className="field-title" htmlFor="size-select">Size</label><div className="size-row"><select id="size-select" value={size} disabled={dirty.length>0} onChange={e=>setSize(e.target.value)}>{sizes.map(s=><option key={s} value={s}>{sizeLabels[s]||s}</option>)}</select><button className="link" onClick={open}>View all sizes</button></div>
 <div className="unit-row"><strong>Unit</strong><div className="tabs"><button disabled={dirty.length>0} className={unit==='cm'?'selected fill':''} onClick={()=>setUnit('cm')}>cm</button><button disabled={dirty.length>0} className={unit==='inch'?'selected fill':''} onClick={()=>setUnit('inch')}>inch</button></div></div>
 <div className="measurement-rows">{fields.map(([key,label])=><label className="measurement-row" key={key}><span>{label}</span><input type="number" min="0.1" max="1000" step="0.01" value={values[key]??''} onChange={e=>edit(key,e.target.value)} aria-label={label}/><small>{unit}</small></label>)}</div>
 {error&&<p role="alert" className="warning">{error}</p>}<div className="measurement-actions"><button type="button" onClick={()=>void reset()}>Reset</button><button className="primary" onClick={()=>void submit()} disabled={busy}>Save Measurements</button></div><small className="source-note">{dirty.length?'Unsaved edits are kept on this device. Save or reset before changing units or size.':project.measurements.length?`${project.measurements.length} source measurements · ${project.resolutions.units?'cm confirmed':'confirm units in Requirements'}`:'Enter measurements or import your workbook.'}</small>
 </section>;
}
