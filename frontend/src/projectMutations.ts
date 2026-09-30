import {lifecycleMutations} from './mutations/lifecycle';
import {measurementMutations} from './mutations/measurement';
import {patternMutations} from './mutations/pattern';
import type {MutationContext} from './mutations/context';
import {nestAndExport} from './nestAndExport';

/** Facade: every project mutation the app controller exposes, composed by responsibility. */
export function projectMutations(ctx: MutationContext) {
  const {project, size, refresh, run} = ctx;
  return {
    ...lifecycleMutations(ctx),
    ...measurementMutations(ctx),
    ...patternMutations(ctx),
    ...nestAndExport({project, size, refresh, run}),
  };
}
