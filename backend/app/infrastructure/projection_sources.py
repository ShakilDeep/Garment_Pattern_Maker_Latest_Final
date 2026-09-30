"""Project sources, measurements and tech-pack attributes into normalized tables."""
from sqlalchemy import text

from app.infrastructure.projection_sql import encoded, put


def sync_sources(c, p):
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
