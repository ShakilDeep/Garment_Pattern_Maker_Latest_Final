"""Command history Memento (PM-05): JSON-ready data, integrity-checked when loaded (digests, canonical text)."""

import json

from app.application.cad.history import HISTORY_LIMIT, History, Manifest
from app.application.cad.snapshot import digest
from app.domain.pattern.canonical import canonical_dumps

HISTORY_SCHEMA_VERSION = 1


def history_to_data(history: History) -> dict:
    return {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "undo": [list(manifest) for manifest in history.undo_steps],
        "redo": [list(manifest) for manifest in history.redo_steps],
        "blobs": dict(history.collected().blobs),
    }


def _steps(value: object) -> tuple[Manifest, ...]:
    if not isinstance(value, list) or not all(
        isinstance(step, list) and all(isinstance(key, str) for key in step) for step in value
    ):
        raise ValueError("Undo and redo steps must be lists of digest lists")
    if not all(value):
        raise ValueError("A command history step must list at least one chunk")
    return tuple(tuple(step) for step in value)


def _blobs(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(text, str) for text in value.values()):
        raise ValueError("Stored chunks must map digests to text")
    for key, text in value.items():
        if digest(text) != key:
            raise ValueError(f"Stored chunk {str(key)[:12]} does not match its digest")
        if not _canonical(text):
            raise ValueError(f"Stored chunk {str(key)[:12]} is not canonical JSON")
    return value


def _canonical(text: str) -> bool:
    """Chunks are written as canonical JSON; any other text would make restored states non-deterministic."""
    try:
        return canonical_dumps(json.loads(text)) == text
    except ValueError:  # not JSON, or NaN/infinity: either way it is not a canonical chunk
        return False


def history_from_data(data: object) -> History:
    """`None` (a project with no edits yet) is an empty history; anything malformed raises ValueError."""
    if data is None:
        return History()
    if not isinstance(data, dict):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError("The command history must be an object")  # noqa: TRY004
    try:
        version = data["schema_version"]
        if type(version) is not int or version != HISTORY_SCHEMA_VERSION:
            raise ValueError(f"Unsupported command history schema version {version!r}")
        undo, redo, blobs = _steps(data["undo"]), _steps(data["redo"]), _blobs(data["blobs"])
    except KeyError as exc:
        raise ValueError(f"Invalid command history: missing field {exc.args[0]!r}") from exc
    if len(undo) + len(redo) > HISTORY_LIMIT:
        raise ValueError(f"The command history has more than {HISTORY_LIMIT} undo and redo steps")
    needed = {key for step in (*undo, *redo) for key in step}
    if needed - blobs.keys():
        raise ValueError("The command history is missing a stored chunk")
    if blobs.keys() - needed:
        raise ValueError("The command history stores a chunk no step uses")
    return History(undo, redo, blobs)
