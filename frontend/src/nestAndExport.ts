import {api, download} from './api';
import {projectSizes} from './projectSizes';
import type {Project} from './types';

type NestCtx = {
  project: Project | null;
  size: string;
  refresh: (id: string) => Promise<Project>;
  run: (task: () => Promise<unknown>, success?: string) => Promise<boolean>;
};

export function nestAndExport(ctx: NestCtx) {
  const {project, size, refresh, run} = ctx;
  return {
    nest: async (width: number, quantity: number | Record<string, number>, gap: number) => {
      if (!project) return;
      const extras = {seed: 0, iterations: 3, time_budget_ms: 250};
      await run(async () => {
        await api(`/projects/${project.id}/markers/generate`, 'POST',
          typeof quantity === 'number'
            ? {size, width, quantity, gap, ...extras}
            : {width, gap, quantities: quantity, ...extras});
        await refresh(project.id);
      }, 'Marker calculated from actual piece areas and quantities.');
    },
    exportFile: async (kind: string, unit?: string) => {
      if (!project) throw new Error('Open a project before downloading.');
      const extension = kind.endsWith('svg') ? 'svg' : kind.endsWith('pdf') ? 'pdf' : kind.startsWith('dxf') ? 'dxf' : kind;
      const markerExport = kind.startsWith('marker');
      const label = markerExport
        ? (project.marker?.size || project.pattern?.size || size)
        : size;
      if (kind === 'aama-graded') { // every size as one zip for Optitex (T146): no size parameter
        const name = `${project.resolutions?.profile ?? 'pattern'}_graded_aama.zip`;
        const query = unit ? `?unit=${encodeURIComponent(unit)}` : '';
        const sizes = projectSizes(project);
        const missing = sizes.some((s) => !drafted(project).has(s));  // Optitex needs every size: grade them first
        await run(async () => {
          if (missing) {
            await api(`/projects/${project.id}/grade`, 'POST', {sizes});
            await refresh(project.id);
          }
          await download(`/projects/${project.id}/exports/aama-graded${query}`, name);
        }, missing ? `All ${sizes.length} sizes graded; download ready.` : 'Download ready.');
        return;
      }
      const path = kind === 'calibration'
        ? `/projects/${project.id}/calibration-request`
        : markerExport
          ? `/projects/${project.id}/exports/${kind}`
          : `/projects/${project.id}/exports/${kind}?size=${encodeURIComponent(size)}${dxfUnit(kind, unit)}`;
      const name = kind === 'calibration'
        ? 'production-calibration-request.txt'
        : `1078983_${label}_${markerExport ? 'marker' : 'pattern'}_demo${kind === 'dxf-aama' ? '_aama' : ''}.${extension}`;
      await run(() => download(path, name), 'Download ready.');
    },
  };
}

/** The sizes the project has a current (not stale) pattern for: its base pattern and its grades. */
function drafted(project: Project): Set<string> {
  const current = [project.pattern, ...(project.grades ?? [])].filter((p) => p && !p.stale);
  return new Set(current.map((p) => p!.size));
}

function dxfUnit(kind: string, unit?: string) {
  return kind.startsWith('dxf') && unit ? `&unit=${encodeURIComponent(unit)}` : '';
}
