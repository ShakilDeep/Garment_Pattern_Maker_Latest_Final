import pytest

from app.application.commands import execute
from app.application.service import Service
from app.infrastructure.repository import Repository


def test_command_changes_allowance_and_undo_redo_are_new_versions(tmp_path):
    service = Service(Repository(f'sqlite:///{tmp_path}/commands.db'))
    p = service.create('Commands', True)
    p['resolutions'] = {'units': 'cm', 'review': 'confirmed', 'profile': 'demo_v1', 'placket': 'workbook'}
    original = service.generate(p, 'L')
    result = execute(service, p, 'allowance', value=1)
    assert result['pattern']['seam_allowance'] == 1
    assert result['pattern']['id'] != original['id']
    undo = execute(service, result, 'undo')
    assert undo['pattern']['seam_allowance'] == 0
    redo = execute(service, undo, 'redo')
    assert redo['pattern']['seam_allowance'] == 1
    with pytest.raises(ValueError):
        execute(service, redo, 'allowance', value=99)
    assert service.repo.get(p['id'])['pattern']['seam_allowance'] == 1
