import pytest

from app.application.state import transition


def test_created_can_restore_imported_geometry():
    p = {"state": "CREATED", "transitions": []}
    transition(p, "PATTERN_NEEDS_REVIEW", "geometry_imported")
    assert p["state"] == "PATTERN_NEEDS_REVIEW"


def test_grading_ready_can_export():
    p = {"state": "GRADING_READY", "transitions": []}
    transition(p, "EXPORT_READY", "export_created")
    assert p["state"] == "EXPORT_READY"
    p = {'state': 'CREATED', 'transitions': []}
    transition(p, 'SOURCES_UPLOADED', 'source_uploaded')
    transition(p, 'NEEDS_INPUT', 'extraction_review_needed')
    assert p['state'] == 'NEEDS_INPUT'
    assert [v['from'] for v in p['transitions']] == ['CREATED', 'SOURCES_UPLOADED']


def test_forbidden_transition_preserves_state():
    p = {'state': 'CREATED', 'transitions': []}
    with pytest.raises(ValueError):
        transition(p, 'MARKER_READY', 'skip_workflow')
    assert p == {'state': 'CREATED', 'transitions': []}


def test_invalidation_can_return_to_needs_input():
    p = {'state': 'EXPORT_READY', 'transitions': []}
    transition(p, 'NEEDS_INPUT', 'measurement_changed')
    assert p['state'] == 'NEEDS_INPUT'


def test_demo_complete_can_reexport_marker_artifacts():
    """Marker download buttons call EXPORT_READY on every export."""
    p = {'state': 'DEMO_COMPLETE', 'transitions': []}
    transition(p, 'EXPORT_READY', 'export_created')
    assert p['state'] == 'EXPORT_READY'


def test_pattern_ready_can_nest_marker():
    p = {'state': 'PATTERN_READY', 'transitions': []}
    transition(p, 'MARKER_READY', 'marker_generated')
    assert p['state'] == 'MARKER_READY'
