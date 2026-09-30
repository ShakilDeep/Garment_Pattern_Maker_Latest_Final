import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.artifact_routes import artifact_routes
from app.api.error_handlers import install_error_handlers
from app.api.middleware import install_request_log
from app.api.routes import router
from app.application.service import Service
from app.infrastructure.repository import Repository
from app.ports.ai_provider import AIProvider


def create_app(database_url=None, *, ai_provider: AIProvider | None = None):
    app = FastAPI(title="Garment Pattern Maker V5", version="0.1.0")
    db_url = database_url or os.getenv("DATABASE_URL") or "sqlite:///garment.db"
    repository = Repository(db_url)
    service = Service(repository)
    app.include_router(router(service, ai_provider))
    app.include_router(artifact_routes(service), prefix='/api/v1')
    origins = [origin.strip() for origin in os.getenv(
        'FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    install_request_log(app)
    install_error_handlers(app)

    @app.get("/health")
    def health():
        from sqlalchemy import text

        with repository.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "profile": "demo_v1", "database": "ok"}

    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
