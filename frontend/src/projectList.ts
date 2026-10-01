import {api} from './api';
import type {Page, ProjectListItem} from './types';

/** The project picker lists the first page; the demo never approaches the page size. */
export async function listProjects(): Promise<ProjectListItem[]> {
  return (await api<Page<ProjectListItem>>('/projects')).items;
}
