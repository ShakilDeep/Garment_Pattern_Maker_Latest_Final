import {useState} from 'react';
import {download} from './api';
import {draftBlock, stylePiece} from './styleApi';
import {LAYERS, type Layer, type StylePiece, type StyleSummary} from './styleTypes';

// The block viewer's own state, kept out of useAppController: the drafted style, its pieces and the layers.
export function useStyleViewer(blockId: string) {
  const [style, setStyle] = useState<StyleSummary | null>(null);
  const [pieces, setPieces] = useState<StylePiece[]>([]);
  const [selected, setSelected] = useState('');
  const [shown, setShown] = useState<Set<Layer>>(new Set(LAYERS));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const draft = async () => {
    setBusy(true);
    setError('');
    try {
      const summary = await draftBlock(blockId);
      const drafted = await Promise.all(summary.piece_ids.map((id) => stylePiece(summary.id, id, summary.base_size)));
      setStyle(summary);
      setPieces(drafted);
      setSelected(drafted[0]?.id ?? '');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  // Base DXF-AAMA + .RUL and the all-sizes DXF in one zip; saved through saveBlobAsFile (api.download).
  const exportAama = async () => {
    if (!style) return;
    setBusy(true);
    setError('');
    try {
      await download(`/styles/${style.id}/export/aama?unit=mm`, `${blockId}_graded_aama.zip`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const toggle = (layer: Layer) => setShown((current) => {
    const next = new Set(current);
    if (next.has(layer)) next.delete(layer); else next.add(layer);
    return next;
  });

  return {style, pieces, selected, select: setSelected, shown, toggle, busy, error, draft, exportAama};
}
