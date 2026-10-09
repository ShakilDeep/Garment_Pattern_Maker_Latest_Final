import {useState} from 'react';
import type {ChartRowView, MappingChoice} from './types';

type Props = {
  row: ChartRowView; keys: string[]; size: string; busy: boolean;
  confirm: (row: number, choice: MappingChoice) => Promise<boolean>;
};

const STATUS: Record<string, string> = {
  unmapped: 'Unmapped', not_used: 'Not used', confirmed: 'Confirmed', catalog: 'Buyer code', synonym: 'Synonym',
};

/** One chart row: its source name, the key it maps to, and the user's Confirm / Not used choice. */
export default function MappingRow({row, keys, size, busy, confirm}: Props) {
  const initial = row.suggestion?.key ?? (row.status === 'unmapped' || row.status === 'not_used' ? '' : row.key);
  const [choice, setChoice] = useState(initial);
  const suggestion = row.suggestion;
  return (
    <article className="mapping-row">
      <div className="mapping-source">
        <strong>{row.label}</strong>
        <small>Row {row.row} · {row.code} · {size} {row.base_value ?? '—'}{row.half ? ' · half' : ''}</small>
        <span className={`badge mapping-${row.status ?? 'manual'}`}>{STATUS[row.status ?? ''] ?? row.status}</span>
      </div>
      {suggestion && (
        <small className="mapping-suggestion">
          {suggestion.key
            ? `Suggested by ${suggestion.provider} · ${Math.round(suggestion.confidence * 100)}% · ${suggestion.reason}`
            : `${suggestion.provider}: ${suggestion.reason}`}
        </small>
      )}
      <div className="mapping-actions">
        <select aria-label={`Canonical key for ${row.label}`} value={choice} disabled={busy}
          onChange={(e) => setChoice(e.target.value)}>
          <option value="">Choose a measurement…</option>
          {keys.map((key) => <option key={key} value={key}>{key}</option>)}
        </select>
        <button className="primary" aria-label={`Confirm ${row.label}`} disabled={busy || !choice || choice === row.key}
          onClick={() => void confirm(row.row, {key: choice})}>Confirm</button>
        <button aria-label={`Mark ${row.label} not used`} disabled={busy || row.status === 'not_used'}
          onClick={() => void confirm(row.row, {not_used: true})}>Not used</button>
      </div>
    </article>
  );
}
