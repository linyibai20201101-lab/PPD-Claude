"""Pydantic models for competitor-benchmark."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class CompetitorBenchmarkRequest(BaseModel):
    input_text: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class CompetitorBenchmarkResponse(BaseModel):
    status: str
    message: str
    result: Optional[str] = None
