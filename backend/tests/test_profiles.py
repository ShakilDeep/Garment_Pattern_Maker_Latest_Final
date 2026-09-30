import pytest

from app.domain.profiles import get_profile


def test_profile_declares_rules_and_rejects_uninstalled_profile():
    profile = get_profile("demo_v1")
    assert profile.garment_family == "mens_regular_long_sleeve_shirt"
    assert "half_chest" in profile.required_measurements
    assert profile.version == "1.0.0"
    with pytest.raises(ValueError):
        get_profile("client_production")
