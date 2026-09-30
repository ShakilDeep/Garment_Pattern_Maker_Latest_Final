/** Selected-piece inspector for Pattern Studio (demo metadata only). */

import type {Piece} from './types';

export default function PieceInspector({piece}: {piece: Piece | null}) {
  if (!piece) {
    return <p className="notice" role="status">Select a piece on the canvas to inspect dimensions.</p>;
  }
  return (
    <section className="piece-inspector" aria-label="Selected piece inspector">
      <h3>{piece.name}</h3>
      <dl>
        <div><dt>Width</dt><dd>{piece.width.toFixed(2)} cm</dd></div>
        <div><dt>Height</dt><dd>{piece.height.toFixed(2)} cm</dd></div>
        <div><dt>Area</dt><dd>{piece.area.toFixed(2)} cm²</dd></div>
        <div><dt>Perimeter</dt><dd>{piece.perimeter.toFixed(2)} cm</dd></div>
        <div><dt>Cut quantity</dt><dd>{piece.quantity}</dd></div>
        <div><dt>Cut on fold</dt><dd>{piece.cut_on_fold ? 'Yes' : 'No'}</dd></div>
      </dl>
      <p><small>Demo dimensions from generated geometry. Production calibration remains external.</small></p>
    </section>
  );
}
