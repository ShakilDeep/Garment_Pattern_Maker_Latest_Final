"""Interpreter: a piece recipe, the measurements and its shape constants become a V6 ``Piece`` with named points.

Grain runs along x (parallel to CF/CB, docs/drafting/shirt.md Q7). The PDS gives no grain position, so the
line is centred on the piece's points over half its length; only its direction carries meaning.
"""
from collections.abc import Mapping

from app.domain.blocks.shirt.recipe import PieceRecipe, evaluate
from app.domain.blocks.shirt.shape import PieceShape, chord_handles
from app.domain.blocks.sketch.sketch import PieceSketch, PieceSpec
from app.domain.geom.primitives import Point2D
from app.domain.pattern.cutting import CutQuantity
from app.domain.pattern.ids import PointId
from app.domain.pattern.piece import Piece
from app.domain.pattern.smooth import smooth_at

GRAIN_SPAN = 0.5  # share of the piece length the grain line covers


def positions(recipe: PieceRecipe, measures: Mapping[str, float], shape: PieceShape) -> dict[str, Point2D]:
    """Each named point: its measurement formula plus its shape offset, in the piece's own frame (cm)."""
    placed = {}
    for point in recipe.points:
        dx, dy = shape.offsets[point.name]
        placed[point.name] = Point2D(evaluate(point.x, measures) + dx, evaluate(point.y, measures) + dy)
    return placed


def _outline(recipe: PieceRecipe, at: dict[str, Point2D], shape: PieceShape) -> PieceSketch:
    first = recipe.points[0].name
    sketch = PieceSketch().start(first, at[first].x, at[first].y)
    for (start, end), kind in zip(recipe.edges(), recipe.kinds, strict=True):
        handles = chord_handles(at[start], at[end], shape.handles[f"{start}:{end}"]) if kind == "cubic" else None
        if end == first:
            sketch.close(handles)
        elif handles is None:
            sketch.line_to(end, at[end].x, at[end].y)
        else:
            sketch.curve_to(end, (at[end].x, at[end].y), handles)
    return sketch


def _grain(at: dict[str, Point2D]) -> tuple[Point2D, Point2D]:
    xs, ys = [p.x for p in at.values()], [p.y for p in at.values()]
    middle, half = (min(xs) + max(xs)) / 2, (max(xs) - min(xs)) * GRAIN_SPAN / 2
    level = (min(ys) + max(ys)) / 2
    return Point2D(middle - half, level), Point2D(middle + half, level)


def draft_recipe(recipe: PieceRecipe, measures: Mapping[str, float], shape: PieceShape) -> Piece:
    at = positions(recipe, measures, shape)
    sketch = _outline(recipe, at, shape).grain(*_grain(at))
    if recipe.fold is not None:
        sketch.fold(*recipe.fold)
    for notch in recipe.notches:
        sketch.notch(notch.name, notch.start, notch.end, shape.notches[notch.name])
    piece = sketch.build(PieceSpec(recipe.id, recipe.name, CutQuantity(*recipe.cut)))
    for name in recipe.smooth:
        piece = smooth_at(piece, PointId(name))
    return piece
