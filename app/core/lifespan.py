from fastapi import FastAPI

from app.core.logging import get_logger

logger = get_logger(__name__)


def register_lifecycle_events(app: FastAPI) -> None:
    """
    Register startup/shutdown hooks.
    """

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Application startup", extra={"event": "app_startup"})

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Application shutdown", extra={"event": "app_shutdown"})
