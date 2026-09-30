import type {Dispatch, SetStateAction} from 'react';
import {api} from './api';
import type {Project, Requirements} from './types';
import type {Evidence} from './CalibrationReview';
import type {ProjectListItem} from './useAppController';
import {nestAndExport} from './nestAndExport';

type Ctx = {
  project: Project | null; size: string; allowance: number; requirements: Requirements | null;
  go: (page: string) => void; refresh: (id: string) => Promise<Project>;
  run: (task: () => Promise<unknown>, success?: string) => Promise<boolean>;
  setDialog: Dispatch<SetStateAction<string>>; setProject: Dispatch<SetStateAction<Project | null>>;
  setProjects: Dispatch<SetStateAction<ProjectListItem[]>>;
  setRequirements: Dispatch<SetStateAction<Requirements | null>>; setError: Dispatch<SetStateAction<string>>;
};

export function projectMutations(ctx: Ctx) {
  const {project, size, allowance, requirements, go, refresh, run} = ctx;
  return {
    create: async (name: string, demo: boolean) => {
      await run(async () => {
        const p = await api<Project>('/projects', 'POST', {name, demo});
        await refresh(p.id); ctx.setDialog(''); go('Measurements');
      }, 'Project created. Review your source measurements.');
    },
    rename: async (name: string) => {
      if (!project) return;
      await run(async () => { await api(`/projects/${project.id}`, 'PATCH', {name}); await refresh(project.id); }, 'Project renamed.');
    },
    remove: async () => {
      if (!project || !window.confirm(`Delete ${project.name}? This cannot be undone.`)) return;
      await run(async () => {
        await api(`/projects/${project.id}`, 'DELETE');
        localStorage.removeItem('garment-project');
        const remaining = await api<ProjectListItem[]>('/projects');
        ctx.setProjects(remaining);
        if (remaining[0]) await refresh(remaining[0].id);
        else { ctx.setProject(null); ctx.setRequirements(null); ctx.setDialog('projects'); }
      }, 'Project deleted.');
    },
    archive: async () => {
      if (!project) return;
      await run(async () => { await api(`/projects/${project.id}/archive`, 'POST'); await refresh(project.id); }, 'Project archived.');
    },
    restore: async () => {
      if (!project) return;
      await run(async () => { await api(`/projects/${project.id}/restore`, 'POST'); await refresh(project.id); }, 'Project restored.');
    },
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
    generate: async () => {
      if (!project) return;
      if (!requirements?.ready) { go('Requirements'); return; }
      go('Measurements');
      await run(async () => {
        await api(`/projects/${project.id}/patterns/generate`, 'POST', {size, allowance});
        await refresh(project.id);
      }, 'Demo pattern generated. Review the validation warnings.');
    },
    upload: async (file: File, replace = false) => {
      if (!project) return;
      if (file.size > 10_000_000) { ctx.setError('Maximum upload size is 10 MB'); return; }
      const shouldReplace = replace || project.documents.length > 0;
      await run(async () => {
        const form = new FormData(); form.append('file', file);
        await api(`/projects/${project.id}/documents${shouldReplace ? '?replace=true' : ''}`, 'POST', form);
        await refresh(project.id);
      }, shouldReplace ? 'Source replaced. Review the retained version history.' : 'Document imported. Review extracted data and requirements.');
    },
    grade: async () => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/grade`, 'POST', {sizes: ['S', 'M', 'L', 'XL', 'XXL', '3XL']});
        await refresh(project.id);
      }, 'All six sizes generated from source measurements.');
    },
    clearPattern: async () => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/patterns/clear`, 'POST');
        await refresh(project.id);
      }, 'Pattern preview cleared.');
    },
    clearSources: async () => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/sources/clear`, 'POST');
        await refresh(project.id);
      }, 'Imported sources and pattern preview cleared.');
    },
    ...nestAndExport({project, size, refresh, run}),
  };
}
