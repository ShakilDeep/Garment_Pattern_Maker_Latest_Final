from fastapi import APIRouter
from pydantic import Field

from app.api.schemas import ObjectResponse, RequestModel, Size
from app.application.assistant import execute, propose
from app.infrastructure.provider_factory import get_ai_provider


class AssistantPrompt(RequestModel):
    prompt: str = Field(min_length=1, max_length=1000)
    size: Size = "L"
    piece_id: str | None = Field(default=None, min_length=1, max_length=100)


class AssistantExecute(RequestModel):
    proposal_id: str = Field(min_length=1, max_length=100)
    confirmed: bool = False


def assistant_routes(service, provider=None):
    provider = provider if provider is not None else get_ai_provider()
    routes = APIRouter(prefix="/projects/{pid}/assistant")

    @routes.post("/propose", response_model=ObjectResponse)
    def create_proposal(pid: str, body: AssistantPrompt):
        return propose(service, service.repo.get(pid), provider, body.prompt, body.size, body.piece_id)

    @routes.post("/execute", response_model=ObjectResponse)
    def execute_proposal(pid: str, body: AssistantExecute):
        return execute(service, service.repo.get(pid), body.proposal_id, body.confirmed)

    return routes
