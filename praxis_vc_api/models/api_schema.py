"""v0.6 P2:FastAPI pydantic schema。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


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
    model_config = ConfigDict(extra="forbid")

    request: dict[str, Any]
    mode: str = "offline"
    enable_llm_report: bool = False
    pack_id: str | None = None
    pack_version: str | None = None

    @model_validator(mode="after")
    def _complete_pack_identity(self):
        if (self.pack_id is None) != (self.pack_version is None):
            raise ValueError("pack_id and pack_version must be provided together")
        for value in (self.pack_id, self.pack_version):
            if value is not None and (not value or value.strip() != value):
                raise ValueError("Pack identity must be a non-empty trimmed string")
        return self


class PackCompatibilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: dict[str, Any]
    pack_id: str
    pack_version: str

    @model_validator(mode="after")
    def _valid_pack_identity(self):
        for value in (self.pack_id, self.pack_version):
            if not value or value.strip() != value:
                raise ValueError("Pack identity must be a non-empty trimmed string")
        return self


class JobOut(BaseModel):
    job_id: str
    status: str


class HealthOut(BaseModel):
    status: str
    mode: str
    llm_enabled: bool
    product_version: str
    api_protocol_version: str
    runtime_protocol_version: str
    runtime_version: str
    git_sha: str
