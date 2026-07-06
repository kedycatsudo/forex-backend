from __future__ import annotations
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.security_settings import get_security_settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        settings=get_security_settings()

        #Baseline hardening headers
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Frame-Options"]="DENY" # or SAMEORIGIN if needed
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Permissions-Policy"]="geolocation=(), microphone=(), camera=()"

        #For API-only services, keep CSP minimal (mostly relevant for HTML response)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        
        #Enable HSTS only in prod/HTTPS deployments
        #(Do not set in plain local HTTP environments)
        if settings.ENV=="prod":
            response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
        
        
        return response