"""The 1078375 block's named points on the client PDS sew line (T130, T131).

Each recipe point is snapped to its PDS sew-line vertex through the locators; a point that is no vertex (the
sleeve crown) is the foot of the piece's notch, inserted as a vertex. Where a curve meets a smooth point,
its handle there follows the PDS line's direction of travel through that point (``smooth_ends``).
"""
from dataclasses import dataclass

from app.domain.blocks.shirt.measures import RECIPES
from app.domain.blocks.shirt.recipe import PieceRecipe
from app.domain.geom.bezier_fit import fit_cubic
from app.domain.geom.lines import unit
from app.domain.geom.primitives import Point2D, Vector2D
from app.domain.interchange import Point
from app.domain.reference import ReferenceStyle
from app.infrastructure.pds.named_points import ccw_ring, foot, run, snap, travel, with_foot
from app.infrastructure.pds.shirt_locators import LOCATORS


@dataclass(frozen=True)
class NamedPiece:
    recipe: PieceRecipe
    ring: list[Point]
    index: dict[str, int]
    notch_bases: list[Point]

    def at(self, name: str) -> Point:
        return self.ring[self.index[name]]

    def run(self, start: str, end: str) -> list[Point]:
        return run(self.ring, self.index[start], self.index[end])


def named_pieces(style: ReferenceStyle) -> dict[str, NamedPiece]:
    by_name = {piece.name: piece for piece in style.pieces}
    named = {}
    for recipe in RECIPES:
        if recipe.name not in by_name:
            raise ValueError(f"PDS has no piece {recipe.name}")
        ring, bases = ccw_ring(by_name[recipe.name]), [n[0] for n in by_name[recipe.name].outline.notches]
        locators = dict(LOCATORS[recipe.id])
        for name in [name for name, at in locators.items() if at is None]:
            if not bases:
                raise ValueError(f"PDS piece {recipe.name} has no notch to place {name} at")
            ring = with_foot(ring, bases[0])
            locators[name] = foot(ring, bases[0])[1]
        index = {name: snap(ring, name, at) for name, at in locators.items() if at is not None}
        named[recipe.id] = NamedPiece(recipe, ring, index, bases)
    return named


def smooth_ends(piece: NamedPiece, start: str, end: str, samples: list[Point2D]) -> tuple[Vector2D, Vector2D] | None:
    """Handle directions for a curve meeting a smooth point: along the PDS line through that point there, and
    the free fit's own direction at the other end (fixing that one too would cost the fit its 0.1 cm)."""
    smooth = piece.recipe.smooth
    if start not in smooth and end not in smooth:
        return None
    free = fit_cubic(samples)
    first, last = unit(free.start_handle), unit(free.end_handle)
    if start in smooth:
        first = Vector2D(*travel(piece.ring, piece.index[start]))
    if end in smooth:
        dx, dy = travel(piece.ring, piece.index[end])
        last = Vector2D(-dx, -dy)
    return first, last
