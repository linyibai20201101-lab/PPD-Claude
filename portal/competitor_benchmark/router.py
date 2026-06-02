"""FastAPI routes for competitor-benchmark."""

from fastapi import APIRouter, HTTPException

from .models import CompetitorBenchmarkRequest, CompetitorBenchmarkResponse

router = APIRouter(prefix="/api/competitor-benchmark", tags=["competitor-benchmark"])

SKILL_ID = "competitor-benchmark"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=CompetitorBenchmarkResponse)
async def run(request: CompetitorBenchmarkRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：竞品跑分表对比分析 功能尚未实现",
    )
