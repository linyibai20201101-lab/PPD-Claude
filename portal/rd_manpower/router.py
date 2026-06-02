"""FastAPI routes for rd-manpower."""

from fastapi import APIRouter, HTTPException

from .models import RdManpowerRequest, RdManpowerResponse

router = APIRouter(prefix="/api/rd-manpower", tags=["rd-manpower"])

SKILL_ID = "rd-manpower"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=RdManpowerResponse)
async def run(request: RdManpowerRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：研发人力评估 功能尚未实现",
    )
