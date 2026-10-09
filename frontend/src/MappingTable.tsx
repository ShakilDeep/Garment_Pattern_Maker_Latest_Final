import {useEffect, useState} from 'react';
import {Sparkles} from 'lucide-react';
import {api} from './api';
import MappingRow from './MappingRow';
import type {ChartView, MappingChoice, Project} from './types';

type Props = {project: Project; busy: boolean; confirm: (row: number, choice: MappingChoice) => Promise<boolean>};

const needsKey = (status: string | null) => status === 'unmapped';

/** Mapping screen for an imported chart: AI suggestions are proposals; only Confirm changes a row. */
export default function MappingTable({project, busy, confirm}: Props) {
  const [chart, setChart] = useState<ChartView | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let ignore = false;
    api<ChartView>(`/projects/${project.id}/chart`)
      .then((view) => { if (!ignore) setChart(view); })
      .catch((e: Error) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, [project]);

  async function suggest() {
    setWorking(true); setError('');
    try {
      await api(`/projects/${project.id}/mappings/suggest`, 'POST');
      setChart(await api<ChartView>(`/projects/${project.id}/chart`));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Suggestions failed. Map the rows manually.');
    } finally { setWorking(false); }
  }

  if (!chart) {
    return error ? <p role="alert" className="warning">{error}</p> : <p role="status">Loading POM mapping…</p>;
  }
  const open = chart.rows.filter((row) => needsKey(row.status));
  const rows = [...open, ...(showAll ? chart.rows.filter((row) => !needsKey(row.status)) : [])];
  return (
    <section className="mapping-table" aria-label="POM mapping">
      <div className="mapping-head">
        <h3>POM mapping</h3>
        <button onClick={() => void suggest()} disabled={busy || working || !open.length}>
          <Sparkles size={15}/>Suggest mappings
        </button>
      </div>
      <p>{open.length
        ? `${open.length} ${open.length === 1 ? 'row needs' : 'rows need'} a canonical measurement. `
          + 'Suggestions change nothing until you confirm.'
        : 'Every row is mapped.'}</p>
      <label className="dropzone-replace">
        <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)}/>
        Show all {chart.rows.length} rows
      </label>
      {error && <p role="alert" className="warning">{error}</p>}
      {rows.map((row) => (
        <MappingRow key={`${row.row}:${row.key}:${row.suggestion?.at ?? ''}`} row={row} keys={chart.canonical_keys}
          size={chart.value_size} busy={busy || working} confirm={confirm}/>
      ))}
    </section>
  );
}
