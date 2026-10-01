import {afterEach, expect, it, vi} from 'vitest';
import {act, cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {createRef} from 'react';
import AICopilot, {type CopilotHandle} from './AICopilot';

vi.mock('./api', () => ({api: vi.fn()}));
afterEach(cleanup);

function renderWithHeaderLaunch() {
  const copilot = createRef<CopilotHandle>();
  render(<><button data-ask-ai onClick={() => copilot.current?.open()}>Ask AI</button>
    <AICopilot ref={copilot} projectId="one" size="M" refresh={vi.fn()} showLaunch={false}/></>);
  fireEvent.click(screen.getByRole('button', {name: 'Ask AI'}));
  return screen.getByRole('button', {name: 'Ask AI'});
}

it('returns focus to the header Ask AI button when Escape closes the panel', async () => {
  const header = renderWithHeaderLaunch();
  await act(async () => {fireEvent.keyDown(window, {key: 'Escape'})});
  await waitFor(() => expect(document.activeElement).toBe(header));
  expect(screen.queryByRole('complementary', {name: 'AI assistant'})).toBeNull();
});

it('returns focus to the header Ask AI button when the close button is used', async () => {
  const header = renderWithHeaderLaunch();
  fireEvent.click(screen.getByRole('button', {name: /close/i}));
  await waitFor(() => expect(document.activeElement).toBe(header));
});
