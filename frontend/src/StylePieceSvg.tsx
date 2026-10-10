import {frame, ringPath, sewPath} from './stylePath';
import type {Layer, StylePiece} from './styleTypes';

type Props = {piece: StylePiece; shown: Set<Layer>; selected: boolean; select: (id: string) => void};

const cutCount = ({single, mirrored_pairs, on_fold}: StylePiece['cut']) =>
  single + 2 * mirrored_pairs + on_fold;

// One V6 piece drawn from the backend's geometry: cut and sew lines, notch slits, grain and its label.
export default function StylePieceSvg({piece, shown, selected, select}: Props) {
  const box = frame(piece);
  const fold = piece.cut.on_fold > 0 ? ', on fold' : '';
  return (
    <figure className={selected ? 'style-piece style-piece-selected' : 'style-piece'}>
      <button type="button" className="style-piece-select" aria-pressed={selected}
        aria-label={`Select ${piece.name}`} onClick={() => select(piece.id)}>
        <svg viewBox={`${box.x} ${box.y} ${box.width} ${box.height}`} role="img"
          aria-label={`${piece.name} pattern piece`}>
          <g transform="scale(1,-1)">
            {shown.has('cut') && piece.cut_outline &&
              <path data-layer="cut" d={ringPath(piece.cut_outline)} className="cut-line" />}
            {shown.has('sew') && <path data-layer="sew" d={sewPath(piece)} className="sew-line" />}
            {shown.has('notches') && piece.notch_marks.map((n) =>
              <line key={n.id} data-layer="notches" x1={n.at[0]} y1={n.at[1]} x2={n.tip[0]} y2={n.tip[1]}
                className="notch-mark" />)}
            {shown.has('grain') && piece.grainline &&
              <line data-layer="grain" x1={piece.grainline[0][0]} y1={piece.grainline[0][1]}
                x2={piece.grainline[1][0]} y2={piece.grainline[1][1]} className="grain-line" />}
          </g>
        </svg>
      </button>
      {shown.has('labels') &&
        <figcaption data-layer="labels">{piece.name} · cut {cutCount(piece.cut)}{fold}</figcaption>}
    </figure>
  );
}
