"""Pydantic models for planning-review."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PlanningReviewRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PlanningReviewResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
