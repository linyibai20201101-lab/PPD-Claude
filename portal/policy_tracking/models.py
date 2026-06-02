"""Pydantic models for policy-tracking."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PolicyTrackingRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class PolicyTrackingResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
