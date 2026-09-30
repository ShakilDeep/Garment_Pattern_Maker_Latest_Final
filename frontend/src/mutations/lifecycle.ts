import {api} from '../api';
import type {Project} from '../types';
import type {ProjectListItem} from '../useAppController';
import type {MutationContext} from './context';

/** Create, rename, delete, archive and restore the current project. */
export function lifecycleMutations(ctx: MutationContext) {
  const {project, go, refresh, run} = ctx;
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
  };
}
