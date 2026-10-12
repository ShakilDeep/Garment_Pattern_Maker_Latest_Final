"""Spec §7 piece gap limits at the base size: each drafted 1078375 sew outline against the PDS sew outline.

The gap is the Hausdorff distance (cm) after the best quarter-turn/mirror fit (``infrastructure/outline_fit``).
The sleeve is checked on its cap: both sleeves are laid with the underarm line (UA_back to UA_front) on the
x axis and the crown above it, and only the part above that line is compared.
"""
from collections.abc import Iterable, Sequence
from math import atan2, degrees

from shapely import affinity
from shapely.geometry import Point, Polygon, box

from app.application.accuracy.model import Check, Source
from app.domain.pattern.edges import stitch_ring
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.reference import ReferenceStyle
from app.infrastructure.outline_fit import fit
from app.infrastructure.pds.shirt_named import NamedPiece, named_pieces

GAP_CM = {"FRT": 0.5, "back": 1.0, "back YK": 0.2, "CLR": 0.6, "BND TOP": 0.6, "BND IN": 0.6}
CAP_CM = 0.2
SLEEVE, CAP_POINTS = "Sleeve", ("UA_back", "UA_front", "cap_crown")
SPEC = Source("pds", "spec §7: shirt L piece gap limits against 1078375")

Corners = tuple[tuple[float, float], ...]


def _cap(outline: Polygon, corners: Corners) -> Polygon:
    """The part of a sleeve above its underarm line, in a frame where that line is the x axis."""
    (bx, by), (fx, fy), crown = corners
    angle = -degrees(atan2(fy - by, fx - bx))
    shapes = [affinity.rotate(affinity.translate(shape, -bx, -by), angle, origin=(0, 0))
              for shape in (outline, Point(crown))]
    laid = affinity.scale(shapes[0], 1, -1, origin=(0, 0)) if shapes[1].y < 0 else shapes[0]
    x0, _, x1, y1 = laid.bounds
    return laid.intersection(box(x0, 0, x1, y1))


def _drafted(piece: Piece) -> Polygon:
    return Polygon([(p.x, p.y) for p in stitch_ring(piece)])


def _pds(named: NamedPiece) -> Polygon:
    return Polygon(named.ring)  # PDS ring points are (x, y) tuples


def _check(piece: Piece, gap: float, limit: float, what: str) -> Check:
    return Check(f"{what} gap", gap, f"{limit} cm Hausdorff to the PDS sew line", gap <= limit, SPEC,
                 piece=piece.name)


def _cap_check(piece: Piece, named: NamedPiece) -> Check:
    drafted = tuple((piece.point(PointId(n)).position.x, piece.point(PointId(n)).position.y) for n in CAP_POINTS)
    pds = tuple(named.at(n) for n in CAP_POINTS)
    gap = fit(_cap(_drafted(piece), drafted), _cap(_pds(named), pds)).hausdorff_cm
    return _check(piece, gap, CAP_CM, f"{SLEEVE} cap")


def gap_checks(pieces: Sequence[Piece], reference: ReferenceStyle) -> list[Check]:
    named = named_pieces(reference)
    by_name = {piece.name: piece for piece in pieces}
    checks = [_check(piece, fit(_drafted(piece), _pds(named[str(piece.id)])).hausdorff_cm, GAP_CM[name], name)
              for name, piece in _present(by_name, GAP_CM)]
    if SLEEVE in by_name:
        checks.append(_cap_check(by_name[SLEEVE], named[str(by_name[SLEEVE].id)]))
    return checks


def _present(by_name: dict[str, Piece], names: Iterable[str]) -> list[tuple[str, Piece]]:
    return [(name, by_name[name]) for name in names if name in by_name]
