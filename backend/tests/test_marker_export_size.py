import pytest

from app.application.service import NotReady
from app.infrastructure.exports import export_artifact


def _marker():
    return {
        "placements": [{
            "name": "Front", "points": [[0, 0], [4, 0], [4, 4], [0, 4]],
            "x": 1, "y": 1, "width": 4, "height": 4,
        }],
        "width": 20, "length": 20, "utilization": 50, "waste": 50,
        "quantity": 1, "size": "L", "strategy": "first-fit", "gap": 0.5,
    }


def test_marker_export_ignores_unrelated_ui_size():
    """Marker Nesting may keep UI size M while the marker was built for L."""
    p = {
        "name": "Sizes",
        "pattern": {"size": "L", "validation": [], "id": "base", "stale": False},
        "grades": [],
        "marker": _marker(),
        "audit": [],
        "documents": [],
    }
    svg, svg_mime = export_artifact(p, "marker-svg", size="M")
    pdf, pdf_mime = export_artifact(p, "marker-pdf", size="M")
    assert svg_mime == "image/svg+xml" and b"<svg" in svg
    assert pdf_mime == "application/pdf" and pdf.startswith(b"%PDF")


def test_marker_export_still_requires_marker():
    p = {
        "name": "Sizes",
        "pattern": {"size": "L", "validation": [], "id": "base", "stale": False},
        "grades": [],
        "marker": None,
        "audit": [],
    }
    with pytest.raises(NotReady, match="marker"):
        export_artifact(p, "marker-svg", size="M")
