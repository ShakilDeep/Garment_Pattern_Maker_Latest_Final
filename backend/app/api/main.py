import json
import logging
import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.artifact_routes import artifact_routes
from app.api.routes import router
from app.application.assistant_contracts import AssistantFailure
from app.application.service import NotReady, Service
from app.infrastructure.repository import Repository
from app.infrastructure.request_context import correlation_id
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

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.correlation_id = str(uuid4())
        token = correlation_id.set(request.state.correlation_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            duration = time.perf_counter() - started
            response.headers["X-Request-ID"] = request.state.correlation_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
            )
            logging.getLogger("garment").info(json.dumps({
                "request_id": request.state.correlation_id,
                "method": request.method,
                "path": request.url.path,
                "project_id": request.path_params.get('pid'),
                "use_case": request.url.path.rsplit('/', 1)[-1] or request.method,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "outcome": "success" if response.status_code < 400 else "error",
            }))
            return response
        finally:
            correlation_id.reset(token)

    def error(request, status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "details": details,
                "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            },
        )

    @app.exception_handler(AssistantFailure)
    async def assistant_failure(request, exc):
        return error(request, exc.status_code, exc.code, str(exc))

    @app.exception_handler(NotReady)
    async def not_ready(request, exc):
        text = str(exc)
        code = 'MEASUREMENT_MISSING' if 'measurement' in text.lower() else 'REQUIREMENTS_NOT_READY'
        return error(request, 409, code, text)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        text = str(exc)
        lowered = text.lower()
        code = 'GEOMETRY_SELF_INTERSECTION' if 'intersect' in lowered else 'MEASUREMENT_INVALID' if 'measurement' in lowered else 'INPUT_INVALID'
        return error(request, 400, code, text)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return error(request, 404, "NOT_FOUND", "The requested project or record was not found")

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "REQUEST_ERROR", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(request, 422, "REQUEST_INVALID", "Check the supplied fields, sizes, and numeric ranges")

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger("garment").exception(
            "Unhandled request error",
            extra={"request_id": getattr(request.state, "correlation_id", "unknown")},
        )
        return error(request, 500, "INTERNAL_ERROR", "The server could not complete this request")

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
