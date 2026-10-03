from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.import_contract import check_import_contract
from app.api.models.project import GeometryImport
from app.api.schemas import DxfUnit, ExportCreate, JsonImport, Size
from app.application.geometry_import import persist_import
from app.application.state import transition
from app.infrastructure.exports import export_artifact
from app.infrastructure.import_geometry import assert_importable, require_project
from app.infrastructure.repository import now

# Artifact bytes: SVG, PDF, DXF, or the JSON geometry document that /exports/import accepts back.
EXPORT_RESPONSES: dict[int | str, dict] = {200: {
    "model": GeometryImport, "description": "Exported artifact",
    "content": {"image/svg+xml": {}, "application/pdf": {}, "application/dxf": {}},
}}


def artifact_routes(service):
    routes = APIRouter()
    repo = service.repo

    def response(project, kind, size=None, unit='cm'):
        data, mime = export_artifact(project, kind, size=size, unit=unit)
        export_size = size or (project.get('pattern') or {}).get('size') or (project.get('marker') or {}).get('size') or 'M'
        extension = {'marker-svg': 'svg', 'marker-pdf': 'pdf'}.get(kind, kind)
        metadata = {'id': str(uuid4()), 'kind': kind, 'size': export_size,
                    **({'unit': unit} if kind == 'dxf' else {}),
                    'sha256': sha256(data).hexdigest(), 'at': now()}
        project.setdefault('export_records', []).append(metadata)
        # Best-effort state update — never block returning the artifact bytes.
        try:
            transition(project, 'EXPORT_READY', 'export_created')
            repo.save(project, 'export_created', metadata, artifact=(metadata, data))
        except ValueError:
            repo.save(project, 'export_created', metadata, artifact=(metadata, data))
        return Response(data, media_type=mime, headers={
            'Content-Disposition': f'attachment; filename="1078983_shirt_{export_size}_demo.{extension}"'})

    @routes.post('/projects/{pid}/exports', response_class=Response, responses=EXPORT_RESPONSES)
    def create(pid: str, body: ExportCreate):
        return response(repo.get(pid), body.kind, body.size, body.unit)

    @routes.get('/projects/{pid}/exports/{kind}', response_class=Response, responses=EXPORT_RESPONSES)
    def export_file(pid: str, kind: str, size: Size | None = None, unit: DxfUnit = 'cm'):
        return response(repo.get(pid), kind, size, unit)

    @routes.post('/projects/{pid}/exports/import', response_model=GeometryImport)
    def import_json(pid: str, body: JsonImport):
        project = require_project(repo, pid)
        assert_importable(body)
        check_import_contract(body)
        persist_import(service, project, body)
        return {"schema_version": 1, "pattern": project["pattern"], "grades": project["grades"],
                "marker": project["marker"]}

    return routes
