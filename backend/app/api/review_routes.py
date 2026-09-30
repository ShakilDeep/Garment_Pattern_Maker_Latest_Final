from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from app.api.schemas import ListResponse, ObjectResponse, RequestModel
from app.application.commands import execute
from app.application.reviews import review, review_status


class ReviewDecision(RequestModel):
    status: Literal['APPROVED_FOR_DEMO', 'REJECTED']
    actor: str = Field(min_length=1, max_length=120)
    note: str = Field(default='', max_length=2000)


class CadCommand(RequestModel):
    command: Literal['allowance', 'fold', 'notch', 'undo', 'redo']
    value: float | None = None
    piece_id: str | None = Field(default=None, max_length=100)


def review_routes(service):
    routes = APIRouter(prefix='/projects/{pid}')

    @routes.get('/reviews', response_model=ListResponse)
    def list_reviews(pid: str):
        return review_status(service.repo.get(pid))

    @routes.post('/commands', response_model=ObjectResponse)
    def command(pid: str, body: CadCommand):
        return execute(service, service.repo.get(pid), **body.model_dump())

    @routes.post('/reviews/{gate}', response_model=ListResponse)
    def decide(pid: str, gate: str, body: ReviewDecision):
        p = service.repo.get(pid)
        result = review(p, gate, body.status, body.actor, body.note)
        service.repo.save(p, 'review_recorded', result)
        return review_status(p)

    return routes
