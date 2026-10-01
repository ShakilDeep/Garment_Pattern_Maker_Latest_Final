"""Import validator: scalar fields that persistence projects into SQL columns have the expected types."""
from app.application.errors import ImportInvalid
from app.infrastructure.import_marker import number

VERSION_TEXT = ("id", "profile", "input_hash")
PIECE_TEXT = ("id", "name")
ISSUE_TEXT = ("severity", "code", "message")
MARKER_TEXT = ("strategy",)
MARKER_NUMBERS = ("utilization", "waste")


def _text(record, keys):
    return isinstance(record, dict) and all(isinstance(record.get(key), str) for key in keys)


def _version_ok(version):
    created_at, pieces, validation = version.get("created_at"), version.get("pieces"), version.get("validation")
    return (_text(version, VERSION_TEXT) and (created_at is None or isinstance(created_at, str))
            and isinstance(pieces, list) and all(_text(piece, PIECE_TEXT) for piece in pieces)
            and isinstance(validation, list) and all(_text(issue, ISSUE_TEXT) for issue in validation))


def check_fields(body):
    versions = [body.pattern, *body.grades]
    if not all(_version_ok(version) for version in versions):
        raise ImportInvalid("IMPORT_GEOMETRY_INVALID", "Imported patterns are missing typed identity or issue fields")
    if len({version["id"] for version in versions}) != len(versions):
        raise ImportInvalid("IMPORT_GEOMETRY_INVALID", "Imported pattern versions need distinct ids")
    marker = body.marker
    if marker is not None and not (_text(marker, MARKER_TEXT) and all(number(marker.get(k)) for k in MARKER_NUMBERS)):
        raise ImportInvalid("IMPORT_MARKER_INVALID", "Imported marker is missing its strategy or utilization figures")
