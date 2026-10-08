"""A project's size list is data from its imported chart (P1-18); the demo's S–3XL is only the fallback."""
from collections.abc import Iterable
from typing import Annotated

from pydantic import Field

from app.application.errors import Unprocessable
from app.domain.catalog import SIZES

# Request-level shape only; membership in the project's chart is checked by require_sizes.
SizeLabel = Annotated[str, Field(min_length=1, max_length=12, pattern=r"^\S(.*\S)?$")]


def project_sizes(project) -> tuple[str, ...]:
    chart = project.get("chart") or {}
    return tuple(chart.get("sizes") or SIZES)


def base_size(project) -> str | None:
    """The base size the user chose, else the one detected from the chart's formulas."""
    chart = project.get("chart") or {}
    return project.get("resolutions", {}).get("base_size") or chart.get("base_size")


def require_sizes(project, sizes: Iterable[str]) -> None:
    allowed = project_sizes(project)
    unknown = [size for size in sizes if size not in allowed]
    if unknown:
        raise Unprocessable(
            "SIZE_UNKNOWN",
            f"Size {unknown[0]} is not in this project's size chart ({', '.join(allowed)})",
            {"allowed": list(allowed)},
        )
