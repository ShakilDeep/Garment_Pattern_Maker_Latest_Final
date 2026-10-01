"""Map domain and framework exceptions to the stable V5 error envelope."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.assistant_contracts import AssistantFailure
from app.application.errors import NotReady, Unprocessable


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


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AssistantFailure)
    async def assistant_failure(request, exc):
        return error(request, exc.status_code, exc.code, str(exc))

    @app.exception_handler(Unprocessable)
    async def unprocessable(request, exc):
        return error(request, 422, exc.code, str(exc))

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
