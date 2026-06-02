"""Pydantic models for rd-manpower."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class RdManpowerRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class RdManpowerResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
