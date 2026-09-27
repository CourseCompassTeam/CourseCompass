"""Standard API error envelope.

Every error response has this shape:

    {"error": {"code": "...", "message": "...", "details": {}}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

# HTTP status -> error code, per the Detailed Design.
BAD_REQUEST = (400, 'BAD_REQUEST')  # Request or tool input failed validation.
UNAUTHORIZED = (401, 'UNAUTHORIZED')  # Missing or invalid/expired session.
FORBIDDEN = (403, 'FORBIDDEN')  # Token valid, resource not owned by student.
NOT_FOUND = (404, 'NOT_FOUND')  # Student, course, or job does not exist.
# A fact could not be confirmed against the course dataset (QA-02 redirect).
UNPROCESSABLE_CONTENT = (422, 'UNPROCESSABLE_CONTENT')
TOO_MANY_REQUESTS = (429, 'TOO_MANY_REQUESTS')  # Rate limit exceeded.
INTERNAL_ERROR = (500, 'INTERNAL_ERROR')  # Unhandled server-side failure.
NOT_IMPLEMENTED = (501, 'NOT_IMPLEMENTED')  # Skeleton stub not wired yet.


class ApiError(Exception):
    """An error that is returned to the client in the standard envelope.

    Attributes:
        status: HTTP status code.
        code: Error code string, e.g. 'NOT_FOUND'.
        message: Human-readable message.
        details: Optional extra information.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_body(code: str, message: str,
               details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Builds the standard error JSON object.

    Args:
        code: Machine-readable error code.
        message: Human-readable message.
        details: Optional extra fields.

    Returns:
        The envelope under the top-level ``error`` key.
    """
    return {
        'error': {
            'code': code,
            'message': message,
            'details': details or {},
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Registers ApiError and fallback handlers on the app.

    Args:
        app: The FastAPI application.
    """

    @app.exception_handler(ApiError)
    async def _handle_api_error(
        _request: Request, exc: ApiError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(NotImplementedError)
    async def _handle_not_implemented(
        _request: Request, exc: NotImplementedError
    ) -> JSONResponse:
        message = str(exc) or 'This endpoint is not implemented yet.'
        status, code = NOT_IMPLEMENTED
        return JSONResponse(
            status_code=status,
            content=error_body(code, message),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        status, code = INTERNAL_ERROR
        return JSONResponse(
            status_code=status,
            content=error_body(
                code,
                'An unexpected error occurred.',
                {'type': type(exc).__name__},
            ),
        )
