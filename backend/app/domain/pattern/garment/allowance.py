"""Keep a piece's seam allowance (PM-03) true when a garment tool changes its edges (CAD-03).

A new edge that continues or bridges an existing one inherits that edge's explicit width, so the cut line
stays the same along it; a dart's new legs inherit the old legs' widths, a mirrored edge or corner its
original's. Entries for edges and corners that no longer exist are dropped (unknown ids are refused when
the cut outline is built). Edges with no explicit width keep using the default.
"""

from collections.abc import Collection, Mapping

from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance


def followed(
    allowance: SeamAllowance,
    widths_from: Mapping[SegmentId, SegmentId],
    dropped: Collection[SegmentId | PointId] = (),
    corners_from: Mapping[PointId, PointId] | None = None,
) -> SeamAllowance:
    widths, corners = dict(allowance.edge_widths), dict(allowance.corner_styles)
    for new, source in widths_from.items():
        if source in widths:
            widths[new] = widths[source]
    for new_corner, source_corner in (corners_from or {}).items():
        if source_corner in corners:
            corners[new_corner] = corners[source_corner]
    return SeamAllowance(
        allowance.default_width,
        tuple((key, width) for key, width in widths.items() if key not in dropped),
        tuple((key, style) for key, style in corners.items() if key not in dropped),
    )
