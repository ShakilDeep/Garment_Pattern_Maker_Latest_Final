"""Audit probes for desired behavior; failures document remaining defects.

Run from backend: python -m pytest ../artifacts/qa/test_gap_audit.py -c pyproject.toml -q
Uses temporary databases. Not included in the normal regression suite.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app

RESULTS = []


@pytest.fixture(scope='session', autouse=True)
def report():
    yield
    Path(__file__).with_name('gap-audit-results.json').write_text(json.dumps(RESULTS, indent=2)+'\n')


@pytest.fixture
def ready(tmp_path):
    with TestClient(create_app(f'sqlite:///{tmp_path}/audit.db')) as client:
        p = client.post('/api/v1/projects', json={'name':'Gap audit','demo':True}).json()
        url = f"/api/v1/projects/{p['id']}"
        for key, value in {'units':'cm','profile':'demo_v1','review':'confirmed','placket':'workbook'}.items():
            assert client.post(f'{url}/requirements/{key}/resolve',json={'value':value}).status_code == 200
        yield client, url


def record(name, **data):
    RESULTS.append({'finding':name, **data})


def test_measurement_route_rejects_unrelated_changes(ready):
    client,url=ready
    response=client.patch(f'{url}/measurements/half_chest',json={'size':'L','changes':{'sleeve_length':-3}})
    row=next(r for r in client.get(url).json()['measurements'] if r['key']=='sleeve_length')
    record('measurement_route_scope_and_range',status=response.status_code,sleeve_length=row['values']['L']['value'])
    assert response.status_code in (400,422)


def test_archived_source_blocks_generation(ready):
    client,url=ready
    project=client.get(url).json()
    document=next(d for d in project['documents'] if d['filename'].endswith('.xlsx'))
    assert client.post(f"{url}/documents/{document['id']}/archive").status_code==200
    check=client.get(f'{url}/requirements').json()
    response=client.post(f'{url}/patterns/generate',json={'size':'L'})
    record('archived_source_readiness',ready=check['ready'],generation_status=response.status_code)
    assert response.status_code==409


def test_import_rejects_invalid_nested_geometry(ready):
    client,url=ready
    pattern=client.post(f'{url}/patterns/generate',json={'size':'L'}).json()
    body={'schema_version':1,'project':'Gap audit','pattern':pattern,
          'grades':[{'size':'M','pieces':[]}], 'marker':{'placements':'invalid'}}
    response=client.post(f'{url}/exports/import',json=body)
    record('nested_import_validation',status=response.status_code,returned_grades=response.json().get('grades'),
           returned_marker=response.json().get('marker'))
    assert response.status_code==422


def test_import_checks_project_exists(ready):
    client,url=ready
    pattern=client.post(f'{url}/patterns/generate',json={'size':'L'}).json()
    response=client.post('/api/v1/projects/nonexistent/exports/import',json={
        'schema_version':1,'project':'Gap audit','pattern':pattern})
    record('import_project_existence',status=response.status_code)
    assert response.status_code==404


def test_version_scoped_grade_uses_requested_version(ready):
    client,url=ready
    old=client.post(f'{url}/patterns/generate',json={'size':'L','allowance':0}).json()
    assert client.post(f'{url}/patterns/generate',json={'size':'L','allowance':2}).status_code==200
    response=client.post(f"{url}/patterns/{old['id']}/grade",json={'sizes':['M']})
    allowances=[p['seam_allowance'] for p in response.json()]
    record('version_scoped_grading',status=response.status_code,requested_allowance=0,result_allowances=allowances)
    assert response.status_code==200
    assert allowances==[0]
