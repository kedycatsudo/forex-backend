# app/core/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_ctx

Request_ID_HEADER = "X-Request-ID"

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_request_id = request.headers.get(Request_ID_HEADER)
        request_id = incoming_request_id or str(uuid.uuid4())

        token = request_id_ctx.set(request_id)
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            request_id_ctx.reset(token)
            if response is not None:
                response.headers[Request_ID_HEADER] = request_id
