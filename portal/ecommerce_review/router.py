"""FastAPI routes for ecommerce-review."""

from fastapi import APIRouter, HTTPException

from .models import EcommerceReviewRequest, EcommerceReviewResponse

router = APIRouter(prefix="/api/ecommerce-review", tags=["ecommerce-review"])

SKILL_ID = "ecommerce-review"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=EcommerceReviewResponse)
async def run(request: EcommerceReviewRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：电商产品评论分析 功能尚未实现",
    )
