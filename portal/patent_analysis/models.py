"""Pydantic models for patent-analysis."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PatentAnalysisRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PatentAnalysisResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
