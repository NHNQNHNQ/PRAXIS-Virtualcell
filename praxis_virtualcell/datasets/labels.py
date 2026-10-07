"""Experimental supervision contracts kept separate from inference inputs."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class RawMeasurement(StrictRecord):
    value: str
    unit: str
    relation: str
    upper_value: str | None = None


class EndpointLabel(StrictRecord):
    """Censoring is part of a measurement, never an exact-value substitute."""
    kind: Literal["MIC", "growth_inhibition", "target_binding", "MBC", "timekill"]
    relation: Literal["=", "<", "<=", ">", ">=", "interval"]
    unit: str = Field(min_length=1)
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    lower_closed: bool = True
    upper_closed: bool = True
    raw: RawMeasurement
    conversion: str = Field(min_length=1)

    @field_validator("value", "lower", "upper", mode="before")
    @classmethod
    def numeric_values(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int))):
            raise ValueError("endpoint values must be finite numbers, not strings or booleans")
        return value

    @model_validator(mode="after")
    def bounds_follow_relation(self):
        if self.kind in {"MIC", "MBC", "target_binding"}:
            if any(v is not None and v <= 0 for v in (self.value, self.lower, self.upper)):
                raise ValueError("concentration endpoints require positive measurements")
        if self.relation == "interval":
            if self.value is not None or self.lower is None or self.upper is None or self.lower >= self.upper:
                raise ValueError("an interval requires two increasing bounds and no exact value")
            return self
        if self.value is None:
            raise ValueError("a scalar endpoint requires a measurement value")
        lower = self.value if self.relation in {"=", ">", ">="} else None
        upper = self.value if self.relation in {"=", "<", "<="} else None
        if self.lower is not None and self.lower != lower or self.upper is not None and self.upper != upper:
            raise ValueError("bounds contradict the measurement relation")
        self.lower, self.upper = lower, upper
        self.lower_closed = self.relation != ">"
        self.upper_closed = self.relation != "<"
        return self

    @property
    def censoring(self) -> str:
        return {"=": "exact", "<": "left", "<=": "left", ">": "right", ">=": "right",
                "interval": "interval"}[self.relation]


class MoleculeIdentity(StrictRecord):
    source_molecule_id: str = Field(min_length=1)
    source_parent_id: str | None = None
    canonical_smiles: str = Field(min_length=1)
    identity_key: str = Field(min_length=1)
    tested_form: Literal["source_record_structure", "verified_tested_form"] = "source_record_structure"


class OrganismIdentity(StrictRecord):
    species: str = Field(min_length=1)
    taxon_id: int | None = None
    isolate_id: str | None = None
    strain: str | None = None
    strain_namespace: str | None = None
    native_strain_label: str | None = None
    identity_evidence: Literal["structured_assay_strain", "explicit_assay_description", "unresolved", "conflicting"]


class AssayConditions(StrictRecord):
    medium: str | None = None
    medium_supplements: list[str] | None = None
    temperature_c: float | None = None
    exposure_hours: float | None = Field(default=None, gt=0)
    method: str | None = None
    inoculum: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)


class SourceEvidence(StrictRecord):
    source_id: str = Field(min_length=1)
    origin: Literal["experimental_database", "publication", "model_prediction", "synthetic", "unverified"]
    reported_as_measured: bool
    measured_qualifier: str = Field(min_length=1)
    native_locator: dict[str, Any]
    activity_id: str | None = None
    assay_id: str | None = None
    document_id: str | None = None
    doi: str | None = None
    license: str | None = None


class OmicsPairing(StrictRecord):
    status: Literal["unpaired", "same_strain_reference", "matched_isolate_and_condition"] = "unpaired"
    profile_ids: list[str] = Field(default_factory=list)
    isolate_evidence_source_ids: list[str] = Field(default_factory=list)
    condition_evidence_source_ids: list[str] = Field(default_factory=list)


class Admission(StrictRecord):
    label_eligible: bool = False
    paired_omics_eligible: bool = False
    reasons: list[str] = Field(min_length=1)


class ExperimentRecord(StrictRecord):
    schema_version: Literal["praxis.experiment.v1"] = "praxis.experiment.v1"
    record_id: str = Field(min_length=1)
    molecule: MoleculeIdentity
    organism: OrganismIdentity
    conditions: AssayConditions
    endpoint: EndpointLabel
    source: SourceEvidence
    pairing: OmicsPairing = Field(default_factory=OmicsPairing)
    admission: Admission

    @model_validator(mode="after")
    def admission_is_evidence_bound(self):
        if self.admission.label_eligible and (
            not self.source.reported_as_measured
            or self.source.origin not in {"experimental_database", "publication"}
            or not self.source.native_locator
        ):
            raise ValueError("prediction, synthetic or untraceable records cannot be experimental labels")
        if self.admission.paired_omics_eligible:
            if (not self.admission.label_eligible
                    or self.organism.identity_evidence in {"unresolved", "conflicting"}
                    or self.pairing.status != "matched_isolate_and_condition"
                    or not self.pairing.profile_ids
                    or not self.pairing.isolate_evidence_source_ids
                    or not self.pairing.condition_evidence_source_ids):
                raise ValueError("omics pairing requires explicit isolate and condition evidence")
        return self

    def analysis_input(self) -> dict[str, Any]:
        """Explicit whitelist: no endpoints, descriptions, labels or supervision."""
        return {
            "candidate": {"id": self.molecule.source_molecule_id, "smiles": self.molecule.canonical_smiles},
            "organism": {"species": self.organism.species, "taxon_id": self.organism.taxon_id,
                         "strain": self.organism.strain, "strain_namespace": self.organism.strain_namespace,
                         "isolate_id": self.organism.isolate_id},
            "conditions": self.conditions.model_dump(exclude={"provenance"}),
            "omics_profile_ids": list(self.pairing.profile_ids) if self.admission.paired_omics_eligible else [],
        }
