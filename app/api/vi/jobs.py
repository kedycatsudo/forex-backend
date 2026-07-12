from fastapi import APIRouter, Depends

from app.security.internal_auth import require_internal_api_key

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/retry", dependencies=[Depends(require_internal_api_key)])
async def retry_job() -> dict:
    return {"ok": True}
