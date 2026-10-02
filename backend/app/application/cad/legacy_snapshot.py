"""V5 snapshot chunks for the history, split so that a V5 edit stores only what it changed.

Chunks: a small header, then measurements, resolutions, the pattern's own fields, each bulky pattern field
(`inputs`, `validation`) on its own, and one chunk per piece. A V5 command changes the pattern's id, parent and
command fields and some pieces, so measurements, resolutions and drafting inputs are stored once.
"""

import json

from app.application.cad.snapshot import Chunks, chunk
from app.domain.pattern.canonical import canonical_dumps

Snapshot = dict
BULKY_FIELDS = ("inputs", "validation")
SEPARATE_FIELDS = ("pieces", *BULKY_FIELDS)


class LegacySnapshotter:
    def chunks(self, state: Snapshot) -> Chunks:
        pattern = state["pattern"]
        fields = pattern or {}
        bulky = [name for name in BULKY_FIELDS if name in fields]
        header = {"has_pattern": pattern is not None, "has_pieces": "pieces" in fields, "bulky": bulky}
        own = {key: value for key, value in fields.items() if key not in SEPARATE_FIELDS}
        texts = [header, state["measurements"], state["resolutions"], own, *(fields[name] for name in bulky)]
        return (*(chunk(canonical_dumps(text)) for text in texts),
                *(chunk(canonical_dumps(piece)) for piece in fields.get("pieces", [])))

    def restore(self, chunks: Chunks, current: Snapshot) -> Snapshot:
        values = [json.loads(text) for _, text in chunks]
        header, measurements, resolutions, pattern = values[:4]
        bulky = header["bulky"]
        pattern.update(zip(bulky, values[4 : 4 + len(bulky)]))
        if header["has_pieces"]:
            pattern["pieces"] = values[4 + len(bulky) :]
        return {
            "measurements": measurements,
            "resolutions": resolutions,
            "pattern": pattern if header["has_pattern"] else None,
        }
