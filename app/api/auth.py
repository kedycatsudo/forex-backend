from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel

from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest):
    # TODO: replace with real auth logic
    if payload.email == "admin@example.com" and payload.password == "secret":
        return {"access_token": "demo-token", "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
    )