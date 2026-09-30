"""Specification: archived sources block generation readiness."""


def source_blockers(project):
    items = []
    for document in project.get("documents", []):
        if document.get("active", True):
            continue
        items.append(
            {
                "key": f"source:{document['id']}",
                "name": f"Archived source {document.get('filename', document['id'])}",
                "status": "MISSING",
                "blocking": True,
                "why": "Restore or replace this source before generation.",
                "options": ["restore"],
                "resolved": False,
                "value": None,
            }
        )
    return items
