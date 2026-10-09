from fastapi import APIRouter

from app.api.models.mapping import ChartView, MappingChoice, MappingSuggestion
from app.api.models.project import Project
from app.application.mapping_service import MappingService


def mapping_routes(mappings: MappingService):
    routes = APIRouter(prefix="/projects/{pid}")

    @routes.get("/chart", response_model=ChartView)
    def chart(pid: str):
        return mappings.chart(pid)

    @routes.post("/mappings/suggest", response_model=list[MappingSuggestion])
    def suggest(pid: str):
        return mappings.suggest(pid)

    @routes.post("/mappings/{row}", response_model=Project)
    def choose(pid: str, row: int, body: MappingChoice):
        return mappings.confirm(pid, row, body.key)

    return routes
