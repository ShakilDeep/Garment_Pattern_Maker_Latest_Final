import './blockViewer.css';
import LayerToggles from './LayerToggles';
import MeasureTool from './MeasureTool';
import StylePieceSvg from './StylePieceSvg';
import WalkReadout from './WalkReadout';
import {useStyleViewer} from './useStyleViewer';

const BLOCK = 'shirt_1078375';

// T130 block viewer: the 1078375 shirt drafted from its named-point block, with layers, measure and walk.
export default function BlockViewer() {
  const v = useStyleViewer(BLOCK);
  const piece = v.pieces.find((p) => p.id === v.selected);
  return (
    <section className="block-viewer card" aria-label="Block viewer (1078375)">
      <header className="block-viewer-header">
        <div><h2>Block viewer (1078375)</h2>
          <p>Men's short-sleeve shirt drafted from the client PDS at size L.</p></div>
        <button type="button" className="primary" disabled={v.busy} onClick={() => void v.draft()}>
          {v.style ? 'Redraft 1078375 block' : 'Draft 1078375 block'}</button>
      </header>
      {v.error && <p role="alert">{v.error}</p>}
      {v.style && <>
        <LayerToggles shown={v.shown} toggle={v.toggle} />
        <div className="style-pieces">
          {v.pieces.map((p) =>
            <StylePieceSvg key={p.id} piece={p} shown={v.shown} selected={p.id === v.selected} select={v.select} />)}
        </div>
        <div className="block-viewer-tools">
          {piece && <MeasureTool key={piece.id} styleId={v.style.id} size={v.style.base_size} piece={piece} />}
          <WalkReadout styleId={v.style.id} size={v.style.base_size} />
        </div>
      </>}
    </section>
  );
}
