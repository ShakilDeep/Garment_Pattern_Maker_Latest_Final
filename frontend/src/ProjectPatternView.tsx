import {useEffect} from 'react';
import './blockViewer.css';
import LayerToggles from './LayerToggles';
import MeasureTool from './MeasureTool';
import StylePieceSvg from './StylePieceSvg';
import WalkReadout, {ARMHOLE, CAP} from './WalkReadout';
import {styleFromProject} from './styleApi';
import type {StyleSummary} from './styleTypes';
import {shownSize, useStyleViewer} from './useStyleViewer';

// One CAD style per project version: POST /styles stores a new style each call, so a remount must not repeat it.
const styles = new Map<string, Promise<StyleSummary>>();
export const resetProjectStyles = () => styles.clear();

function projectStyle(projectId: string, version: string): Promise<StyleSummary> {
  const key = `${projectId}:${version}`;
  const known = styles.get(key);
  if (known) return known;
  const made = styleFromProject(projectId);
  styles.set(key, made);
  made.catch(() => styles.delete(key));  // a failure is not remembered; the next view asks again
  return made;
}

const WALKED = [...CAP, ...ARMHOLE].map((part) => part.piece_id);  // the pieces the sleeve-cap walk reads

type Props = {
  projectId: string; version: string; size: string; busy: boolean;
  select: (name: string) => void;  // the chosen piece, by name, for the panels that address V5 pieces
  download: () => void;  // the project's graded DXF-AAMA + .RUL export (accuracy-gated)
};

// The project's own pattern drawn from its V6 style: piece cards, layers, measure and, for the 1078375 block, the walk.
export default function ProjectPatternView({projectId, version, size, busy, select, download}: Props) {
  const v = useStyleViewer({create: () => projectStyle(projectId, version), size});
  useEffect(() => {
    let ignore = false;
    void v.draft(() => !ignore);
    return () => { ignore = true; };
  }, [projectId, version, size]);  // v.draft is a new function each render; these are what it reads
  const piece = v.pieces.find((p) => p.id === v.selected);
  const at = v.style ? shownSize(v.style, size) : size;
  const walkable = v.style ? WALKED.every((id) => v.style!.piece_ids.includes(id)) : false;
  const choose = (id: string) => {
    v.select(id);
    const name = v.pieces.find((p) => p.id === id)?.name;
    if (name) select(name);
  };
  return (
    <section className="block-viewer project-pattern-view" aria-label="Project pattern pieces">
      {v.error && <p role="alert">{v.error}</p>}
      {v.style && <>
        <div className="block-viewer-actions">
          <LayerToggles shown={v.shown} toggle={v.toggle} />
          <button type="button" disabled={busy} onClick={download}>Download graded DXF-AAMA + RUL</button>
        </div>
        {at !== size && <p className="notice">Size {size} is not graded yet; showing base size {at}.</p>}
        <div className="style-pieces">
          {v.pieces.map((p) =>
            <StylePieceSvg key={p.id} piece={p} shown={v.shown} selected={p.id === v.selected} select={choose} />)}
        </div>
        <div className="block-viewer-tools">
          {piece && <MeasureTool key={piece.id} styleId={v.style.id} size={at} piece={piece} />}
          {walkable && <WalkReadout styleId={v.style.id} size={at} />}
        </div>
      </>}
    </section>
  );
}
