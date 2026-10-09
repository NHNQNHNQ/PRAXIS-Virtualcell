"""v0.6 P2:FastAPI pydantic schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.model_zoo.adapter_sdk import _contains_rooted_local_path


class ParseIn(BaseModel):
    text: str
    mode: str = "offline"  # offline / llm_assisted


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
    submission_contract: Literal[
        "vc.virtual-experiment-compilation.v1",
        "vc.direct-v2-execution.v1",
    ] = "vc.virtual-experiment-compilation.v1"

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


class ResearchTaskDescriptor(BaseModel):
    """Strict public identity for one explicitly configured research task."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["vc.research-task.v1"]
    task_id: str
    request: VirtualCellRequestV2
    pack_id: str
    pack_version: str
    model_name: str
    model_version: str
    execution_scope: Literal["research_only"]
    scientifically_validated: Literal[False]

    @field_validator(
        "task_id",
        "pack_id",
        "pack_version",
        "model_name",
        "model_version",
        mode="before",
    )
    @classmethod
    def _path_safe_identifier(cls, value):
        if (
            not isinstance(value, str)
            or not value
            or value.strip() != value
            or not value[0].isalnum()
            or any(not (character.isalnum() or character in "._@+-") for character in value)
        ):
            raise ValueError("research task identifiers must be canonical and path-safe")
        return value

    @field_validator("request", mode="before")
    @classmethod
    def _canonical_request(cls, value):
        if isinstance(value, VirtualCellRequestV2):
            return VirtualCellRequestV2.from_dict(value.to_dict())
        if not isinstance(value, dict):
            raise ValueError("research task request must be an exact vc.request.v2")
        try:
            request = VirtualCellRequestV2.from_dict(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("research task request must be an exact vc.request.v2") from exc
        if request.to_dict() != value:
            raise ValueError("research task request must use its canonical vc.request.v2 form")
        return request

    @model_validator(mode="after")
    def _exact_path_free_request(self):
        payload = self.model_dump(mode="json")
        if _contains_rooted_local_path(payload) or _contains_parent_traversal(payload):
            raise ValueError("research task descriptor must not contain rooted local paths")
        return self


class ResearchTaskExecutionIn(BaseModel):
    """Bind task execution to the exact compatibility preview the user confirmed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    compatibility_fingerprint: str

    @field_validator("compatibility_fingerprint")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("compatibility_fingerprint must be a lowercase SHA-256")
        return value


def _contains_parent_traversal(value: Any) -> bool:
    if isinstance(value, str):
        return ".." in value.replace("\\", "/").split("/")
    if isinstance(value, dict):
        return any(_contains_parent_traversal(key) or _contains_parent_traversal(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_parent_traversal(item) for item in value)
    return False


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
