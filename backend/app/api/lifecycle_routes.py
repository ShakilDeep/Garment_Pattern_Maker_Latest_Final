from fastapi import APIRouter

from app.api.models.project import Project
from app.application.source_lifecycle import archive_document as archive_source
from app.application.source_lifecycle import restore_document as restore_source


def lifecycle_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.post('/projects/{pid}/archive', response_model=Project)
    def archive_project(pid: str):
        p = repo.get(pid)
        p['archived'] = True
        p['state'] = 'ARCHIVED'
        return repo.save(p, 'project_archived')

    @routes.post('/projects/{pid}/restore', response_model=Project)
    def restore_project(pid: str):
        p = repo.get(pid)
        p['archived'] = False
        if p.get('state') == 'ARCHIVED':
            p['state'] = 'CREATED' if not p.get('pattern') else 'PATTERN_NEEDS_REVIEW'
        return repo.save(p, 'project_restored')

    @routes.post('/projects/{pid}/documents/{document_id}/archive', response_model=Project)
    def archive_document(pid: str, document_id: str):
        return archive_source(service, repo.get(pid), document_id)

    @routes.post('/projects/{pid}/documents/{document_id}/restore', response_model=Project)
    def restore_document(pid: str, document_id: str):
        return restore_source(service, repo.get(pid), document_id)

    return routes
