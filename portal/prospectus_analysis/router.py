"""FastAPI routes for prospectus-analysis."""

from fastapi import APIRouter, HTTPException

from .models import ProspectusAnalysisRequest, ProspectusAnalysisResponse

router = APIRouter(prefix="/api/prospectus-analysis", tags=["prospectus-analysis"])

SKILL_ID = "prospectus-analysis"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=ProspectusAnalysisResponse)
async def run(request: ProspectusAnalysisRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：招股书分析 功能尚未实现",
    )
