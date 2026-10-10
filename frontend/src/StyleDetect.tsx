import {useEffect, useRef, useState} from 'react';
import {ScanSearch} from 'lucide-react';
import {api} from './api';
import StyleOptionRow from './StyleOptionRow';
import type {Project} from './types';
import {proposalValues, UNKNOWN, visibleSpecs, type OptionSpec, type StyleChoices, type StyleDetection,
  type StyleProposal} from './styleDetectTypes';

type Props = {project: Project; busy: boolean; confirm: (choices: StyleChoices) => Promise<boolean>};

const ACCEPT = 'image/png,image/jpeg,image/webp,application/pdf,.pdf';
const fromProposal = (proposal: StyleProposal) =>
  Object.fromEntries(Object.values(proposalValues(proposal)).map((guess) => [guess.id, guess.value]));

function initialValues(project: Project): Record<string, string> {
  const chosen = project.style_choices;
  if (chosen) return {garment: chosen.garment, fit: chosen.fit, ...chosen.options};
  return project.style_detection ? fromProposal(project.style_detection.proposal) : {};
}

/** Style options from an image: the AI proposes with confidence, the user edits; only Confirm stores it. */
export default function StyleDetect({project, busy, confirm}: Props) {
  const [specs, setSpecs] = useState<OptionSpec[]>([]);
  const [detection, setDetection] = useState<StyleDetection | undefined>(project.style_detection ?? undefined);
  const [values, setValues] = useState(() => initialValues(project));
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let ignore = false;
    api<OptionSpec[]>('/style/options').then((rows) => { if (!ignore) setSpecs(rows); })
      .catch((e: Error) => { if (!ignore) setError(e.message); });
    return () => { ignore = true; };
  }, []);

  async function detect(file: File | undefined) {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    setWorking(true); setError('');
    try {
      const found = await api<StyleDetection>(`/projects/${project.id}/style/detect`, 'POST', form);
      setDetection(found); setValues(fromProposal(found.proposal));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Detection failed. Choose the options manually.');
    } finally {
      setWorking(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  const value = (id: string) => values[id] ?? UNKNOWN;
  const garment = value('garment');
  const shown = visibleSpecs(specs, garment);
  const guesses = proposalValues(detection?.proposal);
  const locked = busy || working;
  function save() {
    const options = shown.filter((spec) => spec.id !== 'garment' && spec.id !== 'fit');
    void confirm({garment, fit: value('fit'), options: Object.fromEntries(options.map((s) => [s.id, value(s.id)]))});
  }

  return (
    <section className="style-detect" aria-label="Garment style">
      <div className="mapping-head">
        <h3>Garment style</h3>
        <label className={`browse-files${locked ? ' is-disabled' : ''}`} aria-disabled={locked || undefined}>
          <span className="browse-files-label"><ScanSearch size={15}/>Detect from image</span>
          <input ref={inputRef} className="browse-files-input" aria-label="Detect style from image" type="file"
            accept={ACCEPT} disabled={locked} onChange={(e) => void detect(e.target.files?.[0])}/>
        </label>
      </div>
      <p>{working ? 'Reading the image…' : detection
        ? `Proposed by ${detection.proposal.provider}. Check each option; your choice wins.`
        : 'Upload a photo or tech-pack flat, or choose each option yourself.'}</p>
      {error && <p role="alert" className="warning">{error}</p>}
      {shown.map((spec) => (
        <StyleOptionRow key={spec.id} spec={spec} value={value(spec.id)} guess={guesses[spec.id]} busy={locked}
          change={(id, next) => setValues((current) => ({...current, [id]: next}))}/>
      ))}
      <button className="primary" disabled={locked || garment === UNKNOWN} onClick={save}>Confirm style</button>
      {project.style_choices && <small>Confirmed {project.style_choices.garment} style is stored.</small>}
    </section>
  );
}
