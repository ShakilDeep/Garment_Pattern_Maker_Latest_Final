import {useMemo, useState} from 'react';
import {AlertCircle, ExternalLink} from 'lucide-react';
import type {Requirements} from './types';

type Blocker = Requirements['blockers'][number];
type Filter = 'all' | 'blocking' | 'nonblocking';

const ORDER: Record<string, number> = {
  MISSING: 0, CONFLICTING: 1, AMBIGUOUS: 2, DEMO_DEFAULT_AVAILABLE: 3,
};

function sortBlockers(items: Blocker[]): Blocker[] {
  return [...items].sort((a, b) =>
    Number(b.blocking) - Number(a.blocking)
    || (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9)
    || a.name.localeCompare(b.name));
}

export default function MissingInfoCenter({
  blockers, go,
}: {blockers: Blocker[]; go: (page: string) => void}) {
  const [filter, setFilter] = useState<Filter>('all');
  const rows = useMemo(() => {
    const sorted = sortBlockers(blockers);
    if (filter === 'blocking') return sorted.filter((i) => i.blocking);
    if (filter === 'nonblocking') return sorted.filter((i) => !i.blocking);
    return sorted;
  }, [blockers, filter]);
  const next = rows[0];

  return (
    <section className="missing-info-center" aria-label="Missing information center">
      <div className="section-heading">
        <div>
          <h3>Missing Information Center</h3>
          <p>Guided queue of unresolved source decisions for this project.</p>
        </div>
        <label>Filter
          <select aria-label="Missing info filter" value={filter}
            onChange={(e) => setFilter(e.target.value as Filter)}>
            <option value="all">All</option>
            <option value="blocking">Blocking</option>
            <option value="nonblocking">Non-blocking</option>
          </select>
        </label>
      </div>
      {next && <p className="notice" role="status">Next: {next.name}</p>}
      {!rows.length && <p className="success">No unresolved items in this filter.</p>}
      {rows.map((item) => (
        <article className="issue-row" key={item.key}>
          <AlertCircle />
          <div>
            <strong>{item.name}</strong>
            <p>{item.why}</p>
            <small>
              From: {item.source} · Accepted: {(item.accepted_units || []).join(', ') || 'n/a'}
              {' '}· Default: {item.fallback_policy || 'No automatic default'}
              {' '}· {item.blocking ? 'Blocks generation' : 'Non-blocking'}
            </small>
          </div>
          <button onClick={() => go(item.key.startsWith('measurement:') ? 'Measurements' : 'Requirements')}>
            Resolve <ExternalLink size={14} />
          </button>
        </article>
      ))}
    </section>
  );
}
