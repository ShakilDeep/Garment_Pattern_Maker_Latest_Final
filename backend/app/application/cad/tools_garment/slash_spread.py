"""Slash-and-spread and add-fullness tools (CAD-03); style-wide like the dart tools."""

from app.application.cad.command import Params, require_params
from app.application.cad.tools_draft.params import text
from app.application.cad.tools_garment.params import (
    SPREAD_PARAMS,
    cut,
    piece_id,
    spread,
    spread_angle,
    spread_follow,
)
from app.application.cad.tools_modify.split_join import TopologyEdit
from app.domain.pattern.garment.allowance import followed
from app.domain.pattern.garment.names import SlashNames, SpreadNames
from app.domain.pattern.garment.pivot import Hinge, slash_spread
from app.domain.pattern.garment.spread import add_fullness
from app.domain.pattern.ids import PointId


def slash_spread_tool(params: Params) -> TopologyEdit:
    """Turn the outline from `hinge_id` forward to the cut about the hinge, opening the slash by the angle."""
    require_params(params, ("piece_id", "hinge_id", "segment_id", "t", "angle_degrees", "slash_id"))
    hinge = Hinge(PointId(text(params, "hinge_id")), spread_angle(params, "angle_degrees"))
    at, names = cut(params), SlashNames.of(text(params, "slash_id"))
    sources = {names.edge: at.segment, names.bridge: at.segment}
    return TopologyEdit(piece_id(params), lambda piece: slash_spread(piece, hinge, at, names),
                        lambda allowance, _piece: followed(allowance, sources), "slash_spread")


def add_fullness_tool(params: Params) -> TopologyEdit:
    require_params(params, (*SPREAD_PARAMS, "amount"))
    spreading, names = spread(params, "amount"), SpreadNames.of(text(params, "slash_id"))
    return TopologyEdit(piece_id(params), lambda piece: add_fullness(piece, spreading, names),
                        spread_follow(spreading, names), "add_fullness")
