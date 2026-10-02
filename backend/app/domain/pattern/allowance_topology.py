"""Keep a piece's seam allowance (PM-03) true when split or join changes its edges (CAD-02).

A split must not change the cut line, so the new half inherits the parent edge's explicit width. A join
removes a point and an edge id, so the two halves must already share one width; the second edge's entry and
any corner style at the removed point go away with them.
"""

from app.domain.pattern.ids import PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance


def after_split(allowance: SeamAllowance, segment: SegmentId, new_segment: SegmentId) -> SeamAllowance:
    widths = dict(allowance.edge_widths)
    if segment in widths:
        widths[new_segment] = widths[segment]
    return SeamAllowance(allowance.default_width, tuple(widths.items()), allowance.corner_styles)


def after_join(
    allowance: SeamAllowance, first: SegmentId, second: SegmentId, point: PointId
) -> SeamAllowance:
    if allowance.width_of(first) != allowance.width_of(second):
        raise ValueError(
            f"Edges {first} and {second} have different seam allowances; "
            "give them the same width before joining"
        )
    widths = tuple((key, width) for key, width in allowance.edge_widths if key != second)
    corners = tuple((key, style) for key, style in allowance.corner_styles if key != point)
    return SeamAllowance(allowance.default_width, widths, corners)
