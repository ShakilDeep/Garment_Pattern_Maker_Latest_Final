"""Validated V5 CAD commands, dispatched through the PM-05 command bus with a persisted 100-step history."""
from copy import deepcopy
from uuid import uuid4

from app.application.cad.bus import CommandBus
from app.application.cad.history_codec import history_to_data
from app.application.cad.legacy_commands import legacy_registry
from app.application.cad.legacy_history import HISTORY_KEY, load_history
from app.application.cad.legacy_snapshot import LegacySnapshotter
from app.application.service import NotReady
from app.application.state import transition
from app.infrastructure.geometry_adapter import validate

SNAPSHOT_KEYS = ('pattern', 'measurements', 'resolutions')
BUS = CommandBus(legacy_registry(), LegacySnapshotter())


def _edited(state, history, command, value, piece_id):
    if command == 'undo':
        return BUS.undo(state, history)
    if command == 'redo':
        return BUS.redo(state, history)
    return BUS.dispatch(state, history, command, {'value': value, 'piece_id': piece_id})


def execute(service, project, command, value=None, piece_id=None):
    p = deepcopy(project)
    if not p.get('pattern') or p['pattern'].get('stale'):
        raise NotReady('Generate a current pattern before editing')
    old_pattern = deepcopy(p['pattern'])
    state, history = _edited({k: p[k] for k in SNAPSHOT_KEYS}, load_history(p), command, value, piece_id)
    p.update(state)
    p[HISTORY_KEY] = history_to_data(history)
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
