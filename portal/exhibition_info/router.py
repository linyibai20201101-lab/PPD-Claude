"""FastAPI routes for exhibition-info."""

from fastapi import APIRouter, HTTPException

from .models import ExhibitionInfoRequest, ExhibitionInfoResponse

router = APIRouter(prefix="/api/exhibition-info", tags=["exhibition-info"])

SKILL_ID = "exhibition-info"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=ExhibitionInfoResponse)
async def run(request: ExhibitionInfoRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：展会信息收集 功能尚未实现",
    )
