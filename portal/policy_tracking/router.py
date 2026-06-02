"""FastAPI routes for policy-tracking."""

from fastapi import APIRouter, HTTPException

from .models import PolicyTrackingRequest, PolicyTrackingResponse

router = APIRouter(prefix="/api/policy-tracking", tags=["policy-tracking"])

SKILL_ID = "policy-tracking"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=PolicyTrackingResponse)
async def run(request: PolicyTrackingRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：政策追踪分析 功能尚未实现",
    )
