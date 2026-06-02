"""FastAPI routes for tech-advancement."""

from fastapi import APIRouter, HTTPException

from .models import TechAdvancementRequest, TechAdvancementResponse

router = APIRouter(prefix="/api/tech-advancement", tags=["tech-advancement"])

SKILL_ID = "tech-advancement"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=TechAdvancementResponse)
async def run(request: TechAdvancementRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：技术先进性检索 功能尚未实现",
    )
