import {expect, it} from 'vitest';
import {frame, ringPath, segmentCommand, sewPath} from './stylePath';
import {yoke} from './blockViewerFixture';

it('draws the sew line from typed segments, cubic handles as offsets from their own end point', () => {
  expect(sewPath(yoke)).toBe('M 12 0 C 12.1 6 12 7.4 17 9 L 12.5 26 L 0 0 L 12 0 Z');
});

it('draws an arc from its bulge: a half circle has radius half the chord', () => {
  const arc = {id: 'a:b', type: 'arc' as const, start: 'a', end: 'b', bulge: 1};
  expect(segmentCommand(arc, {a: [0, 0], b: [10, 0]})).toBe('A 5 5 0 0 1 10 0');
});

it('draws the cut ring and frames the piece with the y axis flipped', () => {
  expect(ringPath([[0, 0], [1, 0], [1, 1]])).toBe('M 0 0 L 1 0 L 1 1 Z');
  expect(frame(yoke)).toEqual({x: -3, y: -29, width: 23, height: 32});
});
