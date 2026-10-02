"""Style snapshots for the history: a header chunk, then one chunk per piece per size (its canonical Memento).

A step that edits one piece therefore stores one new chunk (plus the header), however large the style is, and
the per-piece digests come from the SizePieces cache. Restoring reuses the current style's SizePieces for
every size whose pieces are unchanged.
"""

import json

from app.application.cad.snapshot import Chunks, chunk
from app.domain.pattern.canonical import canonical_dumps
from app.domain.pattern.ids import StyleId
from app.domain.pattern.piece_texts import PieceTexts
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style


class StyleSnapshotter:
    def chunks(self, state: Style) -> Chunks:
        layout = [[size, len(stored.piece_ids)] for size, stored in state.geometry.items()]
        header = {
            "id": str(state.id),
            "name": state.name,
            "sizes": list(state.sizes),
            "base_size": state.base_size,
            "layout": layout,
        }
        texts = (stored.piece_texts() for stored in state.geometry.values())
        return (chunk(canonical_dumps(header)), *(pair for t in texts for pair in zip(t.digests, t.texts)))

    def restore(self, chunks: Chunks, current: Style) -> Style:
        header = json.loads(chunks[0][1])
        geometry: dict[str, SizePieces] = {}
        offset = 1
        for size, count in header["layout"]:
            part = chunks[offset : offset + count]
            offset += count
            digests = tuple(key for key, _ in part)
            reusable = current.geometry.get(size)
            if reusable is not None and reusable.piece_texts().digests == digests:
                geometry[size] = reusable
            else:
                geometry[size] = SizePieces.from_piece_texts(PieceTexts(tuple(t for _, t in part), digests))
        return Style(StyleId(header["id"]), header["name"], tuple(header["sizes"]), header["base_size"], geometry)
