import {cleanup, fireEvent, screen, waitFor} from '@testing-library/react';
import {afterEach, describe, expect, it} from 'vitest';
import {setup} from './measurementsFixture';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('Measurements Reset', () => {
  it('discards unsaved edits and restores source values', () => {
    setup();
    const input = screen.getByLabelText('Chest Circumference') as HTMLInputElement;
    expect(input.value).toBe('112.0');
    fireEvent.change(input, {target: {value: '999'}});
    expect(input.value).toBe('999');
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    expect(input.value).toBe('112.0');
    expect(sessionStorage.getItem('measurement-draft:p1:M:cm')).toBeNull();
  });

  it('clears fields when there are no unsaved edits', async () => {
    setup();
    const input = screen.getByLabelText('Chest Circumference') as HTMLInputElement;
    expect(input.value).toBe('112.0');
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(input.value).toBe(''));
  });

  it('resets unit display to cm', async () => {
    setup();
    fireEvent.click(screen.getByRole('button', {name: 'inch'}));
    expect(screen.getAllByText('inch').length).toBeGreaterThan(1);
    fireEvent.click(screen.getByRole('button', {name: 'Reset'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'cm'}).className).toMatch(/selected/));
    expect(screen.getAllByText('cm').length).toBeGreaterThan(1);
  });
});
