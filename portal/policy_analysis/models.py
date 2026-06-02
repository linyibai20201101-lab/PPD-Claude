"""Pydantic models for policy-analysis."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PolicyAnalysisRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PolicyAnalysisResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
