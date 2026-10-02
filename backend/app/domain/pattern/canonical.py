"""Canonical JSON text: sorted keys, no spaces and no NaN, so equal data always gives equal text."""

import json


def canonical_dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
