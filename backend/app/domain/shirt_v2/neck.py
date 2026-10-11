"""shirt_v2 collar and band: the 1078375 PDS CLR and BND TOP halves, rescaled to the chart.

The band keeps the PDS curve (it rises toward CF) and is stretched along its length until its neck edge
equals the drafted half neckline plus the PDS band overlap; its height is the chart's band width. The collar
sits on the band top edge, short of its end by the PDS setback, with the chart's CB width and point length.
"""
from functools import cache
from math import sqrt

from app.domain.blocks.shirt.body import FRONT, YOKE
from app.domain.blocks.shirt.draft import positions
from app.domain.blocks.shirt.parts import BAND_TOP, COLLAR
from app.domain.blocks.shirt.recipe import PieceRecipe
from app.domain.blocks.shirt.reference import reference_measurements
from app.domain.blocks.shirt.shape import chord_handles, shape
from app.domain.geom.primitives import Point2D
from app.domain.geometry import length
from app.domain.shirt_v2.curves import Pt, bezier

REF = reference_measurements()


def _edges(recipe: PieceRecipe, sx: float, sy: float, points: dict[str, tuple[float, float]] | None = None):
    """Each non-fold edge of the recipe as a sampled polyline, the block points scaled by (sx, sy)."""
    form = shape()[recipe.id]
    at = {k: [v.x * sx, v.y * sy] for k, v in positions(recipe, REF, form).items()}
    at.update({k: list(v) for k, v in (points or {}).items()})
    out = {}
    for (start, end), kind, role in zip(recipe.edges(), recipe.kinds, recipe.roles, strict=True):
        if role != "fold":
            out[f"{start}:{end}"] = _chord_cubic(at[start], at[end], form.handles[f"{start}:{end}"]) \
                if kind == "cubic" else [at[start], at[end]]
    return out


def _chord_cubic(start: Pt, end: Pt, fractions: tuple[float, float, float, float]) -> list[Pt]:
    """The block curve between two scaled points, its handles as fractions of the chord (as the block draws)."""
    first, last = chord_handles(Point2D(*start), Point2D(*end), fractions)
    return bezier(start, (start[0] + first.x, start[1] + first.y), (end[0] + last.x, end[1] + last.y), end)


@cache
def offsets() -> tuple[float, float]:
    """PDS L, per half: band neck edge beyond the FRT + back YK necklines, and band top edge beyond the
    collar neck edge (cm)."""
    neckline = length(_edges(FRONT, 1, 1)["CF_neck:HPS"]) + length(_edges(YOKE, 1, 1)["CB_neck:HPS"])
    band, collar = _edges(BAND_TOP, 1, 1), _edges(COLLAR, 1, 1)
    return (length(band["band_neck_end:CB_band_neck"]) - neckline,
            length(band["CB_band_top:band_top_end"]) - length(collar["CB_collar_neck:collar_neck_end"]))


def _half(edges: dict) -> list[Pt]:
    runs = list(edges.values())
    return [*runs[0], *[p for run in runs[1:] for p in run[1:]]]


def band(m: dict, half_neckline: float) -> tuple[list[Pt], float]:
    """Band half from CB top edge round to CB neck edge (block frame: x along, neck edge at +y) and the
    length of its top edge, which the collar is set on."""
    sy, sx, goal = m["collar_band_width_cb"] / REF["band_height_cb"], 1.0, half_neckline + offsets()[0]
    for _ in range(4):  # the neck edge is a curve: rescale until it reaches its target length
        edges = _edges(BAND_TOP, sx, sy)
        sx *= goal / length(edges["band_neck_end:CB_band_neck"])
    edges = _edges(BAND_TOP, sx, sy)
    return _half(edges), length(edges["CB_band_top:band_top_end"])


def collar(m: dict, band_top: float) -> list[Pt]:
    """Collar half from CB neck edge round to CB outer edge (block frame: x along, outer edge at +y)."""
    sy, sx, goal = m["collar_width_cb"] / REF["collar_width_cb"], 1.0, band_top - offsets()[1]
    for _ in range(4):
        sx *= goal / length(_edges(COLLAR, sx, sy)["CB_collar_neck:collar_neck_end"])
    if not m.get("collar_point"):
        return _half(_edges(COLLAR, sx, sy))
    end = _edges(COLLAR, sx, sy)["CB_collar_neck:collar_neck_end"][-1]
    reach = (REF["collar_length"] - REF["collar_neck_reach"]) * sx  # the point edge's run along the collar
    rise = sqrt(max(m["collar_point"] ** 2 - reach * reach, 0.0))  # so the point edge is the chart's length
    return _half(_edges(COLLAR, sx, sy, {"collar_point": (end[0] + reach, end[1] + rise)}))


def unfold_x(half: list[Pt]) -> list[Pt]:
    """Mirror a half that starts and ends on the CB line x = 0 into the whole piece."""
    return [*half, *[[-x, y] for x, y in reversed(half)][1:]]
