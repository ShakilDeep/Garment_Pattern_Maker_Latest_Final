import {useState} from 'react';
import {api} from './api';
import type {Project} from './types';
import PieceInspector from './PieceInspector';

type Props = {project: Project; selected: string; size: string; refresh: () => void};

export default function StudioControls({project, selected, size, refresh}: Props) {
  const [allowance, setAllowance] = useState(String(project.pattern?.seam_allowance || 0));
  const [notch, setNotch] = useState('0.33');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const current = project.pattern?.size === size && !project.pattern.stale;
  const piece = project.pattern?.pieces.find((p) => p.id === selected);
  async function command(name: string, value?: number) {
    setBusy(true); setError('');
    try {
      await api(`/projects/${project.id}/commands`, 'POST', {command: name, value, piece_id: selected || null});
      refresh();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const foldDisabled = !current || !piece || !['Back', 'Yoke'].includes(piece.name)
    ? 'Select Back or Yoke on a current pattern' : undefined;
  return (
    <section className="workflow card" aria-label="Pattern edit controls">
      <h3>Pattern edits</h3>
      <p>Edits create a validated version and clear older grades and markers.</p>
      {!current && <p>Generate this size as the current pattern before editing.</p>}
      <PieceInspector piece={piece || null} />
      <div className="marker-inputs">
        <label>Seam allowance (cm)
          <input type="number" min="0" max="3" step=".1" value={allowance}
            onChange={(e) => setAllowance(e.target.value)} /></label>
        <button disabled={busy || !current || !allowance || Number(allowance) < 0 || Number(allowance) > 3}
          onClick={() => void command('allowance', Number(allowance))}>Apply allowance</button>
        <label>Notch outline fraction
          <input type="number" min="0" max=".99" step=".01" value={notch}
            onChange={(e) => setNotch(e.target.value)} /></label>
        <button disabled={busy || !current || !piece || !notch || Number(notch) < 0 || Number(notch) >= 1}
          title={!piece ? 'Select a piece first' : undefined}
          onClick={() => void command('notch', Number(notch))}>Place demo notch</button>
      </div>
      <div className="actions">
        <button disabled={busy || Boolean(foldDisabled)} title={foldDisabled}
          onClick={() => void command('fold', piece?.cut_on_fold ? 0 : 1)}>Toggle fold annotation</button>
        <button disabled={busy || !current} onClick={() => void command('undo')}>Undo pattern edit</button>
        <button disabled={busy || !current} onClick={() => void command('redo')}>Redo pattern edit</button>
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
