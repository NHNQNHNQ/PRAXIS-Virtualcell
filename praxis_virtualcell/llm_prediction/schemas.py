"""Public result contract for estimates made by an LLM from observed omics."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MICConditions(Contract):
    """Requested MIC assay conditions, independent of reference omics sampling."""
    medium: str | None = None
    medium_supplements: list[str] | None = None
    temperature_c: float | None = Field(default=None, allow_inf_nan=False)
    exposure_hours: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    method: str | None = None
    inoculum: str | None = None

    @field_validator("temperature_c", "exposure_hours", mode="before")
    @classmethod
    def numeric_conditions(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("assay conditions require finite numeric values or null")
        return value


class MICObservation(Contract):
    """An estimated conditional MIC observation; censoring remains explicit."""
    relation: Literal["=", "<", "<=", ">", ">=", "interval"]
    value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    lower: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    upper: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    lower_closed: bool = True
    upper_closed: bool = True

    @field_validator("value", "lower", "upper", mode="before")
    @classmethod
    def numeric_values(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise ValueError("MIC observations require finite numbers or null")
        return value

    @model_validator(mode="after")
    def consistent_bounds(self):
        if self.relation == "interval":
            if self.value is not None or self.lower is None or self.upper is None or self.lower >= self.upper:
                raise ValueError("an interval requires increasing bounds and no point value")
            return self
        if self.value is None:
            raise ValueError("a scalar relation requires a MIC value")
        lower = self.value if self.relation in {"=", ">", ">="} else None
        upper = self.value if self.relation in {"=", "<", "<="} else None
        if self.lower != lower or self.upper != upper:
            raise ValueError("MIC bounds must match the relation and value")
        if self.lower_closed != (self.relation != ">") or self.upper_closed != (self.relation != "<"):
            raise ValueError("MIC open/closed bounds must match the relation")
        return self


class MechanismSource(Contract):
    doi: str = Field(min_length=1)
    locator_id: str = Field(min_length=1)


class MechanismClaim(Contract):
    statement: str = Field(min_length=1)
    evidence_grade: Literal["experimental", "genetic", "author_proposed", "class_background", "unresolved"]
    experiment_type: str = Field(min_length=1)
    target_names: list[str] = Field(default_factory=list)
    mechanism_role: Literal["drug_target", "resistance_mechanism", "activity_modifier", "unresolved"]
    scope: str = Field(min_length=1)
    sources: list[MechanismSource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


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


class StructureHypothesis(Contract):
    """A hypothesis grounded in one returned structure, without upgrading its scope."""
    structure_id: str = Field(min_length=1)
    compartment: str = Field(min_length=1)
    evidence_scope: Literal["species_prior", "strain_evidence"]
    evidence_type: Literal["reference_knowledge", "source_annotation", "measured"]
    protein_id: str | None = Field(default=None, min_length=1)
    protein_namespace: str | None = Field(default=None, min_length=1)
    hypothesis: str = Field(min_length=1)
    status: Literal["hypothesis"] = "hypothesis"
    evidence_refs: list[EvidenceReference] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def paired_native_protein_identity(self):
        if (self.protein_id is None) != (self.protein_namespace is None):
            raise ValueError("protein localization requires both native protein ID and namespace")
        return self


class AccessibilityBarrier(StructureHypothesis):
    accessibility: Literal["unknown", "potentially_accessible", "potential_barrier"] = "unknown"


class StructureAnalysis(Contract):
    compartment_hypotheses: list[StructureHypothesis] = Field(default_factory=list, max_length=20)
    accessibility_barriers: list[AccessibilityBarrier] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=30)


class Assessment(Contract):
    activity: Literal["likely_active", "likely_inactive", "uncertain"]
    mic_estimate: MICEstimate
    mic_observations: list[MICObservation] = Field(default_factory=list, max_length=100)
    mechanism_claims: list[MechanismClaim] = Field(default_factory=list, max_length=30)
    mechanism_limitations: list[str] = Field(default_factory=list, max_length=30)
    structure_analysis: StructureAnalysis | None = None
    confidence: Confidence = Field(default_factory=Confidence)
    killing_effect: Literal["unknown"] = "unknown"
    targets: list[TargetHypothesis] = Field(default_factory=list, max_length=10)
    mechanism_hypotheses: list[MechanismHypothesis] = Field(default_factory=list, max_length=10)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list, max_length=30)
    counterevidence: list[EvidenceItem] = Field(default_factory=list, max_length=30)
    gaps: list[str] = Field(default_factory=list, max_length=30)
    rationale_summary: str

    @model_validator(mode="after")
    def point_estimate_preserves_observations(self):
        if self.mic_observations and self.mic_estimate.value is not None:
            if any(row.relation != "=" or row.value != self.mic_estimate.value for row in self.mic_observations):
                raise ValueError("a point MIC requires all observations to be exact and equal; retain censoring and heterogeneity")
        return self


def empty_assessment(reason: str) -> dict[str, Any]:
    return Assessment(
        activity="uncertain",
        mic_estimate=MICEstimate(value=None, reason=reason),
        gaps=[reason],
        rationale_summary=reason,
    ).model_dump()
