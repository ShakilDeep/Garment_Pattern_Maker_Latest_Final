"""Dart tools (CAD-03): create, rotate and close. Like split and join (P1-09) they change a piece's edges,
so they apply to every size with the same parameters and ids, and the seam allowance follows the edges.
"""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import number, positive, text
from app.application.cad.tools_garment.params import cut, piece_id
from app.application.cad.tools_modify.split_join import TopologyEdit
from app.domain.pattern.garment.allowance import followed
from app.domain.pattern.garment.dart import DartSpan, create_dart, dart_at
from app.domain.pattern.garment.names import DartNames, SlashNames
from app.domain.pattern.garment.pivot import close_dart, rotate_dart
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.piece import Piece
from app.domain.pattern.seam import SeamAllowance


def create_dart_tool(params: Params) -> TopologyEdit:
    require_params(params, ("piece_id", "segment_id", "t_start", "t_end", "length", "dart_id"))
    segment = SegmentId(text(params, "segment_id"))
    span = DartSpan(segment, number(params, "t_start"), number(params, "t_end"), positive(params, "length"))
    names = DartNames.of(text(params, "dart_id"))
    return TopologyEdit(piece_id(params), lambda piece: create_dart(piece, span, names),
                        lambda allowance, _piece: followed(allowance, {names.edge: segment}), "create_dart")


def rotate_dart_tool(params: Params) -> TopologyEdit:
    require_params(params, ("piece_id", "apex_id", "segment_id", "t", "dart_id"))
    apex, at, names = PointId(text(params, "apex_id")), cut(params), DartNames.of(text(params, "dart_id"))

    def follow(allowance: SeamAllowance, piece: Piece) -> SeamAllowance:
        dart = dart_at(piece, apex)
        sources = {names.edge: at.segment, names.leg1: dart.leg1.id, names.leg2: dart.leg2.id}
        return followed(allowance, sources, {dart.leg1.id, dart.leg2.id, dart.leg2.end})

    return TopologyEdit(piece_id(params), lambda piece: rotate_dart(piece, apex, at, names), follow, "rotate_dart")


def close_dart_tool(params: Params) -> TopologyEdit:
    """The dart's intake opens at the cut instead, bridged by a straight edge (flare at that edge)."""
    require_params(params, ("piece_id", "apex_id", "segment_id", "t", "slash_id"))
    apex, at, names = PointId(text(params, "apex_id")), cut(params), SlashNames.of(text(params, "slash_id"))

    def follow(allowance: SeamAllowance, piece: Piece) -> SeamAllowance:
        dart = dart_at(piece, apex)
        sources = {names.edge: at.segment, names.bridge: at.segment}
        return followed(allowance, sources, {dart.leg1.id, dart.leg2.id, dart.leg2.end, apex})

    return TopologyEdit(piece_id(params), lambda piece: close_dart(piece, apex, at, names), follow, "close_dart")
