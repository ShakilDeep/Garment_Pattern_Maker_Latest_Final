"""Project requirements, audit events and reviews."""
from app.application.requirements import requirements
from app.infrastructure.projection_sql import encoded, put


def sync_workflow(c, p):
    pid, at = p['id'], p.get('updated_at', '')
    for item in requirements(p)['items']:
        key = item['key']
        meta = p.get('resolution_metadata', {}).get(key, {})
        put(c, 'project_requirements', {'id': f'{pid}:{key}', 'project_id': pid, 'key': key,
            'category': item.get('category', 'Measurements' if key.startswith('measurement:') else 'Review'),
            'status': item['status'], 'blocking': int(item['blocking']), 'value_json': encoded(item['value']),
            'unit': 'cm' if key.startswith('measurement:') else None, 'source_id': meta.get('source_id'),
            'confidence': None, 'resolution_type': meta.get('resolution_type'), 'resolution_note': meta.get('note'),
            'created_at': meta.get('at', at), 'updated_at': at})
    for event in p.get('audit', []):
        put(c, 'audit_events', {'id': event['id'], 'project_id': pid, 'event_type': event['event'],
            'actor': event.get('actor', 'local user'), 'created_at': event['at'], 'details_json': encoded(event.get('details'))},
            immutable=True)
        details = event.get('details')
        if event['event'] == 'requirement_resolved' and isinstance(details, dict):
            put(c, 'requirement_events', {'id': event['id'], 'requirement_id': f'{pid}:{details["key"]}',
                'event_type': event['event'], 'old_value_json': encoded(details.get('old_value')),
                'new_value_json': encoded(details.get('value')), 'actor': event.get('actor', 'local user'),
                'metadata_json': encoded(details), 'created_at': event['at']}, immutable=True)
    for review in p.get('reviews', []):
        put(c, 'reviews', {**{k: review[k] for k in ('id', 'gate', 'status', 'actor', 'note', 'fingerprint')},
            'project_id': pid, 'created_at': review['at'], 'warnings_json': encoded(review['warnings'])})
