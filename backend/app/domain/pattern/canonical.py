"""Canonical JSON text: sorted keys, no spaces and no NaN, so equal data always gives equal text."""

import json
from hashlib import sha256


def canonical_dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def text_digest(text: str) -> str:
    """SHA-256 hex digest of the text's UTF-8 bytes."""
    return sha256(text.encode("utf-8")).hexdigest()
