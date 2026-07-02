"""v0.6 P2:FastAPI pydantic schema。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParseIn(BaseModel):
    text: str
    mode: str = "offline"           # offline / llm_assisted


class ParseOut(BaseModel):
    candidate_request: dict[str, Any]
    schema_valid: bool
    missing_fields: list[str]
    errors: list[str] = []
    clarification_required: bool
    parser: str
    llm_used: bool
    fallback_used: bool
    assumptions: list[str] = []
    llm_metadata: dict[str, Any] = {}


class JobIn(BaseModel):
    request: dict[str, Any]
    mode: str = "offline"
    enable_llm_report: bool = False


class JobOut(BaseModel):
    job_id: str
    status: str


class HealthOut(BaseModel):
    status: str
    mode: str
    llm_enabled: bool
    runtime_version: str
