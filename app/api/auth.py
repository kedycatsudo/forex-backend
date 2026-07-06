from fastapi import APIRouter, Request, HTTPException, status
from app.schemas.auth import LoginRequest

from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest):
    if payload.email== "admin@example.com" and payload.password.get_secret_value()== "secret123":
        return {"access_token":"demo-token", "token-type":"bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )