import {api} from '../api';
import type {StyleChoices} from '../styleDetectTypes';
import type {MutationContext} from './context';

/** Style detection: the user's confirmed style options; the user's choice always wins over the proposal. */
export function styleMutations(ctx: MutationContext) {
  const {project, refresh, run} = ctx;
  return {
    confirmStyle: async (choices: StyleChoices) => {
      if (!project) return false;
      return run(async () => {
        await api(`/projects/${project.id}/style/choices`, 'POST', choices);
        await refresh(project.id);
      }, 'Style confirmed.');
    },
  };
}
