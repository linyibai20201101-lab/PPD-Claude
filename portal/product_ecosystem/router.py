"""FastAPI routes for product-ecosystem."""

from fastapi import APIRouter, HTTPException

from .models import ProductEcosystemRequest, ProductEcosystemResponse

router = APIRouter(prefix="/api/product-ecosystem", tags=["product-ecosystem"])

SKILL_ID = "product-ecosystem"


@router.get("/status")
async def status():
    return {
        "status": "scaffold",
        "skill": SKILL_ID,
        "message": "骨架阶段，业务逻辑尚未实现",
    }


@router.post("/run", response_model=ProductEcosystemResponse)
async def run(request: ProductEcosystemRequest):
    raise HTTPException(
        status_code=501,
        detail="骨架阶段：产品生态全景 功能尚未实现",
    )
