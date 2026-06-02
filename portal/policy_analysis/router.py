"""FastAPI routes for policy-analysis."""

from fastapi import APIRouter, HTTPException

from .models import PolicyAnalysisRequest, PolicyAnalysisResponse

router = APIRouter(prefix="/api/policy-analysis", tags=["policy-analysis"])

SKILL_ID = "policy-analysis"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=PolicyAnalysisResponse)
async def run(request: PolicyAnalysisRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：政策分析 功能尚未实现",
    )
