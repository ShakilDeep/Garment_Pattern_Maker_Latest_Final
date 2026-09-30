"""Validated CAD commands and independent snapshot history."""
from copy import deepcopy
from uuid import uuid4

from app.application.service import NotReady
from app.application.state import transition
from app.infrastructure.geometry_adapter import apply_allowance, validate


def snapshot(p):
    return deepcopy({k: p[k] for k in ('pattern', 'measurements', 'resolutions')})


def execute(service, project, command, value=None, piece_id=None):
    p = deepcopy(project)
    if not p.get('pattern') or p['pattern'].get('stale'):
        raise NotReady('Generate a current pattern before editing')
    previous = snapshot(p)
    old_pattern = deepcopy(p['pattern'])
    if command in ('undo', 'redo'):
        source, destination = ('command_undo', 'command_redo') if command == 'undo' else ('command_redo', 'command_undo')
        if not p.get(source):
            raise NotReady(f'Nothing to {command}')
        p.setdefault(destination, []).append(previous)
        p.update(p[source].pop())
    elif command == 'allowance':
        if value is None or not 0 <= value <= 3:
            raise ValueError('Seam allowance must be between 0 and 3 cm')
        apply_allowance(p['pattern'], value)
    elif command in ('fold', 'notch'):
        piece = next((v for v in p['pattern']['pieces'] if v['id'] == piece_id), None)
        if piece is None:
            raise ValueError('Select a generated piece')
        if command == 'fold':
            if piece['name'] not in ('Back', 'Yoke') or value not in (0, 1):
                raise ValueError('Fold annotation is supported only for Back and Yoke')
            piece['cut_on_fold'] = bool(value)
        else:
            if value is None or not 0 <= value < 1:
                raise ValueError('Notch position must be a fraction from 0 to below 1')
            points = piece['points']
            piece['notches'] = [points[int(value * (len(points) - 1))]]
    else:
        raise ValueError('Unsupported CAD command')
    if command not in ('undo', 'redo'):
        p.setdefault('command_undo', []).append(previous)
        p['command_undo'] = p['command_undo'][-20:]
        p['command_redo'] = []
    pattern = p['pattern']
    pattern['validation'] = validate(pattern)
    if any(v['severity'] == 'ERROR' for v in pattern['validation']):
        raise ValueError('Edited geometry failed validation')
    pattern['id'] = str(uuid4())
    pattern['parent_id'] = old_pattern['id']
    pattern['command'] = {'name': command, 'value': value, 'piece_id': piece_id}
    p.setdefault('pattern_history', []).append(old_pattern)
    p['grades'] = []
    p['marker'] = p['previous_marker'] = None
    transition(p, 'PATTERN_NEEDS_REVIEW', 'cad_command')
    return service.repo.save(p, 'cad_command', pattern['command'])
