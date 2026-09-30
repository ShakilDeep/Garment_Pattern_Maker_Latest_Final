import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import {afterEach, describe, expect, it, vi} from 'vitest';
import SourceDropzone from './SourceDropzone';

afterEach(() => cleanup());

describe('SourceDropzone browse control', () => {
  it('uses Facade pattern: Browse label contains an on-control file input overlay', () => {
    const upload = vi.fn();
    render(<SourceDropzone upload={upload} busy={false} documents={[]} replaceSource={false} setReplaceSource={vi.fn()} />);
    const input = screen.getByLabelText('Browse files') as HTMLInputElement;
    expect(input.type).toBe('file');
    expect(input.className).toMatch(/browse-files-input/);
    // Must NOT be parked off-screen — browsers skip picker for clipped/off-screen inputs.
    expect(input.className).not.toMatch(/sr-only/);
    const label = input.closest('label');
    expect(label).not.toBeNull();
    expect(label?.className).toMatch(/browse-files/);
    expect(label?.textContent).toContain('Browse files');
  });

  it('uploads the chosen file through the facade input', () => {
    const upload = vi.fn();
    render(<SourceDropzone upload={upload} busy={false} documents={[]} replaceSource={false} setReplaceSource={vi.fn()} />);
    const file = new File(['xlsx'], 'Book.xlsx', {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    fireEvent.change(screen.getByLabelText('Browse files'), {target: {files: [file]}});
    expect(upload).toHaveBeenCalledWith(file, false);
  });

  it('disables the facade input while busy', () => {
    render(<SourceDropzone upload={vi.fn()} busy documents={[]} replaceSource={false} setReplaceSource={vi.fn()} />);
    expect((screen.getByLabelText('Browse files') as HTMLInputElement).disabled).toBe(true);
  });
});
