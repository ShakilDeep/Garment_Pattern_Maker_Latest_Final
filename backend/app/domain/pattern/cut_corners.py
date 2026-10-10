"""The cut-line corner of every outline point (T131): where the two edges' cut lines meet (the mitre).

At a point V, the incoming edge's cut line runs along its end tangent, offset outwards by its allowance,
and the outgoing edge's along its start tangent offset by its own; their crossing is the corner of the
cut line, the point an AAMA grade rule is attached to. Where the two edges run on in line (parallel
tangents) the corner is V offset outwards beside it.
"""
from app.domain.geom.lines import along
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.pattern.corner_join import CornerJoin
from app.domain.pattern.edges import edge_tangents, orientation, stitch_ring
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance


def _outward(direction: Vector2D, side: int) -> Vector2D:
    """Right of travel on a counter-clockwise ring (side +1), left on a clockwise one."""
    return Vector2D(direction.y * side, -direction.x * side)


def cut_corners(piece: Piece, allowance: SeamAllowance) -> dict[PointId, Point2D]:
    side = orientation(stitch_ring(piece))
    positions = {point.id: point.position for point in piece.points}
    tangents = edge_tangents(piece)
    corners = {}
    for index, outgoing in enumerate(piece.outline):
        incoming = piece.outline[index - 1]
        vertex = positions[outgoing.start]
        in_dir, out_dir = tangents[index - 1][1], tangents[index][0]
        in_width, out_width = allowance.width_of(incoming.id), allowance.width_of(outgoing.id)
        join = CornerJoin(vertex, in_dir, out_dir, along(vertex, _outward(in_dir, side), in_width),
                          along(vertex, _outward(out_dir, side), out_width), in_width, out_width)
        met = join.meet()
        corners[outgoing.start] = met if met is not None else join.in_end
    return corners
