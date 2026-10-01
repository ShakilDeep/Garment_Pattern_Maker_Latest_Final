"""Chain of Responsibility: a JSON geometry import must target a live project and carry valid nested data."""
from app.application.errors import ImportInvalid
from app.domain.catalog import SIZES
from app.infrastructure.import_fields import check_fields
from app.infrastructure.import_marker import check_marker, is_polygon
from app.infrastructure.import_values import check_numbers
from app.infrastructure.validation import validate

SCHEMA_VERSION = 1


def require_project(repo, pid):
    return repo.get(pid)


def _versions(body):
    return [body.pattern, *body.grades]


def _invalid_geometry(message):
    return ImportInvalid("IMPORT_GEOMETRY_INVALID", message)


def check_schema(body):
    if any(version.get("schema_version") != SCHEMA_VERSION for version in _versions(body)):
        raise ImportInvalid("IMPORT_SCHEMA_UNSUPPORTED", "Unsupported geometry schema version")


def check_sizes(body):
    grade_sizes = [grade.get("size") for grade in body.grades]
    if any(size not in SIZES for size in [body.pattern.get("size"), *grade_sizes]):
        raise ImportInvalid("IMPORT_SIZES_INVALID", "Imported pattern sizes must be between S and 3XL")
    if len(set(grade_sizes)) != len(grade_sizes):
        raise ImportInvalid("IMPORT_SIZES_INVALID", "Imported grades need distinct sizes")


def _piece_ok(piece):
    if not isinstance(piece, dict) or not is_polygon(piece.get("points")):
        return False
    cut_points, quantity = piece.get("cut_points"), piece.get("quantity")
    if cut_points is not None and not is_polygon(cut_points):
        return False
    return type(quantity) is int and quantity >= 1


def _check_version_geometry(version):
    pieces = version.get("pieces")
    if not isinstance(pieces, list) or not pieces or not all(_piece_ok(piece) for piece in pieces):
        raise _invalid_geometry("Imported patterns must contain polygon piece geometry")
    try:
        issues = validate(version)
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid_geometry("Imported geometry has an invalid pattern structure") from exc
    if any(issue["severity"] == "ERROR" for issue in issues):
        raise _invalid_geometry("Imported geometry failed deterministic validation")


def check_geometry(body):
    for version in _versions(body):
        _check_version_geometry(version)


CHECKS = (check_numbers, check_schema, check_sizes, check_geometry, check_fields, check_marker)


def assert_importable(body):
    for check in CHECKS:
        check(body)
