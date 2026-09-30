import {useState} from 'react';
import type {Project, Requirement} from './types';

export type Evidence = {source_id:string; note:string; actor:string; resolution_type:'source'};
type Props = {project:Project; items:Requirement[]; busy:boolean;
  resolve:(key:string, value:string, evidence?:Evidence)=>void; download:()=>void};

export default function CalibrationReview({project, items, busy, resolve, download}:Props) {
  const [source, setSource] = useState('');
  const [actor, setActor] = useState('');
  const [note, setNote] = useState('');
  const remaining = items.filter(item => item.status !== 'AVAILABLE');
  return <details className="calibration-review">
    <summary>Production calibration · {remaining.length} evidence requests</summary>
    <p>These requests do not block the demo. Record a review only when the selected document contains
      the requested client-approved information. Collecting evidence does not certify production accuracy.</p>
    <button onClick={download}>Prepare production-calibration request</button>
    <div className="marker-inputs">
      <label>Supporting source<select value={source} onChange={e=>setSource(e.target.value)}>
        <option value="">Select a source</option>
        {project.documents.map(d=><option key={d.id} value={d.id}>{d.filename}</option>)}
      </select></label>
      <label>Evidence reviewer<input value={actor} onChange={e=>setActor(e.target.value)}/></label>
      <label>Evidence review note<input value={note} onChange={e=>setNote(e.target.value)}/></label>
    </div>
    {items.map(item=><article className="requirement" key={item.key}>
      <h3>{item.name} · {item.status === 'AVAILABLE'?'Evidence reviewed':'Evidence needed'}</h3>
      <p>{item.why}</p>
      {item.status === 'AVAILABLE'?<small>Source: {item.source}</small>:
        <button disabled={busy||!source||!actor.trim()||!note.trim()}
          onClick={()=>resolve(item.key,'reviewed',{source_id:source,actor,note,resolution_type:'source'})}>
          Record evidence for {item.name.toLowerCase()}
        </button>}
    </article>)}
  </details>;
}
