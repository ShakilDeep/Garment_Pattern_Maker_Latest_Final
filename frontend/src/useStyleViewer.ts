import {useState} from 'react';
import {stylePiece} from './styleApi';
import {LAYERS, type Layer, type StylePiece, type StyleSummary} from './styleTypes';

type Source = {
  create: () => Promise<StyleSummary>;  // where the style comes from (a project's pattern)
  size?: string;  // the size to show when the style has it graded; the base size otherwise
};

export const shownSize = (style: StyleSummary, size?: string) =>
  size && (style.graded_sizes ?? style.sizes).includes(size) ? size : style.base_size;

// A V6 style viewer's own state, kept out of useAppController: the style, its pieces and the layers.
export function useStyleViewer({create, size}: Source) {
  const [style, setStyle] = useState<StyleSummary | null>(null);
  const [pieces, setPieces] = useState<StylePiece[]>([]);
  const [selected, setSelected] = useState('');
  const [shown, setShown] = useState<Set<Layer>>(new Set(LAYERS));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  // `live` is false once the caller no longer wants this result (an effect cleaned up), so a late reply is dropped.
  const draft = async (live: () => boolean = () => true) => {
    setBusy(true);
    setError('');
    try {
      const summary = await create();
      const at = shownSize(summary, size);
      const drafted = await Promise.all(summary.piece_ids.map((id) => stylePiece(summary.id, id, at)));
      if (!live()) return;
      setStyle(summary);
      setPieces(drafted);
      setSelected((current) => drafted.some((p) => p.id === current) ? current : drafted[0]?.id ?? '');
    } catch (e) {
      if (live()) setError((e as Error).message);
    } finally {
      if (live()) setBusy(false);
    }
  };
  const toggle = (layer: Layer) => setShown((current) => {
    const next = new Set(current);
    if (next.has(layer)) next.delete(layer); else next.add(layer);
    return next;
  });

  return {style, pieces, selected, select: setSelected, shown, toggle, busy, error, draft};
}
