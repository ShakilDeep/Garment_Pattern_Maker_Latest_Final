from fastapi import APIRouter

from app.api.schemas import ObjectResponse


def lifecycle_routes(service):
    routes = APIRouter()
    repo = service.repo

    @routes.post('/projects/{pid}/archive', response_model=ObjectResponse)
    def archive_project(pid: str):
        p = repo.get(pid)
        p['archived'] = True
        p['state'] = 'ARCHIVED'
        return repo.save(p, 'project_archived')

    @routes.post('/projects/{pid}/restore', response_model=ObjectResponse)
    def restore_project(pid: str):
        p = repo.get(pid)
        p['archived'] = False
        if p.get('state') == 'ARCHIVED':
            p['state'] = 'CREATED' if not p.get('pattern') else 'PATTERN_NEEDS_REVIEW'
        return repo.save(p, 'project_restored')

    @routes.post('/projects/{pid}/documents/{document_id}/archive', response_model=ObjectResponse)
    def archive_document(pid: str, document_id: str):
        p = repo.get(pid)
        document = next((d for d in p.get('documents', []) if d['id'] == document_id), None)
        if document is None:
            raise KeyError(document_id)
        document['active'] = False
        for row in p.get('measurements', []):
            if row.get('source_id') == document_id:
                for cell in row.get('values', {}).values():
                    cell['issue'] = 'Source archived; review or replace this value before generation'
        service.invalidate(p)
        return repo.save(p, 'document_archived', {'document_id': document_id})

    @routes.post('/projects/{pid}/documents/{document_id}/restore', response_model=ObjectResponse)
    def restore_document(pid: str, document_id: str):
        p = repo.get(pid)
        document = next((d for d in p.get('documents', []) if d['id'] == document_id), None)
        if document is None:
            raise KeyError(document_id)
        document['active'] = True
        for row in p.get('measurements', []):
            if row.get('source_id') == document_id:
                for cell in row.get('values', {}).values():
                    if cell.get('issue') == 'Source archived; review or replace this value before generation':
                        cell['issue'] = None
        return repo.save(p, 'document_restored', {'document_id': document_id})

    return routes
