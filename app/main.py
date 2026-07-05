from fastapi import FastAPI
from app.core.logging import configure_logging, get_logger
from app.core.request_id import RequestIdMiddleware
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import register_lifecycle_events
from app.api.health import router as health_router
from app.api.internal.routes import router as internal_router
from app.core.security_settings import get_security_settings


configure_logging()
logger = get_logger(__name__)

app = FastAPI()
app.include_router(health_router)
app.include_router(internal_router)
app.add_middleware(RequestIdMiddleware)

register_exception_handlers(app)
register_lifecycle_events(app)

@app.on_event("startup")
async def debug_settings_startup() -> None:
    s = get_security_settings()
    print("INTERNAL_API_KEY loaded:", bool(s.INTERNAL_API_KEY))

@app.get("/health/live")
async def live():
    logger.info("Liveness check", extra={"event": "health_live"})
    return {"status": "ok"}