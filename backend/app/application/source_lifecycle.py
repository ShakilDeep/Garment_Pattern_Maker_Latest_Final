"""Commands: archive or restore a source document; either invalidates work drafted from the old inputs."""
from app.application.requirements import requirements
from app.application.state import ALLOWED, transition

ARCHIVED_ISSUE = 'Source archived; review or replace this value before generation'


def _document(p, document_id):
    document = next((d for d in p.get('documents', []) if d['id'] == document_id), None)
    if document is None:
        raise KeyError(document_id)
    return document


def _source_cells(p, document_id):
    return [cell for row in p.get('measurements', []) if row.get('source_id') == document_id
            for cell in row.get('values', {}).values()]


def _settle(service, p, reason):
    service.invalidate(p)
    target = 'MEASUREMENTS_READY' if requirements(p)['ready'] else 'NEEDS_INPUT'
    if target in ALLOWED.get(p.get('state', 'CREATED'), set()):
        transition(p, target, reason)


def archive_document(service, p, document_id):
    service._ensure_active(p)
    document = _document(p, document_id)
    if not document.get('active', True):
        return p
    document['active'] = False
    for cell in _source_cells(p, document_id):
        cell['issue'] = ARCHIVED_ISSUE
    _settle(service, p, 'source_archived')
    return service.repo.save(p, 'document_archived', {'document_id': document_id})


def restore_document(service, p, document_id):
    service._ensure_active(p)
    document = _document(p, document_id)
    if document.get('active', True):
        return p
    document['active'] = True
    for cell in _source_cells(p, document_id):
        if cell.get('issue') == ARCHIVED_ISSUE:
            cell['issue'] = None
    _settle(service, p, 'source_restored')
    return service.repo.save(p, 'document_restored', {'document_id': document_id})
