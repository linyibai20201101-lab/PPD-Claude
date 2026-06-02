"""Pydantic models for leader-analysis."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class LeaderAnalysisRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class LeaderAnalysisResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
