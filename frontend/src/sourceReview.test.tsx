import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, render, screen} from '@testing-library/react';
import SourceReview from './SourceReview';
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it('shows persisted parse status and recoverable extraction issues', async () => {
  const values=Object.fromEntries(Array.from({length:12},(_,index)=>[`size_${index}`,{issue:index===0?'Missing cuff length':null}]));
  render(<SourceReview project={{id: 'p1', documents: [{id:'d1', filename:'measurements.xlsx', bytes:10, sha256:'hash'}], measurements:[{values}, ...Array.from({length:11},()=>({values:{}}))], techpack: null, audit: []} as never} />);
  expect(await screen.findByText(/Parse status:/)).toBeTruthy();
  expect(screen.getByText(/12 measurement rows/)).toBeTruthy();
  expect(screen.getAllByText(/Missing cuff length/).length).toBe(1);
});
