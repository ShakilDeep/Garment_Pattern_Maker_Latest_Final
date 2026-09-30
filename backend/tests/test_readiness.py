from app.application.readiness import check_operation


def test_export_requires_the_requested_size():
    p = {'pattern': {'size': 'L', 'validation': []}, 'grades': []}
    result = check_operation(p, 'export', size='S')
    assert not result['ready']
    assert result['blockers'][0]['key'] == 'pattern:S'


def test_marker_requires_explicit_configuration():
    p = {'pattern': {'size': 'L', 'validation': []}, 'grades': []}
    result = check_operation(p, 'marker')
    assert {i['key'] for i in result['blockers']} == {'width', 'quantities', 'grain_policy'}
    assert check_operation(p, 'marker', width=150, quantities={'L': 1}, grain_policy='vertical')['ready']


def test_stale_and_error_geometry_blocks_export():
    p = {'pattern': {'size': 'L', 'stale': True, 'validation': []}, 'grades': []}
    assert not check_operation(p, 'export')['ready']
    p['pattern'].update(stale=False, validation=[{'severity': 'ERROR'}])
    assert not check_operation(p, 'export')['ready']
