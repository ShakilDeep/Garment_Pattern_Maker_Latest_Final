import type {Project} from './types';
import ReviewPanel from './ReviewPanel';

export default function SourceReview({project:p}:{project:Project}){
 const parse={status:p.documents.length?(p.measurements.length||p.techpack?'complete':'pending'):'empty',measurements:p.measurements.length,techpack:Boolean(p.techpack),issues:p.measurements.flatMap(row=>Object.values(row.values||{}).map(cell=>cell.issue).filter((issue):issue is string=>Boolean(issue)))};
 return <details className="source-review"><summary>Source files, extracted details & activity</summary>
  <div className="source-cards">{p.documents.map(d=><article className="card" key={d.id}><strong>{d.filename}</strong><p>{(d.bytes/1024).toFixed(1)} KB · imported</p><small>SHA-256: {d.sha256}</small></article>)}</div>
  <section aria-label="Parse status" className="notice"><strong>Parse status: </strong>{parse.status}<span> · {parse.measurements} measurement rows · {parse.techpack?'tech-pack details found':'no tech-pack details'}</span>{parse.issues.length ? <details><summary>{parse.issues.length} recoverable extraction issue{parse.issues.length===1?'':'s'}</summary><ul>{parse.issues.map((issue,index)=><li key={`${issue}-${index}`}>{issue}</li>)}</ul></details>:null}</section>
  {p.techpack&&<><dl>{[['Style',p.techpack.style],['Garment',p.techpack.garment],['Fit',p.techpack.fit],['Fabric',p.techpack.fabric],['Colorways',p.techpack.colorways.join(', ')]].map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
   <p>Extracted locally from selectable PDF text. Review source conflicts before using these details.</p>
   <TechnicalDetails project={p}/>
   {p.techpack.pages.map(page=><details key={page.page}><summary>Tech pack · page {page.page}</summary><pre>{page.text}</pre></details>)}</>}
  <h3>Recent project activity</h3><ol>{p.audit.slice(-12).reverse().map((a,i)=><li key={i}>{a.event.replaceAll('_',' ')} <small>{new Date(a.at).toLocaleString()}</small></li>)}</ol>
  <ReviewPanel projectId={p.id}/>
 </details>;
}

function TechnicalDetails({project}: {project:Project}) {
 const tech = project.techpack as (NonNullable<Project['techpack']> & {attributes?: {
   category:string; key:string; value:string; raw:string; page:number; source:string; status:string;
 }[]}) | null;
 return <section aria-label="Extracted technical details">
   {['garment', 'construction', 'fabric', 'bom'].map(category => <details key={category}>
     <summary>{category === 'bom' ? 'Bill of materials' : category} details</summary>
     {(tech?.attributes || []).filter(a => a.category === category).map(a => <article className="card" key={a.key}>
       <strong>{a.key.replaceAll('_', ' ')}: {a.value}</strong>
       <p>{a.source} · page {a.page} · Requires source review</p>
       <pre>{a.raw}</pre>
     </article>)}
   </details>)}
 </section>;
}
