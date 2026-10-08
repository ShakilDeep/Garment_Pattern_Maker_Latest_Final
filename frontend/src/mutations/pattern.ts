import {api} from '../api';
import {projectSizes} from '../projectSizes';
import type {MutationContext} from './context';

/** Generate, grade and clear the pattern for the current project. */
export function patternMutations(ctx: MutationContext) {
  const {project, size, allowance, requirements, go, refresh, run} = ctx;
  return {
    generate: async () => {
      if (!project) return;
      if (!requirements?.ready) { go('Requirements'); return; }
      go('Measurements');
      await run(async () => {
        await api(`/projects/${project.id}/patterns/generate`, 'POST', {size, allowance});
        await refresh(project.id);
      }, 'Demo pattern generated. Review the validation warnings.');
    },
    grade: async () => {
      if (!project) return;
      const sizes = projectSizes(project);
      await run(async () => {
        await api(`/projects/${project.id}/grade`, 'POST', {sizes});
        await refresh(project.id);
      }, `All ${sizes.length} sizes generated from source measurements.`);
    },
    clearPattern: async () => {
      if (!project) return;
      await run(async () => {
        await api(`/projects/${project.id}/patterns/clear`, 'POST');
        await refresh(project.id);
      }, 'Pattern preview cleared.');
    },
  };
}
