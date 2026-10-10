import {useState} from 'react';
import {walk} from './styleApi';
import type {WalkPart, WalkResult} from './styleTypes';

// CAD-04: the sleeve cap walked against the body armhole (front, back and yoke) of the 1078375 block.
export const CAP: WalkPart[] = [{piece_id: 'Sleeve', points: ['UA_back', 'cap_crown', 'UA_front']}];
export const ARMHOLE: WalkPart[] = [
  {piece_id: 'FRT', points: ['SP', 'UA']},
  {piece_id: 'back', points: ['yoke_armhole', 'UA']},
  {piece_id: 'back_YK', points: ['SP', 'yoke_armhole']},
];

type Props = {styleId: string; size: string};

export default function WalkReadout({styleId, size}: Props) {
  const [result, setResult] = useState<WalkResult | null>(null);
  const [error, setError] = useState('');
  const run = async () => {
    setError('');
    try { setResult(await walk(styleId, size, CAP, ARMHOLE)); } catch (e) { setError((e as Error).message); }
  };
  return (
    <section className="walk-readout" aria-label="Sleeve cap walk">
      <h3>Sleeve cap vs armhole</h3>
      <button type="button" onClick={() => void run()}>Walk sleeve cap</button>
      {result && <dl>
        <dt>Sleeve cap</dt><dd>{result.first_cm.toFixed(2)} cm</dd>
        <dt>Armhole</dt><dd>{result.second_cm.toFixed(2)} cm</dd>
        <dt>Cap ease</dt><dd>{result.difference_cm.toFixed(2)} cm</dd>
      </dl>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
