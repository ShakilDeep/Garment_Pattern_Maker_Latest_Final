"""Command: persist an explicit requirement resolution with provenance."""
from datetime import UTC, datetime

from app.application.block_inputs import ACCEPTED, REFERENCE_KEY
from app.application.calibration import CALIBRATION
from app.application.unit_conversion import apply_workbook_unit
from app.domain.blocks.base import NamedBlock
from app.domain.blocks.registry import installed


def resolve(project, key, value, note='', actor='local user', source_id=None, resolution_type='manual'):
    allowed = {
        "units": ["cm", "inch"],
        "profile": list(installed().project_ids()),
        "review": ["confirmed"],
        "placket": ["workbook", "techpack"],
        "base_size": list((project.get("chart") or {}).get("sizes", [])),
    }
    profile = project["resolutions"].get("profile")
    if profile in installed().ids() and isinstance(installed().get(profile), NamedBlock):
        allowed[REFERENCE_KEY] = [ACCEPTED]
    if key.startswith('calibration:') and key.removeprefix('calibration:') in CALIBRATION:
        if resolution_type != 'source' or source_id is None or not note.strip() or not actor.strip():
            raise ValueError('Calibration review requires source evidence, a reviewer and a review note')
        allowed[key] = ['reviewed']
    if resolution_type == 'not_applicable':
        if key not in {'fabric'}:
            raise ValueError('This requirement cannot be marked not applicable')
        allowed[key] = [value]
    if key not in allowed or value not in allowed[key]:
        raise ValueError("Unsupported requirement resolution")
    if source_id is not None and not any(d['id'] == source_id for d in project['documents']):
        raise ValueError('Select a source from this project')
    if resolution_type == 'source' and source_id is None:
        raise ValueError('Choose the supporting source artifact')
    if resolution_type == 'approved_default' and key != 'profile':
        raise ValueError('No demo default is defined for this requirement')
    project.setdefault('resolution_metadata', {})[key] = {
        'old_value': project['resolutions'].get(key), 'note': note, 'actor': actor,
        'source_id': source_id, 'resolution_type': resolution_type, 'at': datetime.now(UTC).isoformat()}
    project["resolutions"][key] = value
    if key == "units":
        apply_workbook_unit(project, value)
    return project
