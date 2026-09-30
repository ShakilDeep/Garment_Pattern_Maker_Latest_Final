import {api} from '../api';
import type {Evidence} from '../CalibrationReview';
import type {MutationContext} from './context';

export const MAX_UPLOAD_BYTES = 10_000_000;

/** Source and measurement inputs: save edits, resolve requirements, import and clear sources. */
export function measurementMutations(ctx: MutationContext) {
  const {project, size, refresh, run} = ctx;
  return {
    save: async (changes: Record<string, number>) => {
      if (!project) return false;
      return run(async () => {
        if (Object.keys(changes).length) await api(`/projects/${project.id}/measurements`, 'PATCH', {size, changes});
        await refresh(project.id);
      }, 'Measurements saved. Confirm your review in Requirements.');
    },
    resolve: async (key: string, value: string, evidence?: Evidence) => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/requirements/${key}/resolve`, 'POST', {value, ...evidence});
        await refresh(project.id);
      }, 'Requirement resolved and recorded.');
    },
    upload: async (file: File, replace = false) => {
      if (!project) return;
      if (file.size > MAX_UPLOAD_BYTES) { ctx.setError('Maximum upload size is 10 MB'); return; }
      const shouldReplace = replace || project.documents.length > 0;
      await run(async () => {
        const form = new FormData(); form.append('file', file);
        await api(`/projects/${project.id}/documents${shouldReplace ? '?replace=true' : ''}`, 'POST', form);
        await refresh(project.id);
      }, shouldReplace ? 'Source replaced. Review the retained version history.' : 'Document imported. Review extracted data and requirements.');
    },
    clearSources: async () => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/sources/clear`, 'POST');
        await refresh(project.id);
      }, 'Imported sources and pattern preview cleared.');
    },
  };
}
