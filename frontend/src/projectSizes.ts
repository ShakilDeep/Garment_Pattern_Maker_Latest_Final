import {sizes as DEMO_SIZES, type Project} from './types';

/** The project's size list comes from its imported chart; the demo's S–3XL is only the fallback. */
export function projectSizes(project: Project | null | undefined): string[] {
  return project?.chart?.sizes?.length ? project.chart.sizes : DEMO_SIZES;
}

/** The base size the user chose, else the detected one, else the first size of the chart. */
export function defaultSize(project: Project | null | undefined): string {
  const list = projectSizes(project);
  const base = project?.resolutions?.base_size ?? project?.chart?.base_size;
  return base && list.includes(base) ? base : list[0];
}
