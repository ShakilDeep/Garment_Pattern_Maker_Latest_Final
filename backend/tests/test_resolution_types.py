"""Explicit requirement resolution types must not invent values or widen keys."""
import pytest

from app.application.requirement_resolve import resolve


def test_approved_default_is_only_demo_profile():
    project = {"resolutions": {}, "measurements": [], "documents": []}
    resolve(project, "profile", "demo_v1", resolution_type="approved_default")
    assert project["resolutions"]["profile"] == "demo_v1"
    assert project["resolution_metadata"]["profile"]["resolution_type"] == "approved_default"
    with pytest.raises(ValueError, match="demo default"):
        resolve(project, "units", "cm", resolution_type="approved_default")


def test_not_applicable_is_only_fabric():
    project = {"resolutions": {}, "measurements": [], "documents": []}
    resolve(project, "fabric", "n/a", resolution_type="not_applicable")
    assert project["resolutions"]["fabric"] == "n/a"
    with pytest.raises(ValueError, match="not applicable"):
        resolve(project, "units", "cm", resolution_type="not_applicable")
