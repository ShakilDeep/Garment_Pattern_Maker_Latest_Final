import CalibrationReview,{type Evidence} from './CalibrationReview';
import MarkerPanel from './MarkerPanel';
import ReviewPanel from './ReviewPanel';
import {CheckCircle2,AlertTriangle,Download,ArrowRight,RefreshCw} from 'lucide-react';
import type {Project,Requirements} from './types';
import {sizes} from './types';
import SourceReview from './SourceReview';
import ValidationCenter from './ValidationCenter';

type Props={
 page:string;project:Project;requirements:Requirements|null;
 resolve:(key:string,value:string,evidence?:Evidence)=>void;generate:()=>void;grade:()=>void;
 nest:(width:number,quantity:number|Record<string,number>,gap:number)=>void;
 download:(kind:string)=>void;busy:boolean;size:string;setSize:(s:string)=>void;
 open:(name:string)=>void;go?:(page:string)=>void;
};

export default function Workflow({page,project:p,requirements:r,resolve,generate,grade,nest,download,busy,size,setSize,open,go}:Props){
 if(page==='Validation Center')return <ValidationCenter project={p} requirements={r} go={go||(()=>{})}/>;
 if(page==='Requirements'||page==='Generate Pattern')return <section className="workflow card">
  <div className="section-heading"><div><h2>{page==='Requirements'?'Requirements review':'Generate pattern'}</h2>
  <p>{r?.ready?'Your demo inputs are ready.':`${r?.blockers.length??0} items need your input before pattern generation`}</p></div>
  <span className="badge">Demo profile</span></div>
  {!r?.ready&&r?.blockers[0]&&<p className="notice" role="status">Next: {[...r.blockers].sort((a,b)=>(Number({MISSING:0,CONFLICTING:1,AMBIGUOUS:2,DEMO_DEFAULT_AVAILABLE:3}[a.status]??9)-Number({MISSING:0,CONFLICTING:1,AMBIGUOUS:2,DEMO_DEFAULT_AVAILABLE:3}[b.status]??9))||a.name.localeCompare(b.name))[0].name}</p>}
  {r?.items.filter(i=>!i.key.startsWith('calibration:')).map(i=><article className={`requirement ${i.status==='AVAILABLE'?'resolved':''}`} key={i.key}>
   <div>{i.status==='AVAILABLE'?<CheckCircle2 size={20}/>:<AlertTriangle size={20}/>}<strong>{i.name}</strong>
   <span className="badge">{i.status.replaceAll('_',' ')}</span></div><p>{i.why}</p>
   {i.options.length>0&&<div className="actions">{i.options.map(v=><button disabled={busy||i.value===v} key={v} onClick={()=>resolve(i.key,v)} className={i.value===v?'accepted':''}>{i.value===v?'Confirmed: ':''}{({cm:'Values are in cm',demo_v1:'Use demo drafting profile',confirmed:'I reviewed the measurements',workbook:'Use workbook (3 cm)',techpack:'Use tech pack (3.5 cm)'} as Record<string,string>)[v]||v}</button>)}</div>}
   {i.key.startsWith('measurement:')&&<button onClick={()=>open('measurements')}>Enter missing measurement</button>}
  </article>)}
  <button className="primary" disabled={busy||!r?.ready} onClick={generate}>Generate {size} Pattern <ArrowRight size={17}/></button>
  <details><summary>Documented demo assumptions</summary><p>Body dimensions follow the workbook. Curves, back neck drop, and collar attachment use explicit demo rules. Seam allowance is optional. Production calibration remains required.</p></details>
  <CalibrationReview project={p} items={r?.items.filter(i=>i.key.startsWith('calibration:'))||[]} busy={busy} resolve={resolve} download={()=>download('calibration')}/>
  <SourceReview project={p}/><ReviewPanel projectId={p.id}/>
 </section>;
 if(page==='Marker Nesting')return <><MarkerPanel project={p} size={size} setSize={setSize} busy={busy} nest={nest} download={download}/><ReviewPanel projectId={p.id}/></>;
 if(page==='Export')return <section className="workflow card"><h2>Export Center</h2>
  <p>Download traceable demo artifacts with validation and drafting assumptions.</p>
  <div className="notice">Demo drafting profile — calibration required for production. PDFs are report previews, not full-scale cutting templates.</div>
  <div className="export-options">{[['svg','Vector pattern','Editable vector outlines in engineering units.'],['pdf','PDF demo report','Pattern preview, validation and assumptions.'],['json','Project geometry','Patterns, grades, marker and provenance.'],['marker-svg','Marker SVG','Full marker placement in fabric units.'],['marker-pdf','Marker PDF','Scaled marker review preview.']].map(([kind,title,desc])=><article className="card" key={kind}><Download size={25}/><h3>{title}</h3><p>{desc}</p><button className="primary" disabled={busy||!p.pattern||p.pattern.stale||(kind.startsWith('marker')&&!p.marker)} onClick={()=>download(kind)}>Download {kind.toUpperCase()}</button></article>)}</div>
  <button onClick={()=>download('calibration')}>Prepare production-calibration request</button>
  <h3>Validation</h3>{p.pattern?.validation.map((v,i)=><p key={i} className={v.severity==='PASS'?'success':'warning'}>{v.severity}: {v.message}</p>)}
  <ReviewPanel projectId={p.id}/>
 </section>;
 if(page==='Grading')return <section className="workflow card">
  <div className="section-heading"><div><h2>Grading</h2><p>Regenerate each size from its own workbook values.</p></div>
  <button className="primary" disabled={busy||!r?.ready} onClick={grade}><RefreshCw size={16}/>Generate all sizes</button></div>
  <div className="grade-sizes">{sizes.map(s=><button key={s} className={size===s?'primary':''} onClick={()=>setSize(s)}>{s}<small>{p.grades.some(g=>g.size===s)?'Generated':'Not generated'}</small></button>)}</div>
  <p>{p.grades.length} of 6 sizes generated. Source values remain authoritative; no extrapolation beyond 3XL.</p>
  <button onClick={()=>open('measurements')}>Compare size measurements</button>
 </section>;
 return null;
}
