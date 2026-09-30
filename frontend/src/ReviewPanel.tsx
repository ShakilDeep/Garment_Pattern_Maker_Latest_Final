import {useEffect, useState} from 'react';
import {api} from './api';

type Review = {gate:string; status:string; actor:string|null; at:string|null; note:string};
export default function ReviewPanel({projectId}: {projectId:string}) {
  const [items, setItems] = useState<Review[]>([]);
  const [actor, setActor] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api<Review[] | {items?: Review[]}>(`/projects/${projectId}/reviews`).then(r => {
      if (!active) return;
      setItems(Array.isArray(r) ? r : (r.items ?? []));
    }).catch(e => {if(active)setError(e.message)});
    return () => {active = false};
  }, [projectId]);
  async function decide(gate:string, status:string) {
    setBusy(true); setError('');
    try {
      const result = await api<Review[] | {items?: Review[]}>(`/projects/${projectId}/reviews/${gate}`, 'POST', {status, actor, note});
      setItems(Array.isArray(result) ? result : (result.items ?? []));
      setNote('');
    } catch(e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  return <section className="card workflow" aria-label="Customer review">
    <h2>Customer review</h2><p>Record a decision for each stage. Changes to reviewed inputs supersede earlier decisions.</p>
    <div className="marker-inputs">
      <label>Reviewer<input value={actor} onChange={e => setActor(e.target.value)}/></label>
      <label>Review note<input value={note} onChange={e => setNote(e.target.value)}/></label>
    </div>
    {error && <p role="alert">{error}</p>}
    {items.map((r, i) => <article className="requirement" key={r.gate}>
      <h3>{r.gate.replaceAll('_', ' ')} · {r.status.replaceAll('_', ' ')}</h3>
      {r.actor && <p>{r.actor} · {r.at && new Date(r.at).toLocaleString()} · {r.note}</p>}
      <div className="actions">
        <button disabled={busy || !actor.trim() || items.slice(0, i).some(v => v.status !== 'APPROVED_FOR_DEMO')}
          onClick={() => void decide(r.gate, 'APPROVED_FOR_DEMO')}>Approve {r.gate} for demo</button>
        <button disabled={busy || !actor.trim()} onClick={() => void decide(r.gate, 'REJECTED')}>Reject {r.gate}</button>
      </div>
    </article>)}
    <p>Demo approval does not certify production fit or manufacturing accuracy.</p>
  </section>;
}
