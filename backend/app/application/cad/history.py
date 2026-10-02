"""Undo/redo history (PM-05): the last 100 steps, stored as manifests of content-addressed chunks.

A manifest lists the digests of one state's chunks (`snapshot.py`); `blobs` maps each digest to its text, so
a chunk shared by many steps is stored once. Chunks no manifest needs are dropped whenever a step is dropped.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.application.cad.snapshot import Chunks
from app.application.errors import NotReady

HISTORY_LIMIT = 100
Manifest = tuple[str, ...]


@dataclass(frozen=True)
class History:
    undo_steps: tuple[Manifest, ...] = ()
    redo_steps: tuple[Manifest, ...] = ()
    blobs: Mapping[str, str] = field(default_factory=dict)

    __hash__ = None  # type: ignore[assignment]  # the blob mapping is not hashable

    def __post_init__(self) -> None:
        object.__setattr__(self, "undo_steps", tuple(map(tuple, self.undo_steps)))
        object.__setattr__(self, "redo_steps", tuple(map(tuple, self.redo_steps)))
        object.__setattr__(self, "blobs", MappingProxyType(dict(self.blobs)))

    @classmethod
    def from_states(cls, undo: list[Chunks], redo: list[Chunks]) -> "History":
        """A history holding these states, oldest first: the newest undo steps, then redo steps up to the limit."""
        undo = undo[-HISTORY_LIMIT:]
        redo = redo[len(redo) - (HISTORY_LIMIT - len(undo)) :] if HISTORY_LIMIT > len(undo) else []
        history = cls()
        manifests: tuple[list[Manifest], list[Manifest]] = ([], [])
        for states, stack in ((undo, manifests[0]), (redo, manifests[1])):
            for chunks in states:
                manifest, blobs = history._stored(chunks)
                history = History(blobs=blobs)
                stack.append(manifest)
        return History(tuple(manifests[0]), tuple(manifests[1]), history.blobs)

    def recorded(self, before: Chunks) -> "History":
        """A new edit: `before` becomes the newest undo step and the redo steps are dropped."""
        manifest, blobs = self._stored(before)
        undo = (*self.undo_steps, manifest)
        history = History(undo[-HISTORY_LIMIT:], (), blobs)
        dropped = bool(self.redo_steps) or len(undo) > HISTORY_LIMIT
        return history.collected() if dropped else history

    def undone(self, current: Chunks) -> tuple["History", Chunks]:
        if not self.undo_steps:
            raise NotReady("Nothing to undo")
        manifest, blobs = self._stored(current)
        target = self.undo_steps[-1]
        history = History(self.undo_steps[:-1], (*self.redo_steps, manifest), blobs)
        return history, self._texts(target)

    def redone(self, current: Chunks) -> tuple["History", Chunks]:
        if not self.redo_steps:
            raise NotReady("Nothing to redo")
        manifest, blobs = self._stored(current)
        target = self.redo_steps[-1]
        history = History((*self.undo_steps, manifest), self.redo_steps[:-1], blobs)
        return history, self._texts(target)

    def _stored(self, chunks: Chunks) -> tuple[Manifest, dict[str, str]]:
        blobs = dict(self.blobs)
        manifest = []
        for key, text in chunks:
            blobs.setdefault(key, text)
            manifest.append(key)
        return tuple(manifest), blobs

    def _texts(self, manifest: Manifest) -> Chunks:
        return tuple((key, self.blobs[key]) for key in manifest)

    def collected(self) -> "History":
        """The same steps without the chunks no step needs (an undone state's chunks linger until then)."""
        needed = {key for manifest in (*self.undo_steps, *self.redo_steps) for key in manifest}
        blobs = {key: text for key, text in self.blobs.items() if key in needed}
        return History(self.undo_steps, self.redo_steps, blobs)
