"""Human review of versioned inputs and outputs; never production certification."""
import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from app.application.requirements import requirements
from app.application.service import NotReady
from app.application.state import transition

GATES = ('sources', 'measurements', 'requirements', 'pattern', 'marker', 'export')


def fingerprint(p, gate):
    values = [p.get('documents', []), p.get('techpack'), p.get('measurements', []),
              p.get('resolutions', {}), [p.get('pattern'), p.get('grades', [])],
              p.get('marker'), p.get('export_records', [])]
    last = {'sources': 2, 'measurements': 3, 'requirements': 4, 'pattern': 5, 'marker': 6, 'export': 7}[gate]
    return sha256(json.dumps(values[:last], sort_keys=True, allow_nan=False).encode()).hexdigest()


def review_status(p):
    result = []
    for gate in GATES:
        latest = next((r for r in reversed(p.get('reviews', [])) if r['gate'] == gate), None)
        state = {**latest} if latest else {'gate': gate, 'status': 'NEEDS_REVIEW', 'note': '', 'actor': None, 'at': None}
        if latest and latest['fingerprint'] != fingerprint(p, gate):
            state['status'] = 'SUPERSEDED'
        result.append(state)
    return result


def review(p, gate, status, actor, note):
    if gate not in GATES or status not in ('APPROVED_FOR_DEMO', 'REJECTED'):
        raise ValueError('Choose a supported review gate and decision')
    if not actor.strip():
        raise ValueError('Enter the reviewer name')
    if status == 'APPROVED_FOR_DEMO':
        previous = review_status(p)[:GATES.index(gate)]
        if any(r['status'] != 'APPROVED_FOR_DEMO' for r in previous):
            raise NotReady('Approve the earlier review gates first')
        available = {'sources': bool(p.get('documents') or p.get('measurements')),
                     'measurements': bool(p.get('measurements')),
                     'requirements': requirements(p)['ready'],
                     'pattern': bool(p.get('pattern') and not p['pattern'].get('stale')),
                     'marker': bool(p.get('marker')), 'export': bool(p.get('export_records'))}
        if not available[gate]:
            raise NotReady(f'Complete {gate} before approving its review')
        if gate in ('pattern', 'marker', 'export') and any(
                v['severity'] == 'ERROR' for v in p['pattern']['validation']):
            raise NotReady('Resolve geometry errors before approving')
    warnings = [v for v in (p.get('pattern') or {}).get('validation', []) if v['severity'] == 'WARNING']
    item = {'id': str(uuid4()), 'gate': gate, 'status': status, 'actor': actor.strip(), 'note': note,
                'fingerprint': fingerprint(p, gate), 'at': datetime.now(UTC).isoformat(), 'warnings': warnings}
    p.setdefault('reviews', []).append(item)
    if gate == 'export' and status == 'APPROVED_FOR_DEMO':
        transition(p, 'DEMO_COMPLETE', 'export_approved', actor.strip())
    elif gate == 'pattern' and status == 'APPROVED_FOR_DEMO':
        transition(p, 'PATTERN_READY', 'pattern_approved', actor.strip())
    return item
