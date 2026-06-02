"""FastAPI routes for planning-review."""

from fastapi import APIRouter, HTTPException

from .models import PlanningReviewRequest, PlanningReviewResponse

router = APIRouter(prefix="/api/planning-review", tags=["planning-review"])

SKILL_ID = "planning-review"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=PlanningReviewResponse)
async def run(request: PlanningReviewRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：企划内容审核 功能尚未实现",
    )
