from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.logging import get_logger,request_id_ctx

logger=get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
async def rate_limit_exceeded_handler(request: Request, exc:RateLimitExceeded):
    logger.warning(
        "Rate limit exceeded",
        extra={
            "event":{
                "path":request.url.path,
                "method":request.method,
                "client_ip":request.client.host
if request.client else None, "request_id":
request_id_ctx.get(),"detail":str(exc.detail),
            },
        },
    )
    return JSONResponse(
        status_code=429,
        content={"detail":"Too Many Requests"},
    )