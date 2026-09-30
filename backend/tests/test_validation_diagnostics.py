from copy import deepcopy
from pathlib import Path

import pytest

from app.domain.drafting import draft
from app.infrastructure.geometry_adapter import validate
from app.infrastructure.parsers import parse_xlsx


@pytest.fixture
def values():
    root = Path(__file__).resolve().parents[2]
    rows = parse_xlsx((root / 'references/Book2(4).xlsx').read_bytes(), 'source.xlsx')
    return {row['key']: row['values']['L']['value'] for row in rows}


def test_missing_piece_is_a_corrective_issue(values):
    pattern = draft(values, 'L')
    pattern['pieces'] = pattern['pieces'][:-1]
    issues = validate(pattern)
    assert any(i['code'] == 'PIECE_INVENTORY' and i['severity'] == 'ERROR' for i in issues)
    assert all(i.get('rule') and i.get('action') for i in issues)


def test_notch_must_be_on_boundary(values):
    pattern = draft(values, 'L')
    piece = pattern['pieces'][5]
    piece['notches'] = [[piece['width'] / 2, piece['height'] / 2]]
    assert any(i['code'] == 'NOTCHES' and i['severity'] == 'ERROR' for i in validate(pattern))


def test_intersection_diagnostic_and_short_outline(values):
    pattern = draft(values, 'L')
    pattern['pieces'][0]['points'] = [[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]
    issue = next(i for i in validate(pattern) if i['code'] == 'GEOMETRY')
    assert issue['severity'] == 'ERROR'
    assert 'intersection' in issue['detail'].lower()
    pattern['pieces'][0]['points'] = [[0, 0]]
    assert validate(pattern)[0]['severity'] == 'ERROR'


@pytest.mark.parametrize('offset,expected', [(0.009, 'PASS'), (0.011, 'WARNING')])
def test_seam_tolerance_boundary(values, offset, expected):
    pattern = draft(values, 'L')
    pattern['pieces'][1]['seams']['yoke'] += offset
    issue = next(i for i in validate(pattern) if i.get('name') == 'Yoke seam')
    assert issue['severity'] == expected


def test_grading_diagnostics_detect_shrinking_size(values):
    from app.infrastructure.validation import validate_grades

    small = draft(values, 'S')
    large = deepcopy(small)
    large['size'] = 'M'
    large['pieces'][0]['width'] -= 3
    assert any(i['severity'] == 'WARNING' for i in validate_grades([large, small]))


def test_export_routes_are_not_double_prefixed(tmp_path):
    from app.api.main import create_app
    paths = create_app(f'sqlite:///{tmp_path}/api.db').openapi()['paths']
    assert '/api/v1/projects/{pid}/exports' in paths
    assert '/api/v1/api/v1/projects/{pid}/exports' not in paths


def test_archived_projects_cannot_generate(tmp_path):
    from app.application.service import NotReady, Service
    from app.infrastructure.repository import Repository
    service = Service(Repository(f'sqlite:///{tmp_path}/archive.db'))
    project = service.create('Archived')
    project['archived'] = True
    with pytest.raises(NotReady, match='archived'):
        service.generate(project, 'L')
