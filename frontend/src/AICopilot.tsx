import {Send, X} from 'lucide-react';
import {forwardRef, useEffect, useImperativeHandle, useRef, useState} from 'react';
import {api} from './api';

type Action = {id:string; intent:string; target:string; parameters:Record<string,unknown>;
  confidence:number; requires_confirmation:boolean; deterministic_service:string; post_action_validation:string};
type Props = {projectId:string; size:string; pieceId?:string; pieceName?:string; contextVersion?:string;
  refresh:()=>void|Promise<unknown>; showLaunch?:boolean};
export type CopilotHandle = {open:()=>void};

const AICopilot = forwardRef<CopilotHandle, Props>(function AICopilot(props, ref) {
  const [open, setOpen] = useState(false);
  const launch = useRef<HTMLButtonElement>(null);
  useImperativeHandle(ref, () => ({open: () => setOpen(true)}), []);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === '/') {event.preventDefault(); setOpen(true)}
      else if (event.key === 'Escape' && open) {setOpen(false); setTimeout(() => launch.current?.focus(), 0)}
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [open]);
  if (!open) {
    if (props.showLaunch === false) return null;
    return <button ref={launch} className="copilot-launch" onClick={() => setOpen(true)}>Ask AI</button>;
  }
  return <AssistantSession key={JSON.stringify([props.projectId, props.size, props.pieceId, props.contextVersion])}
    {...props} close={() => {
      setOpen(false);
      setTimeout(() => {
        (launch.current || document.querySelector<HTMLButtonElement>('[data-ask-ai]'))?.focus();
      }, 0);
    }}/>;
});
export default AICopilot;

function AssistantSession({projectId, size, pieceId, pieceName, refresh, close}: Props & {close:()=>void}) {
  const [prompt, setPrompt] = useState('');
  const [action, setAction] = useState<Action|null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef(true), pending = useRef(false);
  useEffect(() => {active.current = true; return () => {active.current = false}}, []);
  async function request(task:()=>Promise<void>) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {await task()}
    catch (e) {if (active.current) setError(e instanceof Error ? e.message : 'Assistant request failed')}
    finally {pending.current = false; if (active.current) setBusy(false)}
  }
  function propose(text = prompt) {
    if (!text.trim()) return;
    void request(async () => {
      setAction(null);
      const result = await api<Action>(`/projects/${projectId}/assistant/propose`, 'POST', {
        prompt: text, size, ...(pieceId ? {piece_id: pieceId} : {})});
      if (active.current) {setAction(result); setPrompt('')}
    });
  }
  function apply() {
    if (!action) return;
    void request(async () => {
      await api(`/projects/${projectId}/assistant/execute`, 'POST', {proposal_id: action.id, confirmed: true});
      if (active.current) {setAction(null); await refresh()}
    });
  }
  const prompts = [pieceId ? 'Explain selected piece' : 'Why is a requirement unresolved?',
    'Explain validation warnings', 'Add 1 cm seam allowance'];
  return <aside className="copilot card" aria-label="AI assistant" aria-busy={busy}>
    <header><div><strong>AI Copilot</strong><small>Size {size}{pieceId ? ` · ${pieceName || pieceId}` : ''}</small></div>
      <button aria-label="Close AI assistant" onClick={close}><X size={16}/></button></header>
    <p>Suggestions are proposals. Geometry comes from deterministic services and validators.</p>
    <div className="prompt-chips">{prompts.map(value => <button key={value} disabled={busy}
      onClick={() => propose(value)}>{value}</button>)}</div>
    <div role="status" aria-live="polite">{busy ? 'Working on your request…' : action ? 'Assistant response ready.' : ''}</div>
    {action && <article className="assistant-action">
      <span className="badge">{action.intent.replaceAll('_', ' ')}</span>
      <h3>{action.intent === 'explain' ? 'Understanding' : 'Proposed action'}</h3>
      {action.intent === 'explain' ? <p className="assistant-answer">{String(action.parameters.answer)}</p> :
        <dl>{Object.entries(action.parameters).map(([key, value]) => <div key={key}>
          <dt>{key.replaceAll('_', ' ')}</dt><dd>{String(value).replaceAll('_', ' ')}</dd></div>)}</dl>}
      {action.intent !== 'explain' && <><p>Confidence: {Math.round(action.confidence * 100)}%</p>
        <small>After action: {action.post_action_validation}</small>
        <button className="primary" disabled={busy} onClick={apply}>Confirm and apply</button></>}
    </article>}
    {error && <p className="error-text" role="alert">{error}</p>}
    <div className="copilot-input"><input autoFocus aria-label="Ask AI" value={prompt} disabled={busy}
      onChange={e => setPrompt(e.target.value)} placeholder="Ask or propose a supported action"
      onKeyDown={e => {if (e.key === 'Enter') propose()}}/>
      <button aria-label="Send to AI" disabled={busy || !prompt.trim()} onClick={() => propose()}><Send size={16}/></button></div>
  </aside>;
}
