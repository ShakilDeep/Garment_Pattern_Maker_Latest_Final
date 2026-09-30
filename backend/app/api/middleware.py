"""Request middleware: correlation ids, security headers and structured timing logs."""
import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from app.infrastructure.request_context import correlation_id

CONTENT_SECURITY_POLICY = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"


def _log_request(request: Request, status: int, duration: float) -> None:
    logging.getLogger("garment").info(json.dumps({
        "request_id": request.state.correlation_id,
        "method": request.method,
        "path": request.url.path,
        "project_id": request.path_params.get('pid'),
        "use_case": request.url.path.rsplit('/', 1)[-1] or request.method,
        "status": status,
        "duration_ms": round(duration * 1000, 2),
        "outcome": "success" if status < 400 else "error",
    }))


def install_request_log(app: FastAPI) -> None:
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
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
            _log_request(request, response.status_code, duration)
            return response
        finally:
            correlation_id.reset(token)
