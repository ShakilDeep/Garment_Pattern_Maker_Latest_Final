import {api} from '../api';
import type {MappingChoice} from '../types';
import type {MutationContext} from './context';

/** POM mapping: the user's confirmation of a canonical key (or "not used") for one chart row. */
export function mappingMutations(ctx: MutationContext) {
  const {project, refresh, run} = ctx;
  return {
    confirmMapping: async (row: number, choice: MappingChoice) => {
      if (!project) return false;
      return run(async () => {
        await api(`/projects/${project.id}/mappings/${row}`, 'POST', choice);
        await refresh(project.id);
      }, 'Mapping confirmed. Regenerate the pattern to use it.');
    },
  };
}
