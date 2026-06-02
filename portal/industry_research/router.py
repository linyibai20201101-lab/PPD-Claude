"""FastAPI routes for industry-research."""

from fastapi import APIRouter, HTTPException

from .models import IndustryResearchRequest, IndustryResearchResponse

router = APIRouter(prefix="/api/industry-research", tags=["industry-research"])

SKILL_ID = "industry-research"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=IndustryResearchResponse)
async def run(request: IndustryResearchRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：行业调研 功能尚未实现",
    )
