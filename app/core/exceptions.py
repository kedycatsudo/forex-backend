from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(RequestValidationError, exc)

    compact_errors = [
        {
            "loc": e.get("loc"),
            "msg": e.get("msg"),
            "type": e.get("type"),
        }
        for e in err.errors()
    ]

    logger.warning(
        "Request validation failed",
        extra={
            "event": "validation_error",
            "extra": {
                "path": str(request.url.path),
                "method": request.method,
                "errors": compact_errors,
            },
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": compact_errors,
            "request_id": request_id_ctx.get(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception",
        extra={
            "event": "unhandled_exception",
            "extra": {
                "path": str(request.url.path),
                "method": request.method,
            },
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id_ctx.get(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
