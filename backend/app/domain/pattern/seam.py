"""Seam allowance (PM-03): a default width, per-edge widths keyed by segment id and per-corner styles.

Widths are in cm and may be 0 (a fold edge or a raw hem). Unlisted edges use the default width and unlisted
corners use the mitre style. Fitting the allowance to a piece (known ids, no width on the fold) is checked
when the cut outline is built.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

from app.domain.pattern.corners import CornerStyle
from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.point import is_real, quantize

PAIR = 2


def _width(value: object, what: str) -> float:
    if not is_real(value) or quantize(value) < 0:  # type: ignore[arg-type]
        raise ValueError(f"{what} must be a non-negative number of cm")
    return quantize(value)  # type: ignore[arg-type]


def _pairs(entries: Iterable[object], kind: type, what: str) -> tuple[tuple, ...]:
    try:
        items = tuple(entries)
    except TypeError as exc:
        raise ValueError(f"{what} must be (id, value) pairs") from exc
    if not all(isinstance(pair, tuple) and len(pair) == PAIR for pair in items):
        raise ValueError(f"{what} must be (id, value) pairs")
    pairs = cast(tuple[tuple, ...], items)
    if not all(isinstance(key, kind) for key, _ in pairs):
        raise ValueError(f"{what} must be keyed by {kind.__name__}")
    keys = [key for key, _ in pairs]
    repeated = sorted({str(key) for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"{what} name {', '.join(repeated)} more than once")
    return pairs


def _style(value: object) -> CornerStyle:
    try:
        return CornerStyle(value)
    except ValueError as exc:
        raise ValueError(f"Unknown corner style {value!r}; use {[s.value for s in CornerStyle]}") from exc


@dataclass(frozen=True)
class SeamAllowance:
    default_width: float
    edge_widths: tuple[tuple[SegmentId, float], ...] = ()
    corner_styles: tuple[tuple[PointId, CornerStyle], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_width", _width(self.default_width, "The default seam allowance"))
        edges = _pairs(self.edge_widths, SegmentId, "Edge widths")
        widths = tuple((key, _width(value, f"The allowance of {key}")) for key, value in edges)
        object.__setattr__(self, "edge_widths", widths)
        corners = _pairs(self.corner_styles, PointId, "Corner styles")
        object.__setattr__(self, "corner_styles", tuple((key, _style(value)) for key, value in corners))

    def width_of(self, segment: SegmentId) -> float:
        return dict(self.edge_widths).get(segment, self.default_width)

    def style_at(self, corner: PointId) -> CornerStyle:
        return dict(self.corner_styles).get(corner, CornerStyle.MITRE)
