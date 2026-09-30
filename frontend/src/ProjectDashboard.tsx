import {CheckCircle2, Circle, Trash2} from 'lucide-react';
import {useState} from 'react';
import type {Project, Requirements} from './types';

type ListItem = {id: string; name: string; archived?: boolean};

type Props = {
  project: Project;
  requirements: Requirements | null;
  go: (page: string) => void;
  rename: (name: string) => void;
  remove: () => void;
  archive?: () => void;
  restore?: () => void;
  projects?: ListItem[];
  choose?: (id: string) => void;
};

export default function ProjectDashboard({
  project: p, requirements: r, go, rename, remove,
  archive = () => {}, restore = () => {}, projects = [], choose = () => {},
}: Props) {
  const [name, setName] = useState(p.name);
  const [showArchived, setShowArchived] = useState(false);
  const archived = Boolean(p.archived || p.state === 'ARCHIVED');
  const steps: [string, boolean, string, string][] = [
    ['Files imported', p.documents.length > 0, `${p.documents.length} source file${p.documents.length === 1 ? '' : 's'}`, 'Measurements'],
    ['Measurements reviewed', Boolean(p.resolutions.review), `${p.measurements.length} measurement rows`, 'Requirements'],
    ['Pattern generated', Boolean(p.pattern && !p.pattern.stale), p.pattern ? `${p.pattern.pieces.length} pieces · ${p.pattern.size}` : 'Waiting', 'Generate Pattern'],
    ['Grading validated', p.grades.length === 6, `${p.grades.length} of 6 sizes`, 'Grading'],
    ['Marker optimized', Boolean(p.marker), p.marker ? `${p.marker.utilization.toFixed(1)}% utilization` : 'Waiting', 'Marker Nesting'],
    ['Export ready', ['EXPORT_READY', 'DEMO_COMPLETE'].includes(p.state), p.state.replaceAll('_', ' '), 'Export'],
  ];
  const listed = projects.filter((item) => showArchived ? item.archived : !item.archived);
  return (
    <section className="workflow card dashboard">
      <div className="section-heading">
        <div>
          <h2>{p.techpack?.style || p.name}</h2>
          <p>{p.techpack?.garment || 'Shirt project'} · {archived ? 'Archived' : 'Active'} · Updated {p.updated_at ? new Date(p.updated_at).toLocaleString() : 'this session'}</p>
        </div>
        <span className="badge">{r?.blockers.length || 0} blockers</span>
      </div>
      <div className="project-tools">
        <input aria-label="Project name" value={name} onChange={(e) => setName(e.target.value)} />
        <button disabled={!name.trim() || name === p.name} onClick={() => rename(name)}>Rename</button>
        {archived
          ? <button onClick={restore}>Restore project</button>
          : <button onClick={archive}>Archive project</button>}
        <button className="danger-button" onClick={remove}><Trash2 size={15} />Delete</button>
      </div>
      <label><input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> Show archived projects</label>
      {listed.length > 0 && (
        <ul aria-label="Project filter list">
          {listed.map((item) => (
            <li key={item.id}><button onClick={() => choose(item.id)}>{item.name}{item.archived ? ' (archived)' : ''}</button></li>
          ))}
        </ul>
      )}
      <div className="progress-cards">
        {steps.map(([title, done, evidence, page]) => (
          <button key={title} className="card" onClick={() => go(page)}>
            {done ? <CheckCircle2 className="success" /> : <Circle />}
            <span><strong>{title}</strong><small>{evidence}</small></span>
          </button>
        ))}
      </div>
      <ol className="onboarding-queue" aria-label="First-run checkpoints">
        {steps.filter(([, done]) => !done).slice(0, 3).map(([title, , evidence, page]) => (
          <li key={title}>
            <button onClick={() => go(page)}>Next: {title}</button>
            <small>{evidence}. Demo defaults stay labeled until you confirm sources.</small>
          </li>
        ))}
      </ol>
      <div className="dashboard-insights card">
        <h3>Project insight</h3>
        <dl>
          <div><dt>Fabric</dt><dd>{p.techpack?.fabric || 'Not extracted'}</dd></div>
          <div><dt>Detected sizes</dt><dd>{p.measurements.length ? 'S, M, L, XL, XXL, 3XL' : 'None'}</dd></div>
          <div><dt>Drafting profile</dt><dd>{p.resolutions.profile || 'Unresolved'}</dd></div>
          <div><dt>Output trust</dt><dd>Demo; production calibration required</dd></div>
        </dl>
      </div>
    </section>
  );
}
