"""Pydantic models for tech-advancement."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class TechAdvancementRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class TechAdvancementResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
