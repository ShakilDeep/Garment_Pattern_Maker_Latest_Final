import {useEffect, useState} from 'react';
import {sizes, type Project} from './types';
import {api} from './api';

type Props = {
  project: Project;
  size: string;
  setSize: (size: string) => void;
  busy: boolean;
  nest: (width: number, quantity: number | Record<string, number>, gap: number) => void;
  download?: (kind: string) => void;
};

export default function MarkerPanel({project: p, size, setSize, busy, nest, download}: Props) {
  const [width, setWidth] = useState('150');
  const [gap, setGap] = useState('0.5');
  const [quantity, setQuantity] = useState('1');
  const [combined, setCombined] = useState(false);
  const [counts, setCounts] = useState<Record<string, string>>({[size]: '1'});
  const [compare, setCompare] = useState<{length_delta?: number} | null>(null);
  useEffect(() => {
    let live = true;
    if (!p.marker || !p.previous_marker) {setCompare(null); return}
    api<{length_delta?: number}>(`/projects/${p.id}/markers/compare`)
      .then((data) => {if (live) setCompare(data)})
      .catch(() => {if (live) setCompare(null)});
    return () => {live = false};
  }, [p.id, p.marker, p.previous_marker]);
  const generated = [p.pattern, ...p.grades].filter(g => g && !g.stale).map(g => g!.size);
  const quantities = Object.fromEntries(sizes.filter(s => generated.includes(s) && Number(counts[s]) > 0)
    .map(s => [s, Number(counts[s])]));
  const total = combined ? Object.values(quantities).reduce((a, b) => a + b, 0) : Number(quantity);
  const whole = (value: number) => Number.isInteger(value) && value >= 0;
  const validCounts = combined ? generated.every(s => whole(Number(counts[s] || '0'))) : whole(total);
  const current = Boolean(p.pattern && !p.pattern.stale);
  const valid = current && validCounts && total > 0 && total <= 20 &&
    Number(width) > 20 && Number(width) <= 500 && Number(gap) >= .1 && Number(gap) <= 5 &&
    (combined || generated.includes(size));

  return <section className="workflow card">
    <h2>Marker Nesting</h2><p>Arrange generated pieces using the garment quantities in your cut order.</p>
    {!current && <p className="notice">Generate a current pattern before nesting.</p>}
    <div className="marker-inputs">
      <label>Fabric width (cm)<input aria-label="Fabric width" type="number" value={width} onChange={e => setWidth(e.target.value)}/></label>
      <label>Gap (cm)<input aria-label="Piece gap" type="number" step=".1" value={gap} onChange={e => setGap(e.target.value)}/></label>
      <label><input type="checkbox" checked={combined} onChange={e => setCombined(e.target.checked)}/>Combine sizes</label>
      {!combined && <>
        <label>Size<select value={size} onChange={e => setSize(e.target.value)}>{sizes.map(s => <option key={s}>{s}</option>)}</select></label>
        <label>Garments<input aria-label="Garment quantity" type="number" value={quantity} onChange={e => setQuantity(e.target.value)}/></label>
      </>}
    </div>
    {combined && <div className="marker-inputs">{sizes.map(s => <label key={s}>{s} garments
      <input aria-label={`${s} garment quantity`} type="number" min="0" max="20" step="1"
        disabled={!generated.includes(s)} value={counts[s] || '0'}
        onChange={e => setCounts({...counts, [s]: e.target.value})}/>
    </label>)}</div>}
    <button className="primary" disabled={busy || !valid}
      onClick={() => nest(Number(width), combined ? quantities : total, Number(gap))}>Optimize marker</button>
    <p>Vertical grain · No rotation · Up to 20 garments per marker</p>
    <span className="sr-only" role="status" aria-label="Marker status" aria-atomic="true">{busy?'Calculating marker':p.marker?`Marker complete. ${p.marker.placements.length} pieces, ${p.marker.utilization.toFixed(1)}% utilization.`:'No marker generated'}</span>
    {p.marker && <>
      <div className="metrics"><strong>{p.marker.utilization.toFixed(1)}% utilization</strong>
        <span>{p.marker.waste.toFixed(1)}% waste</span><span>{(p.marker.length / 100).toFixed(2)} m length</span>
        <span>{p.marker.placements.length} pieces</span></div>
      <div className="actions" aria-label="Marker downloads">
        <button type="button" className="primary" disabled={busy || !download}
          onClick={() => { void download?.('marker-svg'); }}>Download marker SVG</button>
        <button type="button" disabled={busy || !download}
          onClick={() => { void download?.('marker-pdf'); }}>Download marker PDF</button>
      </div>
      <svg className="marker-canvas" viewBox={`0 0 ${p.marker.width} ${p.marker.length}`} aria-label="Marker layout">
        <rect width={p.marker.width} height={p.marker.length} fill="var(--soft)"/>
        {p.previous_marker && <g opacity=".35" aria-label="Previous marker layout">
          {p.previous_marker.placements.map((item, i) => <g key={`prev-${i}`} transform={`translate(${item.x} ${item.y})`}>
            <polygon points={item.points.map(pt => pt.join(',')).join(' ')} fill="none" stroke="var(--ink)" strokeWidth=".25"/>
          </g>)}
        </g>}
        {p.marker.placements.map((item, i) => <g key={i} transform={`translate(${item.x} ${item.y})`}>
          <polygon points={item.points.map(pt => pt.join(',')).join(' ')} fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth=".2"/>
          <text x={item.width / 2} y={item.height / 2} textAnchor="middle" fontSize="2.2">{item.name}</text>
        </g>)}
      </svg>
      {p.previous_marker && <p className="notice">Previous marker: {p.previous_marker.utilization.toFixed(1)}% utilization,
        {' '}{(p.previous_marker.length / 100).toFixed(2)} m length. Compare equivalent quantities and fabric widths.
        {compare && Number.isFinite(compare.length_delta) ? ` Length delta ${compare.length_delta} cm.` : ''}</p>}
    </>}
  </section>;
}
