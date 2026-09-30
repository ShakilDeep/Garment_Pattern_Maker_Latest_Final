import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import ReviewPanel from './ReviewPanel';
import AICopilot from './AICopilot';
import ProjectDashboard from './ProjectDashboard';
import {api} from './api';
import type {Project} from './types';

vi.mock('./api', () => ({api:vi.fn()}));
afterEach(() => {cleanup(); vi.resetAllMocks()});

it('requires a reviewer and previous approvals, and preserves retry after rejection', async () => {
  const reviews = ['source', 'measurements'].map(gate => ({gate, status:'PENDING', actor:null, at:null, note:''}));
  vi.mocked(api).mockResolvedValueOnce(reviews).mockRejectedValueOnce(Error('Review unavailable'))
    .mockResolvedValueOnce([{...reviews[0], status:'APPROVED_FOR_DEMO'}, reviews[1]]);
  render(<ReviewPanel projectId="test"/>);
  const approve = await screen.findByRole('button', {name:'Approve source for demo'});
  expect((approve as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Reviewer'), {target:{value:'Reviewer'}});
  expect((screen.getByRole('button', {name:'Approve measurements for demo'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(approve);
  expect((await screen.findByRole('alert')).textContent).toBe('Review unavailable');
  fireEvent.click(approve);
  await waitFor(() => expect((screen.getByRole('button', {name:'Approve measurements for demo'}) as HTMLButtonElement).disabled).toBe(false));
});

it('does not execute an AI proposal before explicit confirmation', async () => {
  const refresh = vi.fn();
  vi.mocked(api).mockResolvedValueOnce({id:'proposal', intent:'set_allowance', parameters:{allowance:1},
    confidence:1, deterministic_service:'commands', post_action_validation:'validate'})
    .mockResolvedValueOnce({});
  render(<AICopilot projectId="test" size="L" refresh={refresh}/>);
  fireEvent.click(screen.getByRole('button', {name:'Ask AI'}));
  fireEvent.change(screen.getByLabelText('Ask AI'), {target:{value:'Add 1 cm seam allowance'}});
  fireEvent.click(screen.getByRole('button', {name:'Send to AI'}));
  const confirm = await screen.findByRole('button', {name:'Confirm and apply'});
  expect(api).toHaveBeenCalledTimes(1);
  fireEvent.click(confirm);
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  expect(api).toHaveBeenLastCalledWith('/projects/test/assistant/execute', 'POST', {proposal_id:'proposal',confirmed:true});
});

it('shows project evidence and routes to the unfinished step', () => {
  const go = vi.fn(), rename = vi.fn();
  const project = {id:'test',name:'Shirt',documents:[],measurements:[],resolutions:{},
    pattern:null,grades:[],marker:null,state:'DRAFT',techpack:null} as unknown as Project;
  render(<ProjectDashboard project={project} requirements={null} go={go} rename={rename} remove={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button', {name: /^Files imported/}));
  expect(go).toHaveBeenCalledWith('Measurements');
  expect(screen.getByRole('list', {name:'First-run checkpoints'})).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Project name'), {target:{value:'New name'}});
  fireEvent.click(screen.getByRole('button', {name:'Rename'}));
  expect(rename).toHaveBeenCalledWith('New name');
});
