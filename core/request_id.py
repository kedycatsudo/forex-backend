import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import request_id_ctx

Request_ID_HEADER= "X- Request-ID"

class RequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request:Request, call_next):
        incoming_request_id=request.headers.get(Request_ID_HEADER)
        request_id=incoming_request_id or str(uuid.uuid4())

        #Set request_id in contextvar for this request scope
        token = request_id_ctx.set(request_id)
        
        try:
            response: Response=await call_next(request)
        
        finally:
            #Always reset context to avoid leaking between requests

            request_id_ctx.reset(token)
            
        response.headers[Request_ID_HEADER]=request_id
        return response