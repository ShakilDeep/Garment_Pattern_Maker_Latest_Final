import type {OptionGuess, OptionSpec} from './styleDetectTypes';

type Props = {spec: OptionSpec; value: string; guess?: OptionGuess; busy: boolean;
  change: (id: string, value: string) => void};

const words = (choice: string) => choice.replaceAll('_', ' ');

/** One style option: a select pre-filled from the proposal; the badge says whose value it is. */
export default function StyleOptionRow({spec, value, guess, busy, change}: Props) {
  const fromAi = guess !== undefined && guess.value === value && value !== 'unknown';
  return (
    <label className="style-option" title={spec.note || undefined}>
      <span>{spec.label}</span>
      <select aria-label={spec.label} value={value} disabled={busy}
        onChange={(e) => change(spec.id, e.target.value)}>
        {spec.choices.map((choice) => <option key={choice} value={choice}>{words(choice)}</option>)}
      </select>
      <small className={fromAi ? 'style-ai' : 'style-user'}>
        {fromAi ? `AI ${Math.round(guess.confidence * 100)}%` : value === 'unknown' ? 'Not set' : 'Your choice'}
      </small>
    </label>
  );
}
