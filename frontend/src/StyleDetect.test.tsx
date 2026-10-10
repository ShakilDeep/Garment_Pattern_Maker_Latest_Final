import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import StyleDetect from './StyleDetect';
import {api} from './api';
import type {Project} from './types';
import type {OptionSpec, StyleDetection} from './styleDetectTypes';

vi.mock('./api', () => ({api: vi.fn()}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

const spec = (id: string, label: string, families: string[], ...choices: string[]): OptionSpec =>
  ({id, label, families, choices: [...choices, 'unknown'], note: ''});
const specs = [spec('garment', 'Garment type', ['shirt', 'pant'], 'shirt', 'pant'),
  spec('fit', 'Fit', ['shirt', 'pant'], 'regular', 'relaxed'), spec('sleeve', 'Sleeve', ['shirt'], 'short', 'long'),
  spec('leg', 'Leg', ['pant'], 'straight', 'wide')];
const guess = (id: string, value: string, confidence = 0.92) => ({id, value, confidence});
const detection: StyleDetection = {page: 1, at: 'now', source_sha256: 'x', proposal: {
  garment: guess('garment', 'pant', 1), fit: guess('fit', 'unknown', 0), options: [guess('leg', 'wide')],
  provider: 'gemini', model: 'm', prompt_version: 'v2'}};
const project = {id: 'p1'} as Project;

function setup(confirm = vi.fn().mockResolvedValue(true), current = project) {
  render(<StyleDetect project={current} busy={false} confirm={confirm}/>);
  return confirm;
}

it('starts with every option unset and cannot confirm without a garment', async () => {
  vi.mocked(api).mockResolvedValue(specs);
  setup();
  expect(((await screen.findByLabelText('Garment type')) as HTMLSelectElement).value).toBe('unknown');
  expect(screen.getByLabelText('Sleeve')).toBeTruthy();
  expect(screen.getByRole('button', {name: 'Confirm style'})).toHaveProperty('disabled', true);
  expect(api).toHaveBeenCalledWith('/style/options');
});

it('fills the proposal with confidence and sends the edited choice on confirm', async () => {
  vi.mocked(api).mockResolvedValueOnce(specs).mockResolvedValueOnce(detection);
  const confirm = setup();
  const input = await screen.findByLabelText('Detect style from image');
  fireEvent.change(input, {target: {files: [new File(['png'], 'flat.png', {type: 'image/png'})]}});
  expect(await screen.findByText('AI 92%')).toBeTruthy();
  const [path, method, body] = vi.mocked(api).mock.calls[1];
  expect([path, method, (body as FormData).get('file')]).toEqual(['/projects/p1/style/detect', 'POST', expect.any(File)]);
  expect(screen.queryByLabelText('Sleeve')).toBeNull();
  fireEvent.change(screen.getByLabelText('Fit'), {target: {value: 'relaxed'}});
  expect(screen.getByText('Your choice')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', {name: 'Confirm style'}));
  await waitFor(() => expect(confirm).toHaveBeenCalledWith(
    {garment: 'pant', fit: 'relaxed', options: {leg: 'wide'}}));
});

it('keeps manual choice working when detection fails', async () => {
  vi.mocked(api).mockResolvedValueOnce(specs).mockRejectedValueOnce(new Error('The assistant is unavailable.'));
  setup();
  fireEvent.change(await screen.findByLabelText('Detect style from image'),
    {target: {files: [new File(['png'], 'flat.png', {type: 'image/png'})]}});
  expect((await screen.findByRole('alert')).textContent).toContain('unavailable');
  fireEvent.change(screen.getByLabelText('Garment type'), {target: {value: 'shirt'}});
  expect(screen.getByRole('button', {name: 'Confirm style'})).toHaveProperty('disabled', false);
});

it('restores the confirmed style and uses the transparent Browse input', async () => {
  vi.mocked(api).mockResolvedValue(specs);
  setup(undefined, {...project, style_choices: {garment: 'shirt', fit: 'regular', options: {sleeve: 'long'},
    source: 'user', at: 'now'}} as Project);
  expect(((await screen.findByLabelText('Sleeve')) as HTMLSelectElement).value).toBe('long');
  const input = screen.getByLabelText('Detect style from image');
  expect(input.className).toBe('browse-files-input');
  expect(input.closest('label')?.className).toContain('browse-files');
});
