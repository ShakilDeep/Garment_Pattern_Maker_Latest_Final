"""Style Memento (PM-04): canonical JSON text. Per-size pieces stay undecoded until viewed (`SizePieces`).

The text equals `canonical_dumps` of the parsed document, so it is deterministic and idempotent. A size that
was never viewed serializes exactly as it was loaded; a viewed size serializes as its canonical Memento.
Seam allowances are written only when a piece has one, so documents without them keep their exact text.
"""

import json

from app.domain.pattern.canonical import canonical_dumps
from app.domain.pattern.ids import StyleId
from app.domain.pattern.seam_codec import allowances_from_data, allowances_to_data
from app.domain.pattern.size_pieces import SizePieces
from app.domain.pattern.style import Style

STYLE_SCHEMA_VERSION = 1


def style_to_json(style: Style) -> str:
    geometry = ",".join(
        f'{{"pieces":{stored.text()},"size":{canonical_dumps(size)}}}' for size, stored in style.geometry.items()
    )
    allowances = f'"allowances":{canonical_dumps(allowances_to_data(style.allowances))},' if style.allowances else ""
    return (
        f'{{{allowances}"base_size":{canonical_dumps(style.base_size)},"geometry":[{geometry}],'
        f'"id":{canonical_dumps(str(style.id))},"name":{canonical_dumps(style.name)},'
        f'"schema_version":{STYLE_SCHEMA_VERSION},"sizes":{canonical_dumps(list(style.sizes))}}}'
    )


def _reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not a number")


def _geometry(entries: object) -> dict[str, SizePieces]:
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("Style geometry must be a list of {size, pieces} objects")
    found: dict[str, SizePieces] = {}
    for entry in entries:
        size = entry["size"]
        if size in found:
            raise ValueError(f"Size {size} has geometry more than once")
        found[size] = SizePieces.from_entries(entry["pieces"])
    return found


def style_from_json(text: str | bytes) -> Style:
    """Rebuild a style; malformed documents raise ValueError naming the problem (never KeyError/TypeError)."""
    try:
        document = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, TypeError) as exc:
        raise ValueError("The style document is not valid JSON") from exc
    if not isinstance(document, dict):
        # ValueError, not TypeError: the API maps ValueError to 400.
        raise ValueError("A style document must be an object")  # noqa: TRY004
    try:
        version = document["schema_version"]
        if type(version) is not int or version != STYLE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported style schema version {version!r}")
        return Style(
            id=StyleId(document["id"]),
            name=document["name"],
            sizes=document["sizes"],
            base_size=document["base_size"],
            geometry=_geometry(document["geometry"]),
            allowances=allowances_from_data(document.get("allowances", {})),
        )
    except KeyError as exc:
        raise ValueError(f"Invalid style data: missing field {exc.args[0]!r}") from exc
    except (TypeError, AttributeError) as exc:
        raise ValueError(f"Invalid style data: {exc}") from exc
