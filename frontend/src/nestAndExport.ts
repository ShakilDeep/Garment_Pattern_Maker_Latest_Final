import {api, download} from './api';
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
    exportFile: async (kind: string) => {
      if (!project) throw new Error('Open a project before downloading.');
      const extension = kind.endsWith('svg') ? 'svg' : kind.endsWith('pdf') ? 'pdf' : kind;
      const markerExport = kind.startsWith('marker');
      const label = markerExport
        ? (project.marker?.size || project.pattern?.size || size)
        : size;
      const path = kind === 'calibration'
        ? `/projects/${project.id}/calibration-request`
        : markerExport
          ? `/projects/${project.id}/exports/${kind}`
          : `/projects/${project.id}/exports/${kind}?size=${encodeURIComponent(size)}`;
      const name = kind === 'calibration'
        ? 'production-calibration-request.txt'
        : `1078983_${label}_${markerExport ? 'marker' : 'pattern'}_demo.${extension}`;
      await run(() => download(path, name), 'Download ready.');
    },
  };
}
