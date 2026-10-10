"""Adapter: a V6 piece -> InterchangePiece for DXF-AAMA export (T131).

The cut line is the validated seam-allowance outline (``check_cut_geometry``) and the sew line the stitch
outline, curves sampled. A piece cut on the fold carries its drawn half and its fold edge as the mirror line,
as the interchange model expects. Notches are the 0.7 cm slits from the sew line, as the client PDS draws
them; grade points (a cut-line point and its rule number) are passed in by the caller.
"""
from app.domain.geom.primitives import Point2D
from app.domain.interchange import GradePoint, InterchangePiece, Point
from app.domain.pattern.edges import stitch_ring
from app.domain.pattern.notch_position import notch_mark
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance
from app.infrastructure.piece_validity import check_cut_geometry


def _xy(point: Point2D) -> Point:
    return point.x, point.y


def piece_to_interchange(piece: Piece, size: str, allowance: SeamAllowance,
                         grade_points: tuple[GradePoint, ...] = ()) -> InterchangePiece:
    positions = {point.id: point.position for point in piece.points}
    mirror = None
    if piece.fold is not None:
        fold = next(segment for segment in piece.outline if segment.id == piece.fold.segment)
        mirror = (_xy(positions[fold.start]), _xy(positions[fold.end]))
    grain = None if piece.grainline is None else (_xy(piece.grainline.start), _xy(piece.grainline.end))
    return InterchangePiece(
        name=piece.name, size=size, quantity=piece.cut.total,
        cut=tuple(_xy(point) for point in check_cut_geometry(piece, allowance)),
        sew=(tuple(_xy(point) for point in stitch_ring(piece)),),
        mirror=mirror,
        notches=tuple(tuple(_xy(end) for end in notch_mark(piece, notch)) for notch in piece.notches),
        grain=grain,
        grade_points=grade_points,
    )
