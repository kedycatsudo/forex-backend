from fastapi import FastAPI
from app.core.logging import configure_logging, get_logger
from app.core.request_id import RequestIdMiddleware
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import register_lifecycle_events
from app.api.health import router as health_router
configure_logging()
logger = get_logger(__name__)

app = FastAPI()
app.include_router(health_router)
app.add_middleware(RequestIdMiddleware)

register_exception_handlers(app)
register_lifecycle_events(app)

@app.get("/health/live")
async def live():
    logger.info("Liveness check", extra={"event": "health_live"})
    return {"status": "ok"}