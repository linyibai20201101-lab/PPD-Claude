"""Pydantic models for prospectus-analysis."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ProspectusAnalysisRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ProspectusAnalysisResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
