import type {Dispatch, SetStateAction} from 'react';
import type {Project, Requirements} from '../types';
import type {ProjectListItem} from '../useAppController';

/** State and callbacks the project mutations need from the app controller. */
export type MutationContext = {
  project: Project | null; size: string; allowance: number; requirements: Requirements | null;
  go: (page: string) => void; refresh: (id: string) => Promise<Project>;
  run: (task: () => Promise<unknown>, success?: string) => Promise<boolean>;
  setDialog: Dispatch<SetStateAction<string>>; setProject: Dispatch<SetStateAction<Project | null>>;
  setProjects: Dispatch<SetStateAction<ProjectListItem[]>>;
  setRequirements: Dispatch<SetStateAction<Requirements | null>>; setError: Dispatch<SetStateAction<string>>;
};
