"""FastAPI routes for patent-analysis."""

from fastapi import APIRouter, HTTPException

from .models import PatentAnalysisRequest, PatentAnalysisResponse

router = APIRouter(prefix="/api/patent-analysis", tags=["patent-analysis"])

SKILL_ID = "patent-analysis"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=PatentAnalysisResponse)
async def run(request: PatentAnalysisRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：专利技术分析 功能尚未实现",
    )
