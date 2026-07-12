from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status

from app.core.logging import get_logger, request_id_ctx
from app.core.security_settings import get_security_settings

logger = get_logger(__name__)


def _get_client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()

    xrip = request.headers.get("x-real-ip")
    if xrip:
        return xrip.strip()

    if request.client:
        return request.client.host

    return None


def _log_auth_failure(request: Request, reason: str) -> None:
    logger.warning(
        "Internal API key auth failed",
        extra={
            "event": "auth_failed_internal_key",
            "extra": {
                "reason": reason,  # missing_key | invalid_key
                "path": request.url.path,
                "method": request.method,
                "client_ip": _get_client_ip(request),
                "request_id": request_id_ctx.get(),
            },
        },
    )


def require_internal_api_key(request: Request) -> None:
    settings = get_security_settings()

    provided_key = request.headers.get("X-Internal-API-Key")
    expected_key = settings.INTERNAL_API_KEY

    if not provided_key:
        _log_auth_failure(request, "missing_key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing internal API key",
        )

    if not expected_key:
        logger.error(
            "Internal API key auth misconfigured",
            extra={
                "event": "auth_misconfigured_internal_key",
                "extra": {
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": _get_client_ip(request),
                    "request_id": request_id_ctx.get(),
                },
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal auth unavailable",
        )

    # Constant-time comparison (secure)
    if not hmac.compare_digest(provided_key, expected_key):
        _log_auth_failure(request, "invalid_key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )
