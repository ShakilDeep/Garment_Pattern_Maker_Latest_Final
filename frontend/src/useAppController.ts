import {useCallback, useEffect, useState} from 'react';
import {api} from './api';
import type {Project, ProjectListItem, Requirements} from './types';
import {listProjects} from './projectList';
import {guardedGo} from './navigationGuard';
import {projectMutations} from './projectMutations';
import {bootProjectsDialog, shouldRestoreLastProject} from './startup';
import {useHashPage} from './useHashPage';
import {useKeyboardShortcuts} from './useKeyboardShortcuts';

export function useAppController() {
  const [project, setProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [page, setPage] = useHashPage();
  const [size, setSize] = useState('M');
  const [requirements, setRequirements] = useState<Requirements | null>(null);
  const [selected, select] = useState('');
  const [dialog, setDialog] = useState(bootProjectsDialog);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [allowance, setAllowance] = useState(1);
  const [draftDirty, setDraftDirty] = useState(false);

  const go = useCallback((p: string) => {
    guardedGo(draftDirty, p, (next) => { setPage(next); location.hash = encodeURIComponent(next); });
  }, [draftDirty]);

  const refresh = useCallback(async (id: string) => {
    const p = await api<Project>('/projects/' + id);
    setProject(p);
    localStorage.setItem('garment-project', id);
    setRequirements(await api<Requirements>(`/projects/${id}/requirements?size=${size}`));
    setProjects(await listProjects());
    return p;
  }, [size]);

  async function run(task: () => Promise<unknown>, success = ''): Promise<boolean> {
    setBusy(true); setError('');
    try { await task(); if (success) setMessage(success); return true; }
    catch (e) { setError(e instanceof Error ? e.message : 'The operation failed. Please retry.'); return false; }
    finally { setBusy(false); }
  }

  useEffect(() => {
    let active = true;
    listProjects().then(async (items) => {
      if (!active) return;
      setProjects(items);
      if (shouldRestoreLastProject()) {
        const remembered = localStorage.getItem('garment-project');
        const id = items.find((p) => p.id === remembered)?.id
          || items.find((p) => !p.archived)?.id || items[0]?.id;
        if (id) { await refresh(id); return; }
      }
      setDialog(bootProjectsDialog());
    }).catch((e) => setError(e.message));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (project) {
      api<Requirements>(`/projects/${project.id}/requirements?size=${size}`)
        .then(setRequirements).catch((e) => setError(e.message));
    }
  }, [size, project?.id]);

  const history = useCallback((direction: string) => {
    if (project) void run(async () => {
      await api(`/projects/${project.id}/history/${direction}`, 'POST');
      await refresh(project.id);
    }, `Measurement ${direction} saved`);
  }, [project, refresh]);

  useKeyboardShortcuts(setDialog, history);

  const mutations = projectMutations({
    project, size, allowance, requirements, go, refresh, run,
    setDialog, setProject, setProjects, setRequirements, setError,
  });

  return {
    project, projects, page, size, setSize, requirements, selected, select, dialog, setDialog,
    busy, message, error, setError, setMessage, allowance, setAllowance, setDraftDirty,
    go, refresh, run, history, ...mutations,
  };
}
