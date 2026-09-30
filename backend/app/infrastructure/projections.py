"""Normalized, transactionally synchronized storage alongside compatibility snapshots."""
import json
from hashlib import sha256

from sqlalchemy import text

from app.application.requirements import requirements


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False)


def put(c, table, values, immutable=False):
    columns = list(values)
    placeholders = ','.join(':' + k for k in columns)
    action = 'DO NOTHING' if immutable else 'DO UPDATE SET ' + ','.join(
        f'{k}=excluded.{k}' for k in columns if k != 'id')
    c.execute(text(f'INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders}) '
                   f'ON CONFLICT(id) {action}'), values)


def sync_project(c, p):
    pid, at = p['id'], p.get('updated_at', '')
    sources = {}
    for d in p.get('documents', []):
        sources[d['filename']] = d['id']
        put(c, 'source_artifacts', {'id': d['id'], 'project_id': pid, 'filename': d['filename'],
            'artifact_type': d['filename'].rsplit('.', 1)[-1], 'checksum': d['sha256'],
            'parser_version': d.get('parser_version', 'legacy'), 'imported_at': d.get('imported_at', at)})
    c.execute(text('DELETE FROM measurements WHERE project_id=:id'), {'id': pid})
    for index, row in enumerate(p.get('measurements', [])):
        rid = f'{pid}:measurement:{index}'
        tolerance = row.get('tolerance')
        tolerance = tolerance if isinstance(tolerance, (int, float)) else None
        put(c, 'measurements', {'id': rid, 'project_id': pid, 'code': row['code'], 'canonical_key': row['key'],
            'label': row['label'], 'unit': row['unit'], 'tolerance_plus': tolerance, 'tolerance_minus': tolerance,
            'confidence': row.get('confidence'),
            'source_document_id': sources.get(row.get('source')), 'provenance_json': encoded(
                {k: v for k, v in row.items() if k != 'values'})})
        for size, cell in row['values'].items():
            put(c, 'measurement_values', {'id': f'{rid}:{size}', 'measurement_id': rid, 'size_code': size,
                'value': cell.get('value'), 'formula_text': cell.get('formula'),
                'is_user_override': int(cell.get('override', False)), 'raw_value_json': encoded(cell.get('raw')),
                'issue': cell.get('issue')})
    c.execute(text('DELETE FROM tech_attributes WHERE project_id=:id'), {'id': pid})
    tech = p.get('techpack') or {}
    for key, value in tech.items():
        if key in ('pages', 'source'):
            continue
        if key == 'attributes' and isinstance(value, list):
            for attribute in value:
                put(c, 'tech_attributes', {'id': f"{pid}:tech:{attribute.get('key')}", 'project_id': pid,
                    'category': attribute.get('category', 'techpack'), 'key': attribute.get('key', 'unknown'),
                    'value_json': encoded(attribute.get('value')), 'source_document_id': sources.get(tech.get('source')),
                    'confidence': attribute.get('confidence'), 'provenance_json': encoded(attribute)})
            continue
        put(c, 'tech_attributes', {'id': f'{pid}:tech:{key}', 'project_id': pid, 'category': 'techpack',
            'key': key, 'value_json': encoded(value), 'source_document_id': sources.get(tech.get('source')),
            'confidence': None,
            'provenance_json': encoded({'parser': tech.get('parser')})})
    patterns = [*p.get('pattern_history', []), p.get('pattern'), *p.get('grades', [])]
    for pattern in patterns:
        if not pattern:
            continue
        ident = pattern['id']
        put(c, 'pattern_sets', {'id': ident, 'project_id': pid, 'base_size': pattern['size'],
            'rule_version': pattern['profile'], 'input_hash': pattern['input_hash'],
            'validation_status': 'ERROR' if any(v['severity'] == 'ERROR' for v in pattern['validation']) else 'NEEDS_REVIEW',
            'created_at': pattern.get('created_at', at), 'snapshot_json': encoded(pattern)}, immutable=True)
        for piece in pattern['pieces']:
            put(c, 'pattern_pieces', {'id': f'{ident}:{piece["id"]}', 'pattern_set_id': ident, 'name': piece['name'],
                'size_code': pattern['size'], 'cut_quantity': piece['quantity'], 'geometry_json': encoded(piece),
                'metadata_json': encoded({'profile': pattern['profile']})}, immutable=True)
        for i, issue in enumerate(pattern['validation']):
            put(c, 'validation_results', {'id': f'{ident}:validation:{i}', 'pattern_set_id': ident,
                'severity': issue['severity'], 'code': issue['code'], 'message': issue['message'],
                'details_json': encoded(issue)})
    for marker in [p.get('previous_marker'), p.get('marker')]:
        if marker:
            ident = sha256(encoded(marker).encode()).hexdigest()
            put(c, 'markers', {'id': f'{pid}:{ident}', 'project_id': pid, 'fabric_width': marker['width'],
                'strategy': marker['strategy'], 'utilization': marker['utilization'], 'waste': marker['waste'],
                'geometry_json': encoded(marker), 'created_at': at}, immutable=True)
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
