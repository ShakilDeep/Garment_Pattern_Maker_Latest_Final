import type {Pattern, Project} from './types';

/** Single version-selection rule, mirrored by backend version_select.py: a graded size wins over the base pattern. */
export function selectForSize(project: Project | null, size: string): Pattern | null {
  if (!project) return null;
  const graded = (project.grades ?? []).find((grade) => grade.size === size);
  if (graded) return graded;
  return project.pattern?.size === size ? project.pattern : null;
}
