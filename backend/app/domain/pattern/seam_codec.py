"""Memento for seam allowances (PM-03): JSON-ready data and back; loading re-runs SeamAllowance's checks."""

from collections.abc import Mapping

from app.domain.pattern.ids import PieceId, PointId, SegmentId
from app.domain.pattern.seam import SeamAllowance


def allowance_to_data(allowance: SeamAllowance) -> dict:
    return {
        "default_width": allowance.default_width,
        "edge_widths": [[str(segment), width] for segment, width in allowance.edge_widths],
        "corner_styles": [[str(corner), style.value] for corner, style in allowance.corner_styles],
    }


def allowance_from_data(data: object) -> SeamAllowance:
    """Rebuild an allowance; malformed data raises ValueError naming the problem."""
    if not isinstance(data, dict):
        raise ValueError("A seam allowance must be an object")  # noqa: TRY004 - the API maps ValueError to 400
    try:
        edges = tuple((SegmentId(key), width) for key, width in data["edge_widths"])
        corners = tuple((PointId(key), style) for key, style in data["corner_styles"])
        return SeamAllowance(data["default_width"], edges, corners)
    except KeyError as exc:
        raise ValueError(f"Invalid seam allowance: missing field {exc.args[0]!r}") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid seam allowance: {exc}") from exc


def allowances_to_data(allowances: Mapping[PieceId, SeamAllowance]) -> dict[str, dict]:
    return {str(piece): allowance_to_data(allowance) for piece, allowance in allowances.items()}


def allowances_from_data(data: object) -> dict[PieceId, SeamAllowance]:
    if not isinstance(data, dict):
        raise ValueError("Seam allowances must be an object keyed by piece id")  # noqa: TRY004
    return {PieceId(piece): allowance_from_data(value) for piece, value in data.items()}
