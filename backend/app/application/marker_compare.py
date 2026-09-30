"""Specification: numeric previous-versus-current marker comparison."""
from app.application.errors import NotReady


def compare_markers(current, previous):
    if not current or not previous:
        raise NotReady("Generate a marker twice to compare previous and current layouts")
    return {
        "current_width": current["width"],
        "previous_width": previous["width"],
        "current_length": current["length"],
        "previous_length": previous["length"],
        "current_utilization": current["utilization"],
        "previous_utilization": previous["utilization"],
        "length_delta": current["length"] - previous["length"],
        "utilization_delta": current["utilization"] - previous["utilization"],
        "piece_count_delta": len(current["placements"]) - len(previous["placements"]),
        "same_width": current["width"] == previous["width"],
        "same_quantities": current.get("quantities") == previous.get("quantities"),
    }
