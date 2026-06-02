"""FastAPI routes for leader-analysis."""

from fastapi import APIRouter, HTTPException

from .models import LeaderAnalysisRequest, LeaderAnalysisResponse

router = APIRouter(prefix="/api/leader-analysis", tags=["leader-analysis"])

SKILL_ID = "leader-analysis"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=LeaderAnalysisResponse)
async def run(request: LeaderAnalysisRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：龙头分析 功能尚未实现",
    )
