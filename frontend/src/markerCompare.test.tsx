import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, render, screen, waitFor} from '@testing-library/react';
import Workflow from './Workflow';
import {api} from './api';
import type {Pattern, Project} from './types';

vi.mock('./api', () => ({api: vi.fn()}));
afterEach(() => {cleanup(); vi.resetAllMocks()});

it('shows compare length delta only from the stored prior marker', async () => {
  vi.mocked(api).mockResolvedValue({
    current_width: 200, previous_width: 150, length_delta: -12.5, current_length: 80, previous_length: 92.5,
  });
  const piece = {name: 'Front', points: [[0, 0], [4, 0], [4, 4], [0, 4]] as [number, number][], x: 1, y: 1, width: 4, height: 4};
  const marker = {placements: [piece], width: 20, length: 80, utilization: 50, waste: 50, quantity: 1, size: 'L', strategy: 'first-fit', gap: 0.5};
  const pattern = {id: 'L', size: 'L', stale: false, validation: [], pieces: []} as unknown as Pattern;
  const project = {id: 'test', pattern, grades: [], marker, previous_marker: {...marker, utilization: 40, length: 92.5}} as unknown as Project;
  render(<Workflow page="Marker Nesting" project={project} requirements={null} resolve={vi.fn()} generate={vi.fn()} grade={vi.fn()} nest={vi.fn()} download={vi.fn()} busy={false} size="L" setSize={vi.fn()} open={vi.fn()}/>);
  await waitFor(() => expect(screen.getByText(/length delta -12.5 cm/i)).toBeTruthy());
  expect(api).toHaveBeenCalledWith('/projects/test/markers/compare');
});
