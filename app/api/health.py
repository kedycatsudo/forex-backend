import os
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)

APP_NAME = os.getenv("APP_NAME", "forex-backend")
APP_ENV = os.getenv("APP_ENV", "development")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@router.get("/live")
@limiter.limit("60/minute")
async def health_live(request: Request) -> dict:
    return {
        "status": "ok",
        "service": APP_NAME,
        "env": APP_ENV,
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
@limiter.limit("60/minute")
async def health_ready(request: Request, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception(
            "Database readiness check failed",
            extra={"event": "health_ready_db_failed"},
        )
        checks["database"] = "fail"

    redis_client = None
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.warning(
            "Redis readiness check failed",
            extra={"event": "health_ready_redis_failed"},
        )
        checks["redis"] = "fail"
    finally:
        if redis_client is not None:
            await redis_client.aclose()

    is_ready = checks.get("database") == "ok"
    return JSONResponse(
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if is_ready else "not_ready", "checks": checks},
    )
