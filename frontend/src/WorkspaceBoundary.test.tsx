import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import WorkspaceBoundary from './WorkspaceBoundary';

afterEach(() => {cleanup(); vi.restoreAllMocks()});
it('keeps recovery controls available after a child fails and retries', () => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  let broken = true;
  function Screen() {if (broken) throw Error('Render failure'); return <h2>Recovered screen</h2>}
  render(<WorkspaceBoundary recover={vi.fn()}><Screen/></WorkspaceBoundary>);
  expect(screen.getByRole('alert').textContent).toContain('Your saved project is retained');
  broken = false;
  fireEvent.click(screen.getByRole('button', {name:'Retry workspace'}));
  expect(screen.getByRole('heading', {name:'Recovered screen'})).toBeTruthy();
});
