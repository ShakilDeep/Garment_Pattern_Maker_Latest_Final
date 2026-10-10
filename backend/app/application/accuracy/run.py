"""The 1078375 accuracy report: piece size and area, every sew edge, seams, notches, grain and outline validity."""
from collections.abc import Sequence

from app.application.accuracy.model import Check, Report
from app.application.accuracy.piece_checks import edge_checks, size_checks
from app.application.accuracy.seam_checks import seam_checks
from app.domain.pattern.edges import orientation, stitch_ring
from app.domain.pattern.piece import Piece
from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.shirt_derive import named_pieces
from app.infrastructure.piece_validity import check_stitch_outline

NOTCHES = {"shoulder_notch", "crown_notch"}  # docs/drafting/shirt.md Q6: exactly the two PDS notches


def outline_invalid(piece: Piece) -> bool:
    """An outline that crosses or touches itself, encloses no area, or runs clockwise."""
    try:
        check_stitch_outline(piece)
    except ValueError:
        return True
    return orientation(stitch_ring(piece)) != 1


def _geometry_checks(pieces: Sequence[Piece]) -> list[Check]:
    invalid = sum(outline_invalid(piece) for piece in pieces)
    notches = {str(notch.id) for piece in pieces for notch in piece.notches}
    level = sum(p.grainline is None or p.grainline.start.y != p.grainline.end.y for p in pieces)
    return [
        Check("outlines valid", invalid, "0 invalid (closed, simple, counter-clockwise)", invalid == 0,
              "build plan accuracy suite: geometry validity"),
        Check("notches", len(notches), "shoulder_notch and crown_notch only", notches == NOTCHES,
              "docs/drafting/shirt.md Q6"),
        Check("grain along x", level, "0 pieces off the x axis", level == 0, "docs/drafting/shirt.md Q7"),
    ]


def shirt_report(pieces: Sequence[Piece], reference: ReferenceStyle) -> Report:
    named = named_pieces(reference)
    by_name = {piece.name: piece for piece in reference.pieces}
    checks: list[Check] = []
    for piece in pieces:
        checks += size_checks(piece, by_name[piece.name].geometry[reference.base_size])
        checks += edge_checks(piece, named[str(piece.id)])
    checks += seam_checks({str(piece.id): piece for piece in pieces}, named)
    return Report(tuple(checks + _geometry_checks(pieces)))
