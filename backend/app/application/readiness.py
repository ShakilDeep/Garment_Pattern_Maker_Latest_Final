"""Operation-specific prerequisites shared by API clients and review screens."""
from app.application.requirements import requirements
from app.domain.catalog import SIZES


def check_operation(project, target_operation, size='L', width=None, quantities=None, grain_policy=None):
    items = []

    def need(key, available, message, source):
        items.append({'key': key, 'name': key.replace('_', ' ').title(),
                      'status': 'AVAILABLE' if available else 'MISSING', 'blocking': True,
                      'why': message, 'source': source, 'question': message,
                      'fallback_policy': 'No automatic default', 'options': []})

    if target_operation in ('generate', 'grade'):
        selected = [size] if target_operation == 'generate' else list(SIZES)
        for selected_size in selected:
            items.extend({**i, 'size': selected_size} for i in requirements(project, selected_size)['items'])
    elif target_operation in ('validate', 'marker', 'export'):
        patterns = {p['size']: p for p in [project.get('pattern'), *project.get('grades', [])] if p}
        selected = list(quantities) if target_operation == 'marker' and quantities else [size]
        for selected_size in selected:
            p = patterns.get(selected_size)
            current = bool(p and not p.get('stale'))
            valid = bool(p) and current and (target_operation == 'validate' or not any(
                v['severity'] == 'ERROR' for v in (p or {}).get('validation', [])))
            need('pattern:' + selected_size, valid,
                 f'Generate a current {selected_size} pattern and resolve geometry errors.', 'Generated patterns')
        if target_operation == 'marker':
            need('width', width is not None and 20 < width <= 500,
                 'Enter fabric width greater than 20 and at most 500 cm.', 'Fabric specification')
            valid_quantities = bool(quantities) and all(
                s in SIZES and type(q) is int and q > 0 for s, q in quantities.items())
            valid_quantities = valid_quantities and sum(quantities.values()) <= 20
            need('quantities', valid_quantities, 'Choose 1 to 20 garments across generated sizes.', 'Cut order')
            need('grain_policy', grain_policy == 'vertical',
                 'Confirm vertical grain with no rotation for this demo.', 'Fabric specification')
    else:
        raise ValueError('Supported operations: generate, grade, validate, marker, export')
    blockers = [i for i in items if i['blocking'] and i['status'] != 'AVAILABLE']
    return {'target_operation': target_operation, 'ready': not blockers, 'items': items,
            'blockers': blockers, 'warnings': [i for i in items if not i['blocking']],
            'next_actions': [i['why'] for i in blockers]}
