"""Public result contract for estimates made by an LLM from observed omics."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReference(Contract):
    tool_call_id: str
    pointer: str = Field(description="JSON Pointer into the tool result's data")
    source_id: str
    value: Any = Field(description="Exact value copied from that pointer")


class Observation(Contract):
    gene_id: str | None = None
    field: str
    value: Any
    evidence_ref: EvidenceReference


class EvidenceItem(Contract):
    claim: str
    observations: list[Observation] = Field(default_factory=list)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class MICEstimate(Contract):
    value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    unit: Literal["ug/mL"] = "ug/mL"
    basis: Literal["llm_estimate"] = "llm_estimate"
    reason: str
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)

    @field_validator("value", mode="before")
    @classmethod
    def require_numeric_estimate(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("MIC must be a positive finite number or null")
        return value


class Confidence(Contract):
    level: Literal["low", "medium", "high"] = "low"
    calibrated: Literal[False] = False


class TargetHypothesis(Contract):
    name: str
    target_id: str | None = None
    hypothesis: str
    status: Literal["hypothesis"] = "hypothesis"
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    counterevidence_refs: list[EvidenceReference] = Field(default_factory=list)


class MechanismHypothesis(Contract):
    hypothesis: str
    status: Literal["hypothesis"] = "hypothesis"
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)
    counterevidence_refs: list[EvidenceReference] = Field(default_factory=list)


class Assessment(Contract):
    activity: Literal["likely_active", "likely_inactive", "uncertain"]
    mic_estimate: MICEstimate
    confidence: Confidence = Field(default_factory=Confidence)
    killing_effect: Literal["unknown"] = "unknown"
    targets: list[TargetHypothesis] = Field(default_factory=list, max_length=10)
    mechanism_hypotheses: list[MechanismHypothesis] = Field(default_factory=list, max_length=10)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list, max_length=30)
    counterevidence: list[EvidenceItem] = Field(default_factory=list, max_length=30)
    gaps: list[str] = Field(default_factory=list, max_length=30)
    rationale_summary: str


def empty_assessment(reason: str) -> dict[str, Any]:
    return Assessment(
        activity="uncertain",
        mic_estimate=MICEstimate(value=None, reason=reason),
        gaps=[reason],
        rationale_summary=reason,
    ).model_dump()
