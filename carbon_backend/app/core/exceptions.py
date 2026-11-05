"""Domain errors raised by services; translated to HTTP responses in one place.

Services stay free of FastAPI imports, and every error body keeps the `{"detail": "..."}` shape
that the Flutter and web clients already parse.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from routing.service import RoutingError


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BusinessRuleError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class InvalidInputError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


async def _app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


async def _routing_error_handler(_request: Request, exc: RoutingError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RoutingError, _routing_error_handler)
