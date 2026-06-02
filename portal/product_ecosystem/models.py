"""Pydantic models for product-ecosystem."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProductEcosystemRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ProductEcosystemResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
