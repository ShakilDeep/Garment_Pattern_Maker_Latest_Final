"""Derive the 1078375 block's data from the client PDS (T130): its measurement set and its shape constants.

The measurements follow ``shirt.measures.DEFINITIONS`` on the named sew-line vertices. Shape constants are
what the measurement formulas leave over: each point's offset, each curve's best cubic (``fit_cubic``) as
chord fractions, and each notch's parameter on its edge. ``scripts/derive_shirt_1078375.py`` writes them.
"""
from math import hypot

from app.domain.blocks.shirt.measures import DEFINITIONS
from app.domain.blocks.shirt.recipe import NotchRecipe, evaluate
from app.domain.blocks.shirt.shape import chord_fractions
from app.domain.geom.bezier_fit import fit_cubic
from app.domain.geom.primitives import Point2D
from app.domain.interchange import Point
from app.domain.pattern.point import quantize
from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.named_points import foot
from app.infrastructure.pds.shirt_named import NamedPiece, named_pieces, smooth_ends

STYLE = "1078375"
NOTE = "Derived from the 1078375 PDS sew line, base size L, by scripts/derive_shirt_1078375.py. Do not edit."


def _notch_t(piece: NamedPiece, notch: NotchRecipe, base: Point) -> float:
    (ax, ay), (bx, by) = piece.at(notch.start), piece.at(notch.end)
    at = foot(piece.ring, base)[1]
    if at in (piece.at(notch.start), piece.at(notch.end)):
        return 0.0 if at == piece.at(notch.start) else 1.0
    return quantize(hypot(at[0] - ax, at[1] - ay) / hypot(bx - ax, by - ay))


def _shape(piece: NamedPiece, measures: dict[str, float]) -> dict:
    recipe = piece.recipe
    ox, oy = piece.at(recipe.origin[0])[0], piece.at(recipe.origin[1])[1]
    offsets = {p.name: [quantize(piece.at(p.name)[0] - ox - evaluate(p.x, measures)),
                        quantize(piece.at(p.name)[1] - oy - evaluate(p.y, measures))] for p in recipe.points}
    handles = {}
    for (start, end), kind in zip(recipe.edges(), recipe.kinds, strict=True):
        if kind == "cubic":
            samples = [Point2D(*point) for point in piece.run(start, end)]
            fit = fit_cubic(samples, smooth_ends(piece, start, end, samples))
            fractions = chord_fractions(samples[0], samples[-1], (fit.start_handle, fit.end_handle))
            handles[f"{start}:{end}"] = [quantize(value) for value in fractions]
    notches = {n.name: _notch_t(piece, n, base) for n, base in zip(recipe.notches, piece.notch_bases, strict=True)}
    return {"offsets": offsets, "handles": handles, "notches": notches}


def derive(style: ReferenceStyle) -> tuple[dict, dict]:
    named = named_pieces(style)
    measurements, values = {}, {}
    for name, d in DEFINITIONS.items():
        axis, piece = (0 if d.axis == "x" else 1), named[d.piece]
        values[name] = quantize(piece.at(d.end)[axis] - piece.at(d.start)[axis])
        measurements[name] = {"value_cm": values[name],
                              "source": f"{piece.recipe.name}: {d.end}.{d.axis} - {d.start}.{d.axis}, PDS sew line"}
    head = {"source_pds": STYLE, "size": style.base_size, "note": NOTE}
    return ({**head, "measurements": measurements},
            {**head, "pieces": {piece_id: _shape(piece, values) for piece_id, piece in named.items()}})
