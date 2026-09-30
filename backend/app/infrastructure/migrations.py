"""Additive SQLite migrations. Legacy snapshots remain recoverable."""
import json

from sqlalchemy import text

SCHEMA = {
    'source_artifacts': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        filename TEXT NOT NULL, artifact_type TEXT, checksum TEXT, parser_version TEXT, imported_at TEXT''',
    'measurements': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        code TEXT, canonical_key TEXT, label TEXT, unit TEXT, tolerance_plus REAL, tolerance_minus REAL,
        source_document_id TEXT REFERENCES source_artifacts(id), provenance_json TEXT''',
    'measurement_values': '''id TEXT PRIMARY KEY, measurement_id TEXT NOT NULL REFERENCES measurements(id)
        ON DELETE CASCADE, size_code TEXT NOT NULL, value REAL, formula_text TEXT, is_user_override INTEGER,
        raw_value_json TEXT, issue TEXT, UNIQUE(measurement_id, size_code)''',
    'tech_attributes': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        category TEXT, key TEXT, value_json TEXT, source_document_id TEXT REFERENCES source_artifacts(id),
        confidence REAL, provenance_json TEXT''',
    'pattern_sets': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        base_size TEXT, rule_version TEXT, input_hash TEXT, validation_status TEXT, created_at TEXT,
        snapshot_json TEXT NOT NULL''',
    'pattern_pieces': '''id TEXT PRIMARY KEY, pattern_set_id TEXT NOT NULL REFERENCES pattern_sets(id)
        ON DELETE CASCADE, name TEXT, size_code TEXT, cut_quantity INTEGER, geometry_json TEXT, metadata_json TEXT''',
    'validation_results': '''id TEXT PRIMARY KEY, pattern_set_id TEXT NOT NULL REFERENCES pattern_sets(id)
        ON DELETE CASCADE, severity TEXT, code TEXT, message TEXT, details_json TEXT''',
    'markers': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        fabric_width REAL, strategy TEXT, utilization REAL, waste REAL, geometry_json TEXT, created_at TEXT''',
    'exports': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        kind TEXT, path_or_blob_ref TEXT, sha256 TEXT, created_at TEXT, metadata_json TEXT''',
    'project_requirements': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        key TEXT, category TEXT, status TEXT, blocking INTEGER, value_json TEXT, unit TEXT, source_id TEXT,
        confidence REAL, resolution_type TEXT, resolution_note TEXT, created_at TEXT, updated_at TEXT''',
    'requirement_events': '''id TEXT PRIMARY KEY, requirement_id TEXT NOT NULL REFERENCES project_requirements(id)
        ON DELETE CASCADE, event_type TEXT, old_value_json TEXT, new_value_json TEXT, actor TEXT,
        metadata_json TEXT, created_at TEXT''',
    'audit_events': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        event_type TEXT, actor TEXT, created_at TEXT, details_json TEXT''',
    'reviews': '''id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        gate TEXT, status TEXT, actor TEXT, created_at TEXT, note TEXT, fingerprint TEXT, warnings_json TEXT''',
}


def migrate(connection):
    from app.infrastructure.projections import sync_project

    version = connection.execute(text('SELECT max(version) FROM schema_versions')).scalar() or 0
    if version > 3:
        raise RuntimeError('Database is newer than this application; upgrade the application')
    if version == 3:
        return
    for name, definition in SCHEMA.items():
        connection.execute(text(f'CREATE TABLE IF NOT EXISTS {name} ({definition})'))
    existing_columns = {row[1] for row in connection.execute(text('PRAGMA table_info(measurements)'))}
    if 'confidence' not in existing_columns:
        connection.execute(text('ALTER TABLE measurements ADD COLUMN confidence REAL'))
    for table, columns in [('project_requirements', 'project_id,status'),
                           ('project_requirements', 'project_id,category'),
                           ('requirement_events', 'requirement_id,created_at')]:
        connection.execute(text(f'CREATE INDEX IF NOT EXISTS ix_{table}_{columns.replace(",", "_")} '
                                f'ON {table} ({columns})'))
    for row in connection.execute(text('SELECT data FROM projects')).fetchall():
        sync_project(connection, json.loads(row[0]))
    connection.execute(text('INSERT OR IGNORE INTO schema_versions VALUES (2)'))
    connection.execute(text('INSERT INTO schema_versions VALUES (3)'))
