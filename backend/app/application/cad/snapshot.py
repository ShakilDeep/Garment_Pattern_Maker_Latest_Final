"""Snapshots for the command history: a state is split into text chunks stored by their SHA-256 digest.

Chunking lets 100 steps of a large style share every piece a step did not change. The digest of the chunk
digests is the state's geometry key: two states with equal keys serialize identically.
"""

from typing import Protocol

from app.domain.pattern.canonical import text_digest as digest

Chunk = tuple[str, str]  # (digest, text): snapshotters pass digests they already cached
Chunks = tuple[Chunk, ...]


def chunk(text: str) -> Chunk:
    return digest(text), text


def state_key(chunks: Chunks) -> str:
    return digest("\n".join(key for key, _ in chunks))


class Snapshotter[State](Protocol):
    def chunks(self, state: State) -> Chunks:
        """The state as canonical (digest, text) chunks; the first chunk says how to reassemble the rest."""
        ...

    def restore(self, chunks: Chunks, current: State) -> State:
        """Rebuild a state from its chunks; `current` lets unchanged parts be reused."""
        ...
