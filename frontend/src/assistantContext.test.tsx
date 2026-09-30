import {afterEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import AICopilot from './AICopilot';
import {api} from './api';

vi.mock('./api', () => ({api:vi.fn()}));
afterEach(() => {cleanup();vi.resetAllMocks()});
const action = {id:'proposal',intent:'set_allowance',target:'pattern',parameters:{value:1},
  confidence:.99,requires_confirmation:true,deterministic_service:'cad_commands',post_action_validation:'Validate geometry'};

it('sends selected piece context and displays explanations as readable text', async () => {
  vi.mocked(api).mockResolvedValue({...action,intent:'explain',parameters:{answer:'Sleeve: 40 × 60 cm.'}});
  render(<AICopilot projectId="one" size="L" pieceId="sleeve" pieceName="Sleeve" refresh={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Ask AI'}));
  fireEvent.click(screen.getByRole('button',{name:'Explain selected piece'}));
  expect(await screen.findByText('Sleeve: 40 × 60 cm.')).toBeTruthy();
  expect(api).toHaveBeenCalledWith('/projects/one/assistant/propose','POST',{
    prompt:'Explain selected piece',size:'L',piece_id:'sleeve'});
  expect(screen.queryByRole('button',{name:'Confirm and apply'})).toBeNull();
});

it('discards a delayed response after changing project and size', async () => {
  let resolve!:(value:unknown)=>void;
  vi.mocked(api).mockImplementationOnce(()=>new Promise(r=>{resolve=r}));
  const {rerender}=render(<AICopilot projectId="one" size="L" refresh={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Ask AI'}));
  fireEvent.click(screen.getByRole('button',{name:'Add 1 cm seam allowance'}));
  rerender(<AICopilot projectId="two" size="M" refresh={vi.fn()}/>);
  await act(async()=>resolve(action));
  expect(screen.queryByRole('button',{name:'Confirm and apply'})).toBeNull();
  expect(screen.getByLabelText('Ask AI')).toHaveProperty('value','');
});

it('clears an existing proposal when selection changes and blocks duplicate requests', async () => {
  vi.mocked(api).mockResolvedValue(action);
  const {rerender}=render(<AICopilot projectId="one" size="L" pieceId="front" refresh={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Ask AI'}));
  const chip=screen.getByRole('button',{name:'Add 1 cm seam allowance'});
  fireEvent.click(chip);fireEvent.click(chip);
  await screen.findByRole('button',{name:'Confirm and apply'});
  expect(api).toHaveBeenCalledTimes(1);
  rerender(<AICopilot projectId="one" size="L" pieceId="back" refresh={vi.fn()}/>);
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Confirm and apply'})).toBeNull());
});
