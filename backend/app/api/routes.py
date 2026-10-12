from fastapi import APIRouter

from app.api.accuracy_routes import accuracy_routes
from app.api.assistant_routes import assistant_routes
from app.api.cad_routes import cad_routes
from app.api.lifecycle_routes import lifecycle_routes
from app.api.mapping_routes import mapping_routes
from app.api.measurement_routes import measurement_routes
from app.api.pattern_routes import pattern_routes
from app.api.project_routes import project_routes
from app.api.requirement_routes import requirement_routes
from app.api.review_routes import review_routes
from app.api.source_routes import source_routes
from app.api.style_detect_routes import style_detect_routes
from app.application.cad.style_service import StyleService
from app.application.mapping_service import MappingService
from app.application.style_service import StyleDetectService
from app.infrastructure.image_prep import prepare_image
from app.infrastructure.provider_factory import get_pom_suggester, get_style_detector
from app.infrastructure.style_repository import StyleRepository


def router(service, ai_provider=None, pom_suggester=None, style_detector=None):
    routes = APIRouter(prefix="/api/v1")
    for child in (
        project_routes(service),
        source_routes(service),
        measurement_routes(service),
        requirement_routes(service),
        pattern_routes(service),
        accuracy_routes(service),
        review_routes(service),
        lifecycle_routes(service),
        mapping_routes(MappingService(service, pom_suggester or get_pom_suggester())),
        assistant_routes(service, ai_provider),
        style_detect_routes(StyleDetectService(service, style_detector or get_style_detector(), prepare_image)),
        cad_routes(StyleService(StyleRepository(service.repo.engine), service.repo)),
    ):
        routes.include_router(child)
    return routes
