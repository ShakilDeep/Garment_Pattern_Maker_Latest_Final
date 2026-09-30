import json

import pytest

from app.application.service import NotReady
from app.infrastructure.exports import export_artifact


def project():
    return {
        'name': 'Sizes', 'pattern': {'size': 'L', 'validation': [], 'id': 'base'},
        'grades': [{'size': 'S', 'validation': [], 'id': 'small'}],
        'marker': None, 'audit': [],
    }


def test_selected_grade_export_preserves_base():
    p = project()
    data, _ = export_artifact(p, 'json', size='S')
    assert json.loads(data)['pattern']['id'] == 'small'
    assert p['pattern']['id'] == 'base'


def test_missing_or_stale_selected_grade_is_rejected():
    p = project()
    with pytest.raises(NotReady):
        export_artifact(p, 'json', size='M')
    p['grades'][0]['stale'] = True
    with pytest.raises(NotReady):
        export_artifact(p, 'json', size='S')
