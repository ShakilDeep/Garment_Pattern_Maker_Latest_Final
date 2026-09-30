import json
from base64 import b64encode
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, event, text

from app.infrastructure.migrations import migrate
from app.infrastructure.projections import put, sync_project
from app.infrastructure.request_context import correlation_id


def now():
    return datetime.now(UTC).isoformat()


class Repository:
    def __init__(self, url):
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        @event.listens_for(self.engine, 'connect')
        def configure(connection, record):
            connection.isolation_level = None
            connection.execute('PRAGMA foreign_keys=ON')

        @event.listens_for(self.engine, 'begin')
        def begin(connection):
            connection.exec_driver_sql('BEGIN')

        with self.engine.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY)"))
            c.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL)"
                )
            )
            c.execute(text("INSERT OR IGNORE INTO schema_versions VALUES (1)"))
            migrate(c)

    def list(self):
        with self.engine.connect() as c:
            rows = []
            for r in c.execute(text("SELECT id,name,updated_at,data FROM projects ORDER BY updated_at DESC")).mappings():
                data = json.loads(r["data"])
                rows.append({
                    "id": r["id"],
                    "name": r["name"],
                    "updated_at": r["updated_at"],
                    "archived": bool(data.get("archived") or data.get("state") == "ARCHIVED"),
                })
            return rows

    def get(self, project_id):
        with self.engine.connect() as c:
            row = c.execute(text("SELECT data FROM projects WHERE id=:id"), {"id": project_id}).first()
            if row is None:
                raise KeyError(project_id)
            return json.loads(row[0])

    def save(self, project, event, details=None, artifact=None):
        project["updated_at"] = now()
        actor = details.get('actor', 'local user') if isinstance(details, dict) else 'local user'
        project["audit"].append({"id": str(uuid4()), "event": event, "at": now(), "details": details,
                                 "actor": actor, "outcome": "success",
                                 "correlation_id": correlation_id.get()})
        with self.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO projects (id,name,data,updated_at) VALUES (:id,:name,:data,:at) ON CONFLICT(id) DO UPDATE SET name=:name,data=:data,updated_at=:at"
                ),
                {
                    "id": project["id"],
                    "name": project["name"],
                    "data": json.dumps(project, allow_nan=False),
                    "at": project["updated_at"],
                },
            )
            sync_project(c, project)
            if artifact:
                metadata, data = artifact
                put(c, 'exports', {"id": metadata['id'], "project_id": project['id'], "kind": metadata['kind'],
                    "path_or_blob_ref": 'base64:' + b64encode(data).decode('ascii'), "sha256": metadata['sha256'],
                    "created_at": metadata['at'], "metadata_json": json.dumps(metadata)}, immutable=True)
        return project

    def delete(self, project_id):
        self.get(project_id)
        with self.engine.begin() as c:
            c.execute(text("DELETE FROM projects WHERE id=:id"), {"id": project_id})
