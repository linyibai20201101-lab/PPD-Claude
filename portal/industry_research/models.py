"""Pydantic models for industry-research."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class IndustryResearchRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class IndustryResearchResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
