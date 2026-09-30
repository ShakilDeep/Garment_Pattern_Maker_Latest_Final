from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.requirements import requirements, resolve


def test_production_requirements_do_not_block_demo_and_need_source_evidence():
    project = {'resolutions': {}, 'measurements': [], 'documents': [{'id': 'source'}]}
    items = [i for i in requirements(project)['items'] if i['category'] == 'Production calibration']
    assert len(items) >= 8
    assert all(not item['blocking'] and item['status'] == 'MISSING' for item in items)
    key = items[0]['key']
    with pytest.raises(ValueError, match='source evidence'):
        resolve(project, key, 'reviewed')
    with pytest.raises(ValueError, match='source'):
        resolve(project, key, 'reviewed', resolution_type='source', source_id='foreign', note='Checked')
    resolve(project, key, 'reviewed', resolution_type='source', source_id='source', note='Reviewed supplied rules')
    item = next(i for i in requirements(project)['items'] if i['key'] == key)
    assert item['status'] == 'AVAILABLE'
    assert item['resolution']['source_id'] == 'source'
    project['documents'] = []
    assert next(i for i in requirements(project)['items'] if i['key'] == key)['status'] == 'MISSING'


def test_request_contains_only_unresolved_calibration_items_and_project_context(tmp_path: Path):
    client = TestClient(create_app(f'sqlite:///{tmp_path / "calibration.db"}'))
    project = client.post('/api/v1/projects', json={'name':'Calibration shirt', 'demo':True}).json()
    base = '/api/v1/projects/' + project['id']
    response = client.get(base + '/calibration-request')
    assert response.status_code == 200
    assert 'Calibration shirt' in response.text
    assert project['id'] in response.text
    assert 'calibration:base_pattern' in response.text
    assert 'measurement:half_chest' not in response.text
    resolved = client.post(base + '/requirements/calibration:base_pattern/resolve', json={
        'value':'reviewed', 'resolution_type':'source', 'source_id':project['documents'][0]['id'],
        'note':'Client review confirms this reference contains the approved block', 'actor':'Client reviewer'})
    assert resolved.status_code == 200
    text = client.get(base + '/calibration-request').text
    assert 'calibration:base_pattern' not in text
    assert 'calibration:grading' in text
    assert 'does not certify production' in text
    assert client.get('/api/v1/projects/missing/calibration-request').status_code == 404
