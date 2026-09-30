"""Golden mixed-size marker metrics and independent spacing checks."""
import pytest
from shapely.geometry import Polygon, box
from test_demo_goldens import values_for

from app.domain.drafting import draft
from app.infrastructure.marker import marker_batch


def test_fixed_mixed_marker_metrics_and_independent_spacing(rows, golden):
    config = golden["marker"]["config"]
    patterns = {s: {**draft(values_for(rows, s), s), "id": f"golden:{s}"} for s in config["quantities"]}
    result = marker_batch(patterns, **config)
    assert result == marker_batch(patterns, **config)
    for key in ("length", "utilization", "waste"):
        assert result[key] == pytest.approx(golden["marker"][key], abs=1e-6, rel=0)
    assert len(result["placements"]) == golden["marker"]["placements"]
    shapes = []
    for p in result["placements"]:
        shape = Polygon([(x + p["x"], y + p["y"]) for x, y in p["points"]])
        assert box(0, 0, result["width"], result["length"]).covers(shape)
        assert all(shape.distance(other) >= config["gap"] - 1e-6 for other in shapes)
        shapes.append(shape)
