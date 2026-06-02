"""Pydantic models for product-design."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProductDesignRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ProductDesignResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
