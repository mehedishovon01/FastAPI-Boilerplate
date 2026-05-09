"""Project-wide exception classes and FastAPI exception handlers.

Custom exceptions let services raise errors *without* knowing about
HTTP status codes. The handlers below translate them into clean JSON
responses, so the same exception can be raised from a CLI, worker,
or test without any ``HTTPException`` coupling.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppException(Exception):
    """Base for every domain exception in the project."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "An error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class AlreadyExistsError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication failed."


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class InvalidTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid or expired token."


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error."},
        )
