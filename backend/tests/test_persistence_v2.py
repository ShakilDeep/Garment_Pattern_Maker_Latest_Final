import json
import sqlite3

from sqlalchemy import text

from app.application.service import Service
from app.infrastructure.repository import Repository


def test_v2_migration_adds_measurement_confidence_and_preserves_snapshots(tmp_path):
    from app.infrastructure.migrations import SCHEMA

    path = tmp_path / 'v2.db'
    p = {'id': 'old', 'name': 'Retained', 'updated_at': '2026-01-01',
         'documents': [], 'measurements': [], 'audit': [], 'resolutions': {}}
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE schema_versions (version INTEGER PRIMARY KEY)')
        c.execute('INSERT INTO schema_versions VALUES (2)')
        c.execute('CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, data TEXT, updated_at TEXT)')
        c.execute('INSERT INTO projects VALUES (?,?,?,?)', ('old', p['name'], json.dumps(p), p['updated_at']))
        for name, definition in SCHEMA.items():
            c.execute(f'CREATE TABLE {name} ({definition})')
    for _ in range(2):
        repo = Repository(f'sqlite:///{path}')
        assert repo.get('old') == p
        with repo.engine.connect() as c:
            assert 'confidence' in [r[1] for r in c.execute(text('PRAGMA table_info(measurements)'))]
            assert c.execute(text('SELECT max(version) FROM schema_versions')).scalar() == 3
        repo.engine.dispose()


def test_migration_preserves_existing_project_and_is_repeatable(tmp_path):
    path = tmp_path / 'legacy.db'
    p = {'id': 'legacy', 'name': 'Keep me', 'updated_at': '2026-01-01',
         'state': 'CREATED', 'documents': [], 'measurements': [], 'audit': [],
         'pattern': None, 'grades': [], 'resolutions': {}}
    with sqlite3.connect(path) as c:
        c.execute('CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, data TEXT, updated_at TEXT)')
        c.execute('INSERT INTO projects VALUES (?,?,?,?)', ('legacy', p['name'], json.dumps(p), p['updated_at']))
    for _ in range(2):
        repo = Repository(f'sqlite:///{path}')
        assert repo.get('legacy')['name'] == 'Keep me'
        with repo.engine.connect() as c:
            assert c.execute(text('SELECT max(version) FROM schema_versions')).scalar() >= 2
            assert c.execute(text('PRAGMA foreign_keys')).scalar() == 1
        repo.engine.dispose()


def test_normalized_rows_versions_and_cascade(tmp_path):
    repo = Repository(f'sqlite:///{tmp_path}/project.db')
    service = Service(repo)
    p = service.create('Demo', True)
    p['resolutions'] = {'units': 'cm', 'review': 'confirmed', 'profile': 'demo_v1', 'placket': 'workbook'}
    first = service.generate(p, 'L')
    second = service.generate(p, 'M')
    with repo.engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM source_artifacts')).scalar() == 2
        assert c.execute(text('SELECT count(*) FROM measurements')).scalar() == 35
        assert c.execute(text('SELECT count(*) FROM measurement_values')).scalar() == 210
        assert c.execute(text('SELECT count(*) FROM pattern_sets')).scalar() == 2
        assert c.execute(text('SELECT count(*) FROM pattern_pieces')).scalar() == 16
        assert c.execute(text('SELECT count(*) FROM audit_events')).scalar() == len(p['audit'])
    assert first['id'] != second['id']
    repo.delete(p['id'])
    with repo.engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM measurement_values')).scalar() == 0
        assert c.execute(text('SELECT count(*) FROM pattern_sets')).scalar() == 0
