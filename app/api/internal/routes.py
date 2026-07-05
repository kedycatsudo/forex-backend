from fastapi import APIRouter, Depends
from app.security.internal_auth import require_internal_api_key

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_internal_api_key)],
)

@router.post("/workers/trigger")
async def trigger_worker()->dict:
    return {"ok":True}