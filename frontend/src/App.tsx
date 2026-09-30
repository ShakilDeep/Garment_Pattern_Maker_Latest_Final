import {useRef} from 'react';
import {LoaderCircle, Undo2, Redo2, AlertCircle, X} from 'lucide-react';
import type {Pattern} from './types';
import Shell, {navigation} from './Shell';
import Measurements from './Measurements';
import Preview from './Preview';
import Workflow from './Workflow';
import Dialogs from './Dialogs';
import StudioControls from './StudioControls';
import ProjectDashboard from './ProjectDashboard';
import AICopilot, {type CopilotHandle} from './AICopilot';
import WorkspaceBoundary from './WorkspaceBoundary';
import {useAppController} from './useAppController';
import {api} from './api';

export default function App() {
  const copilot = useRef<CopilotHandle>(null);
  const c = useAppController();
  const pattern: Pattern | null = c.project?.grades.find((g) => g.size === c.size)
    || (c.project?.pattern?.size === c.size ? c.project.pattern : null);
  const showPreview = ['Measurements', 'Pattern Studio', 'Grading'].includes(c.page);
  return <>
    <Shell project={c.project} page={c.page} go={c.go} open={c.setDialog} projects={c.projects}
      choose={(id) => void c.run(() => c.refresh(id))} askAi={c.project ? () => copilot.current?.open() : undefined} />
    <main className={showPreview ? 'main-workspace' : 'main-workspace single-workspace'}>
      {!c.project ? <div className="welcome card"><h1>From measurements to your first pattern</h1>
        <p>A guided workspace for shirt development.</p>
        <button className="primary" onClick={() => c.setDialog('projects')}>Create or open a demo project</button></div> : <>
        {showPreview && <Measurements project={c.project} size={c.size} setSize={c.setSize} save={c.save}
          upload={c.upload} open={() => c.setDialog('measurements')} busy={c.busy}
          onDirtyChange={c.setDraftDirty} clearSources={c.clearSources} />}
        <div className="main-content">
          <WorkspaceBoundary key={`${c.project.id}:${c.page}`} recover={() => c.go('Measurements')}>
            {c.page === 'Project Dashboard' && <ProjectDashboard project={c.project} requirements={c.requirements}
              go={c.go} rename={(name) => void c.rename(name)} remove={() => void c.remove()}
              archive={() => void c.archive()} restore={() => void c.restore()} projects={c.projects}
              choose={(id) => void c.run(() => c.refresh(id))} />}
            {c.page === 'Pattern Studio' && <StudioControls project={c.project} size={c.size} selected={c.selected}
              refresh={() => void c.refresh(c.project!.id)} />}
            {c.page !== 'Measurements' && c.page !== 'Pattern Studio' && c.page !== 'Project Dashboard' &&
              <Workflow page={c.page} project={c.project} requirements={c.requirements} resolve={c.resolve}
                generate={c.generate} grade={c.grade} nest={c.nest} download={c.exportFile} busy={c.busy}
                size={c.size} setSize={c.setSize} open={c.setDialog} go={c.go} />}
            {showPreview && <Preview project={c.project} pattern={pattern} size={c.size} page={c.page}
              selected={c.selected} select={c.select} go={c.go} generate={c.generate} busy={c.busy}
              validate={() => void c.run(async () => {
                await api(`/projects/${c.project!.id}/validate`, 'POST'); await c.refresh(c.project!.id);
              }, 'Validation refreshed.')} />}
          </WorkspaceBoundary>
        </div>
      </>}
      {!navigation.includes(c.page) && <button onClick={() => c.go('Measurements')}>Return to Measurements</button>}
    </main>
    {c.project && c.page === 'Pattern Studio' && <div className="history-controls">
      <button disabled={c.busy || !c.project.undo.length} onClick={() => c.history('undo')}><Undo2 size={16} />Undo edit</button>
      <button disabled={c.busy || !c.project.redo.length} onClick={() => c.history('redo')}><Redo2 size={16} />Redo edit</button>
    </div>}
    {(c.busy || c.error || c.message) && <div className={`toast ${c.error ? 'error' : ''}`} role={c.error ? 'alert' : 'status'}>
      {c.busy ? <><LoaderCircle className="spin" size={18} />Processing…</>
        : <>{c.error ? <AlertCircle size={18} /> : null}<span>{c.error || c.message}</span>
          <button aria-label="Dismiss notification" onClick={() => { c.setError(''); c.setMessage(''); }}><X size={16} /></button></>}
    </div>}
    {c.dialog && <Dialogs key={c.dialog} name={c.dialog} close={() => c.setDialog('')} project={c.project}
      create={c.create} go={c.go} save={c.save} size={c.size} setSize={c.setSize} allowance={c.allowance}
      setAllowance={c.setAllowance} busy={c.busy} canGenerate={Boolean(c.requirements?.ready)}
      hasPattern={Boolean(pattern && !pattern.stale)} />}
    {c.project && <AICopilot ref={copilot} projectId={c.project.id} size={c.size}
      pieceId={pattern?.pieces.find((p) => p.id === c.selected)?.id}
      pieceName={pattern?.pieces.find((p) => p.id === c.selected)?.name}
      contextVersion={c.project.updated_at} refresh={() => c.refresh(c.project!.id)} showLaunch={false} />}
  </>;
}
