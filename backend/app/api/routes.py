from fastapi import APIRouter

from app.api.assistant_routes import assistant_routes
from app.api.lifecycle_routes import lifecycle_routes
from app.api.measurement_routes import measurement_routes
from app.api.pattern_routes import pattern_routes
from app.api.project_routes import project_routes
from app.api.requirement_routes import requirement_routes
from app.api.review_routes import review_routes
from app.api.source_routes import source_routes


def router(service, ai_provider=None):
    routes = APIRouter(prefix="/api/v1")
    for child in (
        project_routes(service),
        source_routes(service),
        measurement_routes(service),
        requirement_routes(service),
        pattern_routes(service),
        review_routes(service),
        lifecycle_routes(service),
        assistant_routes(service, ai_provider),
    ):
        routes.include_router(child)
    return routes
