from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.internal.routes import router as internal_router
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import register_lifecycle_events
from app.core.rate_limit import limiter
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import rate_limit_exceeded_handler
from app.core.request_id import RequestIdMiddleware
from app.core.security_settings import get_security_settings

configure_logging()
logger = get_logger(__name__)
settings = get_security_settings()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info(
        "Security settings loaded",
        extra={
            "event": "security_settings_loaded",
            "extra": {
                "env": settings.ENV,
                "docs_enabled": settings.DOCS_ENABLED,
                "internal_api_key_loaded": bool(settings.INTERNAL_API_KEY),
                "cors_allowed_origins": settings.cors_allowed_origins_list,
                "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
            },
        },
    )
    yield


async def _rate_limit_handler_adapter(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, RateLimitExceeded):
        return await rate_limit_exceeded_handler(request, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


app = FastAPI(
    lifespan=app_lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

# make limiter available to slowapi internals
limiter.enabled = settings.RATE_LIMIT_ENABLED
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler_adapter)

# CORS: strict explicit allowlist, env-driven
if settings.ENV != "local" and not settings.cors_allowed_origins_list:
    raise RuntimeError("CORS_ALLOWED_ORIGINS must be set in non-local environments")

if settings.CORS_ALLOW_CREDENTIALS and "*" in settings.cors_allowed_origins_list:
    raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*' when credentials are enabled")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.cors_allowed_methods_list,
    allow_headers=settings.cors_allowed_headers_list,
    expose_headers=settings.cors_expose_headers_list,
    max_age=settings.CORS_MAX_AGE,
)

app.add_middleware(RequestIdMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(internal_router)

register_exception_handlers(app)
register_lifecycle_events(app)