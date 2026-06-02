"""Pydantic models for ecommerce-review."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class EcommerceReviewRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class EcommerceReviewResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
