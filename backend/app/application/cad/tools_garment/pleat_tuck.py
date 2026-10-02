"""Pleat and tuck tools (CAD-03): the intake is the user's own value; no pleat depth rule is assumed."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import positive, text
from app.application.cad.tools_garment.params import SPREAD_PARAMS, piece_id, spread, spread_follow
from app.application.cad.tools_modify.split_join import TopologyEdit
from app.domain.pattern.garment.names import SpreadNames
from app.domain.pattern.garment.spread import pleat, tuck


def pleat_tool(params: Params) -> TopologyEdit:
    require_params(params, (*SPREAD_PARAMS, "intake"))
    spreading, names = spread(params, "intake"), SpreadNames.of(text(params, "slash_id"))
    return TopologyEdit(piece_id(params), lambda piece: pleat(piece, spreading, names),
                        spread_follow(spreading, names), "pleat")


def tuck_tool(params: Params) -> TopologyEdit:
    """A pleat stitched down for `length` cm from the first edge: its marks run only that far."""
    require_params(params, (*SPREAD_PARAMS, "intake", "length"))
    spreading, names = spread(params, "intake"), SpreadNames.of(text(params, "slash_id"))
    length = positive(params, "length")
    return TopologyEdit(piece_id(params), lambda piece: tuck(piece, spreading, length, names),
                        spread_follow(spreading, names), "tuck")
