import {AlertCircle, AlertTriangle, CheckCircle2, ExternalLink} from 'lucide-react';
import type {Project, Requirements} from './types';
import MissingInfoCenter from './MissingInfoCenter';

export default function ValidationCenter({
  project, requirements, go,
}: {project: Project; requirements: Requirements | null; go: (page: string) => void}) {
  const geometry = project.pattern?.validation || [];
  const unresolved = requirements?.blockers || [];
  const passed = geometry.filter((i) => i.severity === 'PASS').length;
  const warnings = geometry.filter((i) => i.severity === 'WARNING').length;
  const errors = geometry.filter((i) => i.severity === 'ERROR').length;
  return (
    <section className="workflow card validation-center">
      <div className="section-heading">
        <div>
          <h2>Validation Center</h2>
          <p>Engineering checks and unresolved source decisions for the current project.</p>
        </div>
        <span className="badge">{project.pattern?.size || 'No pattern'} · {project.state.replaceAll('_', ' ')}</span>
      </div>
      <span className="sr-only" role="status" aria-label="Validation status" aria-atomic="true">
        {passed} passed, {warnings} warnings, {errors} errors, {unresolved.length} unresolved requirements.
      </span>
      <div className="validation-counts">
        {([[passed, 'Passed', 'pass'], [warnings, 'Warnings', 'warn'], [errors, 'Errors', 'error'],
          [unresolved.length, 'Unresolved', 'open']] as const).map(([count, label, tone]) => (
          <article className={`card ${tone}`} key={label}><strong>{count}</strong><span>{label}</span></article>
        ))}
      </div>
      {!project.pattern && <div className="notice">Generate a pattern to run geometry validation.</div>}
      <MissingInfoCenter blockers={unresolved} go={go} />
      {geometry.map((item, index) => {
        const Icon = item.severity === 'PASS' ? CheckCircle2
          : item.severity === 'ERROR' ? AlertCircle : AlertTriangle;
        return (
          <article className={`issue-row ${item.severity.toLowerCase()}`} key={`${item.code}-${index}`}>
            <Icon />
            <div>
              <strong>{item.code.replaceAll('_', ' ')}</strong>
              <p>{item.message}</p>
              <small>Geometry rule · {item.piece || 'Pattern set'} · demo_v1</small>
            </div>
            {item.piece && (
              <button onClick={() => go('Pattern Studio')}>Inspect <ExternalLink size={14} /></button>
            )}
          </article>
        );
      })}
    </section>
  );
}
