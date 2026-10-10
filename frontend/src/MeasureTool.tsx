import {useId, useState} from 'react';
import {measure} from './styleApi';
import type {MeasureBody, MeasureKind, Measurement, StylePiece} from './styleTypes';

const KINDS: [MeasureKind, string][] = [
  ['distance', 'Distance between points'], ['path', 'Edge length'], ['angle', 'Angle at a point'],
  ['area', 'Area'], ['perimeter', 'Perimeter'],
];
const OUTLINES: [string, string][] = [['sew', 'Sew line'], ['cut', 'Cut line']];
const UNITS = {cm: 'cm', deg: '°', cm2: 'cm²'};

type FieldProps = {label: string; value: string; set: (value: string) => void; options: [string, string][]};

// A labelled select whose accessible name is only its label (not its option texts).
function Field({label, value, set, options}: FieldProps) {
  const id = useId();
  return (
    <div className="measure-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => set(e.target.value)}>
        {options.map(([option, text]) => <option key={option} value={option}>{text}</option>)}
      </select>
    </div>
  );
}

type Props = {styleId: string; size: string; piece: StylePiece};

// CAD-05: every value shown comes from the backend measure route, never from the browser.
export default function MeasureTool({styleId, size, piece}: Props) {
  const points = piece.points.map((p): [string, string] => [p.id, p.id]);
  const edges = piece.outline.map((s): [string, string] => [s.id, s.id]);
  const [kind, setKind] = useState<MeasureKind>('distance');
  const [a, setA] = useState(points[0][0]);
  const [b, setB] = useState((points[1] ?? points[0])[0]);
  const [edge, setEdge] = useState(edges[0][0]);
  const [outline, setOutline] = useState('sew');
  const [result, setResult] = useState<Measurement | null>(null);
  const [error, setError] = useState('');

  const body = (): MeasureBody => {
    const base = {size, piece_id: piece.id, kind};
    if (kind === 'distance') return {...base, points: [a, b]};
    if (kind === 'path') return {...base, edges: [edge]};
    if (kind === 'angle') return {...base, point: a};
    return {...base, outline: outline as 'sew' | 'cut'};
  };
  const run = async () => {
    setError('');
    try { setResult(await measure(styleId, body())); } catch (e) { setResult(null); setError((e as Error).message); }
  };

  return (
    <section className="measure-tool" aria-label={`Measure ${piece.name}`}>
      <h3>Measure {piece.name}</h3>
      <Field label="Measurement" value={kind} set={(v) => setKind(v as MeasureKind)} options={KINDS} />
      {kind === 'distance' && <Field label="From point" value={a} set={setA} options={points} />}
      {kind === 'distance' && <Field label="To point" value={b} set={setB} options={points} />}
      {kind === 'angle' && <Field label="Point" value={a} set={setA} options={points} />}
      {kind === 'path' && <Field label="Edge" value={edge} set={setEdge} options={edges} />}
      {(kind === 'area' || kind === 'perimeter') &&
        <Field label="Outline" value={outline} set={setOutline} options={OUTLINES} />}
      <button type="button" onClick={() => void run()}>Measure</button>
      {result && <output aria-label="Measurement result">{result.value.toFixed(2)} {UNITS[result.unit]}</output>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
