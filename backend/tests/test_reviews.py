import pytest

from app.application.reviews import review, review_status
from app.application.service import NotReady, Service
from app.infrastructure.repository import Repository


def test_review_guards_and_supersession(tmp_path):
    service = Service(Repository(f'sqlite:///{tmp_path}/reviews.db'))
    p = service.create('Reviews', True)
    with pytest.raises(NotReady):
        review(p, 'pattern', 'APPROVED_FOR_DEMO', 'Reviewer', '')
    review(p, 'sources', 'APPROVED_FOR_DEMO', 'Reviewer', 'Source text checked')
    review(p, 'measurements', 'APPROVED_FOR_DEMO', 'Reviewer', 'All sizes checked')
    assert review_status(p)[1]['status'] == 'APPROVED_FOR_DEMO'
    service.update_measurements(p, {'half_chest': 59}, 'L')
    statuses = review_status(p)
    assert statuses[0]['status'] == 'APPROVED_FOR_DEMO'
    assert statuses[1]['status'] == 'SUPERSEDED'


def test_review_persists_actor_and_rejection(tmp_path):
    repo = Repository(f'sqlite:///{tmp_path}/reviews.db')
    p = Service(repo).create('Review', True)
    review(p, 'sources', 'REJECTED', 'Pattern reviewer', 'Check composition conflict')
    repo.save(p, 'review_recorded')
    item = review_status(repo.get(p['id']))[0]
    assert item['status'] == 'REJECTED'
    assert item['actor'] == 'Pattern reviewer'
    assert item['note'] == 'Check composition conflict'
