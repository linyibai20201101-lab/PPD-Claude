"""FastAPI routes for product-design."""

from fastapi import APIRouter, HTTPException

from .models import ProductDesignRequest, ProductDesignResponse

router = APIRouter(prefix="/api/product-design", tags=["product-design"])

SKILL_ID = "product-design"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=ProductDesignResponse)
async def run(request: ProductDesignRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：产品设计 功能尚未实现",
    )
