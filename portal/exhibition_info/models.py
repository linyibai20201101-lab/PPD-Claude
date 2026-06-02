"""Pydantic models for exhibition-info."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ExhibitionInfoRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ExhibitionInfoResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
