"""Project immutable pattern versions, pieces, validation results and markers."""
from hashlib import sha256

from app.infrastructure.projection_sql import encoded, put


def sync_patterns(c, p):
    pid, at = p['id'], p.get('updated_at', '')
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
