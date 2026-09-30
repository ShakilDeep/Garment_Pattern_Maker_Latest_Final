"""Evidence collection from docs 47/101; never a production certification gate."""

CALIBRATION = {
    'base_pattern': ('Approved base pattern', 'Provide the client-approved block for representative sizes.'),
    'drafting': ('Drafting methodology', 'Provide the construction equations and block methodology.'),
    'grading': ('Grading rules', 'Provide client grade points and increments for the supported sizes.'),
    'seams': ('Seam allowance policy', 'Provide seam allowances by piece and edge.'),
    'marks': ('Notch and grainline standards', 'Provide notch, drill, fold and grainline conventions.'),
    'shrinkage': ('Fabric shrinkage policy', 'Provide fabric-specific shrinkage and relaxation allowances.'),
    'marker': ('Production marker constraints', 'Provide width, nap, rotation, matching and spacing policies.'),
    'tolerances': ('Production QA tolerances', 'Provide dimensional and seam acceptance tolerances.'),
    'samples': ('Physical sample results', 'Provide approved finished-sample measurements and fit review.'),
    'export': ('Production export requirements', 'Provide plotter formats and certified export fixtures.'),
}


def calibration_requirements(project):
    sources = {d['id']: d for d in project.get('documents', [])}
    metadata = project.get('resolution_metadata', {})
    items: list[dict] = []
    for suffix, (name, why) in CALIBRATION.items():
        key = 'calibration:' + suffix
        evidence = metadata.get(key, {})
        source = sources.get(evidence.get('source_id'))
        reviewed = (project.get('resolutions', {}).get(key) == 'reviewed' and source is not None
                    and evidence.get('resolution_type') == 'source' and bool(evidence.get('note', '').strip()))
        items.append({'key': key, 'name': name, 'why': why, 'question': why,
                      'category': 'Production calibration', 'status': 'AVAILABLE' if reviewed else 'MISSING',
                      'blocking': False, 'resolved': reviewed, 'value': 'reviewed' if reviewed else None,
                      'source': source.get('filename', 'Client evidence') if source else 'Client evidence required',
                      'confidence': None, 'options': [], 'accepted_units': [],
                      'fallback_policy': 'No demo default; evidence review does not certify production',
                      'resolution': evidence or None})
    return items


def calibration_request(project):
    items = [item for item in calibration_requirements(project) if not item['resolved']]
    lines = ['Production calibration request', f"Project: {project['name']} ({project['id']})",
             f"Drafting profile: {project.get('resolutions', {}).get('profile', 'Not selected')}",
             f"Unresolved evidence requests: {len(items)}", '']
    for item in items:
        lines.extend([f"- {item['name']} [{item['key']}]", f"  {item['why']}"])
    if (project.get('techpack') or {}).get('fabric_conflict'):
        lines.extend(['', 'Source conflict: clarify the inconsistent fabric composition in the tech pack.'])
    if not items:
        lines.append('No unresolved calibration evidence requests remain.')
    lines.extend(['', 'Evidence review does not certify production. Approved rules must still be implemented,',
                  'validated against reference patterns, and verified through physical samples.'])
    return '\n'.join(lines) + '\n'
