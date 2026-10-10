"""The PDS per-size numbers grading reads (T131): each piece's numbers per size, their steps from the base
size, and the proportional steps (each measurement's L value scaled by its piece's growth on its axis).
"""
from app.domain.blocks.shirt.grading import GROWS_WITH, STARTED, PdsNumber
from app.domain.blocks.shirt.measures import DEFINITIONS, RECIPES
from app.domain.reference import ReferenceStyle

FIELDS = ("size_x_cm", "size_y_cm", "sew_perimeter_cm", "sew_area_m2")


def pds_values(style: ReferenceStyle, size: str) -> dict[PdsNumber, float]:
    return {(piece.name, field): float(getattr(piece.geometry[size], field) or 0.0)
            for piece in style.pieces for field in FIELDS}


def pds_steps(style: ReferenceStyle, size: str) -> dict[PdsNumber, float]:
    """Each PDS piece number's step from the base size to ``size`` (cm; areas in m²)."""
    here, base = pds_values(style, size), pds_values(style, style.base_size)
    return {number: here[number] - base[number] for number in here}


def axis_number(measurement: str) -> PdsNumber:
    """The PDS number of the measurement's own piece along its grading axis (length for x, width for y)."""
    names = {recipe.id: recipe.name for recipe in RECIPES}
    definition = DEFINITIONS[measurement]
    axis = GROWS_WITH.get(measurement, definition.axis)
    return names[definition.piece], "size_x_cm" if axis == "x" else "size_y_cm"


def proportional_steps(style: ReferenceStyle, size: str, base: dict[str, float]) -> list[float]:
    """The step of each STARTED measurement when it scales with its piece on its axis.

    For the PROPORTIONAL measurements these are their steps; for the TRUED ones they are only the starting
    guesses that ``true_seams`` then solves from.
    """
    steps, sizes = pds_steps(style, size), pds_values(style, style.base_size)
    return [base[name] * steps[axis_number(name)] / sizes[axis_number(name)] for name in STARTED]
