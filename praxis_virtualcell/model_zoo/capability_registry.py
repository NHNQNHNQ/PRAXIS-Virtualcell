"""Strict model cards and deterministic Request × Pack × Model × Environment planning."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from praxis_virtualcell.biological_modules import modules as M
from praxis_virtualcell.core.request_v2 import (
    VirtualCellRequestV2,
    _freeze_json,
    _json_value,
)
from praxis_virtualcell.data_packs.registry import RegisteredPack
from praxis_virtualcell.model_zoo.adapter_sdk import (
    DEFAULT_ADAPTER_REGISTRY,
    AdapterContractError,
    AdapterRegistry,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.registry_v2 import (
    EnvironmentIdentity,
    ModelRegistryV2,
)

_TAXON = re.compile(r"^NCBITaxon:[0-9]+$")
_CURIE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MODEL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_PLAN_ID = re.compile(r"^plan_[0-9a-f]{24}$")
_ENTRYPOINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)
_PYTHON_MODULE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)
_OOD_DIMENSIONS = (
    "taxon",
    "modality",
    "assay",
    "cell_domain",
    "perturbation",
    "task",
    "output",
    "feature_namespace",
    "representation",
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string without surrounding whitespace")
    return value


def _text_array(
    value: Any,
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    items = tuple(_text(item, field) for item in value)
    if not allow_empty and not items:
        raise ValueError(f"{field} must not be empty")
    if len(set(items)) != len(items):
        raise ValueError(f"{field} must not contain duplicates")
    return items


def _canonical_fingerprint(value: dict[str, Any]) -> str:
    _json_value(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fingerprint(value: Any, field: str) -> str:
    value = _text(value, field)
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 fingerprint")
    return value


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:  # noqa: BLE001 - dependency probing must fail closed
        return False


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    def model_post_init(self, __context: Any) -> None:
        for name, value in self.__dict__.items():
            if isinstance(value, dict):
                object.__setattr__(self, name, _freeze_json(value))

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        return cls.model_validate(value)

    def to_dict(self) -> dict[str, Any]:
        value = self.model_dump(mode="json")
        _json_value(value)
        return value

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.to_dict())


class ModelModalityContract(_Contract):
    name: str
    ontology_id: str

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        return _text(value, "modality.name")

    @field_validator("ontology_id", mode="before")
    @classmethod
    def _valid_ontology(cls, value):
        value = _text(value, "modality.ontology_id")
        if not _CURIE.fullmatch(value):
            raise ValueError("modality.ontology_id must be a CURIE")
        return value


class ModelFeatureNamespaceContract(_Contract):
    name: str
    version: str
    id_format: Literal[
        "ensembl_gene",
        "ncbi_gene_curie",
        "sgd_systematic",
        "uniprot_protein",
    ]

    @field_validator("name", "version", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "feature_namespace field")


class ModelAssetContract(_Contract):
    filename: str
    sha256: str
    media_type: str
    source_note: str

    @field_validator("filename", mode="before")
    @classmethod
    def _valid_filename(cls, value):
        value = _text(value, "assets.filename")
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or value == "."
            or ".." in path.parts
            or "\\" in value
            or "\x00" in value
            or str(path) != value
        ):
            raise ValueError("assets.filename must be a canonical relative path")
        return value

    @field_validator("sha256", mode="before")
    @classmethod
    def _valid_sha(cls, value):
        value = _text(value, "assets.sha256")
        if not _SHA256.fullmatch(value):
            raise ValueError("assets.sha256 must be 64 lowercase hexadecimal characters")
        return value

    @field_validator("media_type", "source_note", mode="before")
    @classmethod
    def _valid_text(cls, value):
        return _text(value, "asset field")


class CellDomainContract(_Contract):
    cell_type_ids: tuple[str, ...] = ()
    cell_type_names: tuple[str, ...] = ()
    tissue_ids: tuple[str, ...] = ()
    tissue_names: tuple[str, ...] = ()
    allow_unspecified: bool = False

    @field_validator(
        "cell_type_ids",
        "cell_type_names",
        "tissue_ids",
        "tissue_names",
        mode="before",
    )
    @classmethod
    def _valid_arrays(cls, value, info):
        return _text_array(value, info.field_name, allow_empty=True)

    @field_validator("cell_type_ids", "tissue_ids")
    @classmethod
    def _valid_ids(cls, value):
        if any(not _CURIE.fullmatch(item) and not item.startswith("CVCL_") for item in value):
            raise ValueError("cell-domain IDs must be ontology CURIEs or canonical CVCL accessions")
        return value

    @model_validator(mode="after")
    def _declared_domain(self):
        if not self.allow_unspecified and not (
            self.cell_type_ids
            or self.cell_type_names
            or self.tissue_ids
            or self.tissue_names
        ):
            raise ValueError("cell_domain must declare a domain or allow_unspecified")
        return self


class ResourceContract(_Contract):
    python_dependencies: tuple[str, ...] = ()
    required: tuple[str, ...]

    @field_validator("python_dependencies", mode="before")
    @classmethod
    def _valid_dependencies(cls, value):
        values = _text_array(value, "resources.python_dependencies", allow_empty=True)
        if any(not _PYTHON_MODULE.fullmatch(item) for item in values):
            raise ValueError("python dependencies must be importable module names")
        return values

    @field_validator("required", mode="before")
    @classmethod
    def _valid_resources(cls, value):
        return _text_array(value, "resources.required")


class UncertaintyContract(_Contract):
    required: bool
    methods: tuple[str, ...]
    calibrated: bool

    @field_validator("methods", mode="before")
    @classmethod
    def _valid_methods(cls, value):
        return _text_array(value, "uncertainty.methods")


class OODContract(_Contract):
    action: Literal["abstain"]
    dimensions: tuple[str, ...]

    @field_validator("dimensions", mode="before")
    @classmethod
    def _valid_dimensions(cls, value):
        dimensions = _text_array(value, "ood.dimensions")
        if dimensions != _OOD_DIMENSIONS:
            raise ValueError(
                f"ood.dimensions must use the canonical complete order {_OOD_DIMENSIONS}"
            )
        return dimensions


class ModelCard(_Contract):
    schema_version: Literal["vc.model-card.v1"]
    name: str
    type: Literal["public_model", "self_trained"]
    species: tuple[str, ...]
    taxon: tuple[str, ...]
    module: str
    modality: tuple[ModelModalityContract, ...]
    assay: tuple[str, ...]
    cell_domain: CellDomainContract
    perturbation: tuple[str, ...]
    task: str
    output: tuple[str, ...]
    feature_namespace: tuple[ModelFeatureNamespaceContract, ...]
    representation: tuple[str, ...]
    source: str
    license: str
    status: Literal["available", "planned", "missing"]
    wrapper: str
    version: str
    requires: tuple[str, ...] = ()
    assets: tuple[ModelAssetContract, ...]
    resources: ResourceContract
    uncertainty: UncertaintyContract
    ood: OODContract
    reliability_policy: str
    training_card: dict[str, Any] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "module",
        "task",
        "source",
        "license",
        "wrapper",
        "version",
        "reliability_policy",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("name", mode="before")
    @classmethod
    def _valid_name(cls, value):
        value = _text(value, "name")
        if not _MODEL_NAME.fullmatch(value):
            raise ValueError("name must be canonical lower_snake_case")
        return value

    @field_validator(
        "species",
        "taxon",
        "assay",
        "perturbation",
        "output",
        "representation",
        mode="before",
    )
    @classmethod
    def _valid_nonempty_arrays(cls, value, info):
        return _text_array(value, info.field_name)

    @field_validator("requires", mode="before")
    @classmethod
    def _valid_requires(cls, value):
        return _text_array(value, "requires", allow_empty=True)

    @field_validator("modality", "feature_namespace", mode="before")
    @classmethod
    def _valid_contract_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)) or not value:
            raise ValueError(f"{info.field_name} must be a non-empty array")
        return tuple(value)

    @field_validator("assets", mode="before")
    @classmethod
    def _valid_assets(cls, value):
        if not isinstance(value, (list, tuple)):
            raise ValueError("assets must be an array")
        return tuple(value)

    @field_validator("taxon")
    @classmethod
    def _valid_taxon(cls, value):
        if any(not _TAXON.fullmatch(item) for item in value):
            raise ValueError("taxon values must be canonical NCBITaxon CURIEs")
        return value

    @field_validator("assay")
    @classmethod
    def _valid_assay(cls, value):
        if any(not _CURIE.fullmatch(item) for item in value):
            raise ValueError("assay values must be CURIEs")
        return value

    @field_validator("wrapper")
    @classmethod
    def _valid_wrapper(cls, value):
        if not _ENTRYPOINT.fullmatch(value):
            raise ValueError("wrapper must be a fully-qualified Python class path")
        return value

    @field_validator("training_card", "provenance", mode="before")
    @classmethod
    def _valid_json(cls, value, info):
        if value is None and info.field_name == "training_card":
            return None
        if not isinstance(value, dict):
            raise ValueError(f"{info.field_name} must be a JSON object")
        return _json_value(value, f"$.{info.field_name}")

    @model_validator(mode="after")
    def _consistent_contract(self):
        if self.module not in M.MODULE_ORDER:
            raise ValueError(f"module must be one of {M.MODULE_ORDER}")
        if self.type == "self_trained":
            if self.training_card is None:
                raise ValueError("self_trained model cards require training_card")
            required = (
                "training_data",
                "split",
                "baseline",
                "metrics",
                "provenance",
            )
            missing = [field for field in required if field not in self.training_card]
            if missing:
                raise ValueError(f"training_card missing fields: {missing}")
            if not isinstance(self.training_card["metrics"], dict):
                raise ValueError("training_card.metrics must be a JSON object")
            for field in ("training_data", "split", "baseline", "provenance"):
                _text(self.training_card[field], f"training_card.{field}")
        if len({item.name for item in self.modality}) != len(self.modality):
            raise ValueError("modality names must be unique")
        if len(set(self.feature_namespace)) != len(self.feature_namespace):
            raise ValueError("feature_namespace entries must be unique")
        if len({item.filename for item in self.assets}) != len(self.assets):
            raise ValueError("asset filenames must be unique")
        declared_requirements = set(self.resources.python_dependencies) | set(
            self.resources.required
        )
        if any(item not in declared_requirements for item in self.requires):
            raise ValueError("legacy requires must also be declared in resources")
        return self


class EnvironmentSnapshot(_Contract):
    schema_version: Literal["vc.environment.v1", "vc.environment.v2"]
    python_dependencies: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    runtime_tasks: tuple[str, ...] = ("predict_delta_expression",)
    runtime_outputs: tuple[str, ...] = ("delta_expression",)
    identity: EnvironmentIdentity | None = None

    @field_validator("python_dependencies", mode="before")
    @classmethod
    def _valid_dependencies(cls, value):
        values = _text_array(value, "python_dependencies", allow_empty=True)
        if any(not _PYTHON_MODULE.fullmatch(item) for item in values):
            raise ValueError("python_dependencies must contain import module names")
        return values

    @field_validator("resources", mode="before")
    @classmethod
    def _valid_resources(cls, value):
        return _text_array(value, "resources", allow_empty=True)

    @field_validator("runtime_tasks", "runtime_outputs", mode="before")
    @classmethod
    def _valid_runtime_contract(cls, value, info):
        return _text_array(value, info.field_name)

    @model_validator(mode="after")
    def _versioned_identity(self):
        if self.schema_version == "vc.environment.v1":
            if self.identity is not None:
                raise ValueError("vc.environment.v1 cannot contain a v2 identity")
            return self
        if self.identity is None:
            raise ValueError("vc.environment.v2 requires an EnvironmentIdentity")
        if set(self.resources) != set(self.identity.resources):
            raise ValueError("environment resources do not match EnvironmentIdentity")
        return self

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        if self.schema_version == "vc.environment.v1":
            value.pop("identity", None)
        return value

    @classmethod
    def detect(cls, cards: tuple[ModelCard, ...]) -> EnvironmentSnapshot:
        dependencies = sorted(
            {
                dependency
                for card in cards
                for dependency in card.resources.python_dependencies
                if _module_available(dependency)
            }
        )
        return cls(
            schema_version="vc.environment.v1",
            python_dependencies=dependencies,
            resources=["cpu"],
        )


class CompatibilityReport(_Contract):
    schema_version: Literal["vc.compatibility-report.v1"]
    request_id: str
    request_fingerprint: str
    model_name: str
    model_version: str
    model_fingerprint: str
    pack_id: str | None
    pack_version: str | None
    pack_fingerprint: str | None
    environment_fingerprint: str
    pack_valid: bool
    model_compatible: bool
    environment_compatible: bool
    assets_ready: bool
    wrapper_ready: bool
    executable: bool
    scientifically_validated: Literal[False] = False
    checks: dict[str, bool]
    reasons: tuple[str, ...]
    asset_paths: dict[str, str]

    @field_validator(
        "request_id",
        "request_fingerprint",
        "model_name",
        "model_version",
        "model_fingerprint",
        "environment_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "request_fingerprint",
        "model_fingerprint",
        "environment_fingerprint",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("pack_fingerprint", mode="before")
    @classmethod
    def _valid_optional_pack_fingerprint(cls, value):
        if value is None:
            return None
        return _fingerprint(value, "pack_fingerprint")

    @field_validator("reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _text_array(value, "reasons", allow_empty=True)

    @model_validator(mode="after")
    def _consistent_pack_identity(self):
        identity_present = (
            self.pack_id is not None,
            self.pack_version is not None,
            self.pack_fingerprint is not None,
        )
        if any(identity_present) and not all(identity_present):
            raise ValueError("compatibility report Pack identity must be all-or-none")
        if self.pack_valid != all(identity_present):
            raise ValueError(
                "pack_valid must match a complete Pack identity and fingerprint"
            )
        return self


class CompatibilityReportV2(_Contract):
    schema_version: Literal["vc.compatibility-report.v2"]
    request_id: str
    request_fingerprint: str
    model_name: str
    model_version: str | None
    model_fingerprint: str
    release_fingerprint: str | None
    capability_fingerprint: str | None
    pack_id: str | None
    pack_version: str | None
    pack_fingerprint: str | None
    environment_fingerprint: str | None
    environment_snapshot_fingerprint: str
    artifact_fingerprints: tuple[str, ...]
    adapter_fingerprints: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]
    policy_fingerprint: str | None
    cataloged: bool
    artifact_ready: bool
    revoked: bool
    superseded_by: str | None
    pack_valid: bool
    model_compatible: bool
    environment_compatible: bool
    adapter_compatible: bool
    assets_ready: bool
    wrapper_ready: bool
    benchmark_passed: bool | None
    scientifically_validated: bool | None
    promotion_eligible: bool | None
    policy_present: bool
    production_promoted: bool
    executable: bool
    checks: dict[str, bool]
    reasons: tuple[str, ...]
    asset_paths: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "request_id",
        "model_name",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("model_version", mode="before")
    @classmethod
    def _valid_optional_model_version(cls, value):
        return None if value is None else _text(value, "model_version")

    @field_validator(
        "request_fingerprint",
        "model_fingerprint",
        "environment_snapshot_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "release_fingerprint",
        "capability_fingerprint",
        "pack_fingerprint",
        "environment_fingerprint",
        "policy_fingerprint",
        "superseded_by",
        mode="before",
    )
    @classmethod
    def _valid_optional_fingerprint(cls, value, info):
        return None if value is None else _fingerprint(value, info.field_name)

    @field_validator(
        "artifact_fingerprints",
        "adapter_fingerprints",
        "evidence_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        values = _text_array(value, info.field_name, allow_empty=True)
        return tuple(_fingerprint(item, info.field_name) for item in values)

    @field_validator("reasons", mode="before")
    @classmethod
    def _valid_reasons(cls, value):
        return _text_array(value, "reasons", allow_empty=True)

    @model_validator(mode="after")
    def _consistent_identity_and_states(self):
        pack_identity = (
            self.pack_id is not None,
            self.pack_version is not None,
            self.pack_fingerprint is not None,
        )
        if any(pack_identity) and not all(pack_identity):
            raise ValueError("compatibility report Pack identity must be all-or-none")
        if self.pack_valid != all(pack_identity):
            raise ValueError("pack_valid must match a complete Pack identity")
        release_identity = (
            self.release_fingerprint,
            self.capability_fingerprint,
        )
        if any(item is not None for item in release_identity) and not all(
            item is not None for item in release_identity
        ):
            raise ValueError("release and capability fingerprints must be all-or-none")
        release_present = all(item is not None for item in release_identity)
        if not release_present and (
            self.environment_fingerprint is not None
            or self.artifact_fingerprints
            or self.adapter_fingerprints
            or self.evidence_fingerprints
            or self.policy_fingerprint is not None
            or self.cataloged
            or self.artifact_ready
            or self.revoked
            or self.superseded_by is not None
        ):
            raise ValueError("release-scoped identity and state require a release")
        evidence_states = (
            self.benchmark_passed,
            self.scientifically_validated,
            self.promotion_eligible,
        )
        if any(item is None for item in evidence_states) and not all(
            item is None for item in evidence_states
        ):
            raise ValueError("scientific evidence states must be all present or unavailable")
        if bool(self.evidence_fingerprints) != all(
            item is not None for item in evidence_states
        ):
            raise ValueError(
                "scientific evidence refs and states must agree before executable state"
            )
        if self.scientifically_validated and not self.benchmark_passed:
            raise ValueError("scientific validation requires benchmark_passed")
        if self.promotion_eligible and not (
            self.benchmark_passed and self.scientifically_validated
        ):
            raise ValueError("promotion eligibility exceeds evidence")
        if self.policy_present != (self.policy_fingerprint is not None):
            raise ValueError("policy_present must match policy_fingerprint")
        if self.production_promoted and not self.policy_present:
            raise ValueError("production promotion requires a policy record")
        if self.production_promoted and not (
            self.evidence_fingerprints
            and self.benchmark_passed is True
            and self.scientifically_validated is True
            and self.promotion_eligible is True
        ):
            raise ValueError(
                "production promotion requires bound passing scientific evidence"
            )
        if self.executable and not (
            release_present
            and self.model_version is not None
            and bool(self.artifact_fingerprints)
            and self.environment_fingerprint is not None
            and bool(self.adapter_fingerprints)
            and bool(self.evidence_fingerprints)
            and self.cataloged
            and self.artifact_ready
            and not self.revoked
            and self.superseded_by is None
            and self.pack_valid
            and self.model_compatible
            and self.environment_compatible
            and self.adapter_compatible
            and self.assets_ready
            and self.wrapper_ready
            and self.benchmark_passed
            and self.scientifically_validated
            and self.promotion_eligible
            and self.policy_present
            and self.production_promoted
        ):
            raise ValueError("executable exceeds the v2 evidence and policy gates")
        return self

    def fingerprint(self) -> str:
        value = self.to_dict()
        value.pop("asset_paths")
        value.pop("model_version")
        return _canonical_fingerprint(value)


class ExecutionStep(_Contract):
    model_name: str
    model_version: str
    model_fingerprint: str
    compatibility_fingerprint: str
    wrapper: str
    agent_name: str
    asset_paths: dict[str, str]

    @field_validator(
        "model_name",
        "model_version",
        "model_fingerprint",
        "compatibility_fingerprint",
        "wrapper",
        "agent_name",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "model_fingerprint",
        "compatibility_fingerprint",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)


class ExecutionStepV2(_Contract):
    schema_version: Literal["vc.execution-step.v2"]
    model_name: str
    model_version: str
    model_fingerprint: str
    release_fingerprint: str
    capability_fingerprint: str
    artifact_fingerprints: tuple[str, ...]
    environment_fingerprint: str
    adapter_fingerprints: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]
    policy_fingerprint: str
    compatibility_fingerprint: str
    wrapper: str
    agent_name: str
    asset_paths: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "model_name",
        "model_version",
        "wrapper",
        "agent_name",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator(
        "model_fingerprint",
        "release_fingerprint",
        "capability_fingerprint",
        "environment_fingerprint",
        "policy_fingerprint",
        "compatibility_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator(
        "artifact_fingerprints",
        "adapter_fingerprints",
        "evidence_fingerprints",
        mode="before",
    )
    @classmethod
    def _valid_fingerprints(cls, value, info):
        values = _text_array(value, info.field_name, allow_empty=True)
        return tuple(_fingerprint(item, info.field_name) for item in values)

    def identity_dict(self) -> dict[str, Any]:
        value = self.to_dict()
        value.pop("asset_paths")
        value.pop("model_version")
        return value

    def fingerprint(self) -> str:
        return _canonical_fingerprint(self.identity_dict())

    @model_validator(mode="after")
    def _consistent_step(self):
        if not (
            self.artifact_fingerprints
            and self.adapter_fingerprints
            and self.evidence_fingerprints
        ):
            raise ValueError("v2 execution steps require artifact, adapter, and evidence refs")
        if self.agent_name != self.model_name:
            raise ValueError("execution step agent_name must match model_name")
        return self


class ExecutionPlan(_Contract):
    schema_version: Literal["vc.execution-plan.v1"]
    plan_id: str
    request_id: str
    request_fingerprint: str
    pack_id: str | None
    pack_version: str | None
    pack_fingerprint: str | None
    environment_fingerprint: str
    executable: bool
    legacy_adapter: Literal[False] = False
    steps: tuple[ExecutionStep, ...]
    reports: tuple[CompatibilityReport, ...]

    @field_validator(
        "plan_id",
        "request_id",
        "request_fingerprint",
        "environment_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("plan_id")
    @classmethod
    def _valid_plan_id(cls, value):
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be plan_ plus 24 lowercase hex characters")
        return value

    @field_validator("request_fingerprint", "environment_fingerprint")
    @classmethod
    def _valid_fingerprints(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("pack_fingerprint", mode="before")
    @classmethod
    def _valid_optional_pack_fingerprint(cls, value):
        if value is None:
            return None
        return _fingerprint(value, "pack_fingerprint")

    @field_validator("steps", "reports", mode="before")
    @classmethod
    def _valid_contract_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        return tuple(value)

    @model_validator(mode="after")
    def _consistent_pack_identity(self):
        identity_present = (
            self.pack_id is not None,
            self.pack_version is not None,
            self.pack_fingerprint is not None,
        )
        if any(identity_present) and not all(identity_present):
            raise ValueError("execution plan Pack identity must be all-or-none")
        return self


class ExecutionPlanV2(_Contract):
    schema_version: Literal["vc.execution-plan.v2"]
    plan_id: str
    request_id: str
    request_fingerprint: str
    pack_id: str | None
    pack_version: str | None
    pack_fingerprint: str | None
    environment_snapshot_fingerprint: str
    executable: bool
    legacy_adapter: Literal[False] = False
    steps: tuple[ExecutionStepV2, ...]
    reports: tuple[CompatibilityReportV2, ...]

    @field_validator(
        "plan_id",
        "request_id",
        "request_fingerprint",
        "environment_snapshot_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_text(cls, value, info):
        return _text(value, info.field_name)

    @field_validator("plan_id")
    @classmethod
    def _valid_plan_id(cls, value):
        if not _PLAN_ID.fullmatch(value):
            raise ValueError("plan_id must be plan_ plus 24 lowercase hex characters")
        return value

    @field_validator(
        "request_fingerprint",
        "environment_snapshot_fingerprint",
        mode="before",
    )
    @classmethod
    def _valid_fingerprint(cls, value, info):
        return _fingerprint(value, info.field_name)

    @field_validator("pack_fingerprint", mode="before")
    @classmethod
    def _valid_optional_pack_fingerprint(cls, value):
        return None if value is None else _fingerprint(value, "pack_fingerprint")

    @field_validator("steps", "reports", mode="before")
    @classmethod
    def _valid_arrays(cls, value, info):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{info.field_name} must be an array")
        return tuple(value)

    @classmethod
    def _canonical_identity(
        cls,
        *,
        request_id: str,
        request_fingerprint: str,
        pack_fingerprint: str | None,
        environment_snapshot_fingerprint: str,
        reports: tuple[CompatibilityReportV2, ...],
        steps: tuple[ExecutionStepV2, ...],
    ) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "request_fingerprint": request_fingerprint,
            "pack_fingerprint": pack_fingerprint,
            "environment_snapshot_fingerprint": environment_snapshot_fingerprint,
            "reports": [report.fingerprint() for report in reports],
            "steps": [step.identity_dict() for step in steps],
        }

    @classmethod
    def build(
        cls,
        *,
        request_id: str,
        request_fingerprint: str,
        pack_id: str | None,
        pack_version: str | None,
        pack_fingerprint: str | None,
        environment_snapshot_fingerprint: str,
        reports: tuple[CompatibilityReportV2, ...],
        steps: tuple[ExecutionStepV2, ...],
    ) -> ExecutionPlanV2:
        identity = cls._canonical_identity(
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=pack_fingerprint,
            environment_snapshot_fingerprint=environment_snapshot_fingerprint,
            reports=reports,
            steps=steps,
        )
        return cls(
            schema_version="vc.execution-plan.v2",
            plan_id=f"plan_{_canonical_fingerprint(identity)[:24]}",
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            pack_id=pack_id,
            pack_version=pack_version,
            pack_fingerprint=pack_fingerprint,
            environment_snapshot_fingerprint=environment_snapshot_fingerprint,
            executable=bool(steps),
            legacy_adapter=False,
            steps=steps,
            reports=reports,
        )

    def rebuild(
        self,
        *,
        reports: tuple[CompatibilityReportV2, ...],
        steps: tuple[ExecutionStepV2, ...],
    ) -> ExecutionPlanV2:
        return type(self).build(
            request_id=self.request_id,
            request_fingerprint=self.request_fingerprint,
            pack_id=self.pack_id,
            pack_version=self.pack_version,
            pack_fingerprint=self.pack_fingerprint,
            environment_snapshot_fingerprint=self.environment_snapshot_fingerprint,
            reports=reports,
            steps=steps,
        )

    @model_validator(mode="after")
    def _consistent_plan(self):
        pack_identity = (
            self.pack_id is not None,
            self.pack_version is not None,
            self.pack_fingerprint is not None,
        )
        if any(pack_identity) and not all(pack_identity):
            raise ValueError("execution plan Pack identity must be all-or-none")
        if self.executable != bool(self.steps):
            raise ValueError("execution plan executable must match non-empty steps")
        report_names = tuple(report.model_name for report in self.reports)
        step_names = tuple(step.model_name for step in self.steps)
        if len(set(report_names)) != len(report_names):
            raise ValueError("execution plan reports must have unique model names")
        if len(set(step_names)) != len(step_names):
            raise ValueError("execution plan steps must have unique model names")
        for report in self.reports:
            if not (
                report.request_id == self.request_id
                and report.request_fingerprint == self.request_fingerprint
                and report.pack_id == self.pack_id
                and report.pack_version == self.pack_version
                and report.pack_fingerprint == self.pack_fingerprint
                and report.environment_snapshot_fingerprint
                == self.environment_snapshot_fingerprint
            ):
                raise ValueError("execution plan report identity does not match the plan")
        executable_names = {
            report.model_name for report in self.reports if report.executable
        }
        if set(step_names) != executable_names:
            raise ValueError("execution steps must exactly match executable reports")
        reports_by_name = {report.model_name: report for report in self.reports}
        for step in self.steps:
            report = reports_by_name[step.model_name]
            if not (
                step.model_version == report.model_version
                and step.model_fingerprint == report.model_fingerprint
                and step.release_fingerprint == report.release_fingerprint
                and step.capability_fingerprint == report.capability_fingerprint
                and step.artifact_fingerprints == report.artifact_fingerprints
                and step.environment_fingerprint == report.environment_fingerprint
                and step.adapter_fingerprints == report.adapter_fingerprints
                and step.evidence_fingerprints == report.evidence_fingerprints
                and step.policy_fingerprint == report.policy_fingerprint
                and step.compatibility_fingerprint == report.fingerprint()
                and dict(step.asset_paths) == dict(report.asset_paths)
            ):
                raise ValueError("execution step identity does not match its report")
        identity = self._canonical_identity(
            request_id=self.request_id,
            request_fingerprint=self.request_fingerprint,
            pack_fingerprint=self.pack_fingerprint,
            environment_snapshot_fingerprint=self.environment_snapshot_fingerprint,
            reports=self.reports,
            steps=self.steps,
        )
        expected_plan_id = f"plan_{_canonical_fingerprint(identity)[:24]}"
        if self.plan_id != expected_plan_id:
            raise ValueError("execution plan_id does not match canonical plan identity")
        return self


class CapabilityRegistry:
    """Evaluate strict model cards without routing, prediction, or scientific inference."""

    def __init__(
        self,
        model_zoo,
        cache: ModelCache,
        *,
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self.model_zoo = model_zoo
        self.cache = cache
        self.adapter_registry = (
            DEFAULT_ADAPTER_REGISTRY
            if adapter_registry is None
            else adapter_registry
        )
        if not isinstance(self.adapter_registry, AdapterRegistry):
            raise TypeError("adapter_registry must be AdapterRegistry")
        registry_v2 = getattr(model_zoo, "registry_v2", None)
        if registry_v2 is not None and not isinstance(registry_v2, ModelRegistryV2):
            raise TypeError("model_zoo.registry_v2 must be ModelRegistryV2")
        self.registry_v2 = registry_v2

    @staticmethod
    def _pack_dimensions(pack: RegisteredPack | None) -> dict[str, Any]:
        if pack is None:
            return {
                "taxon": None,
                "modalities": (),
                "assays": (),
                "namespaces": (),
                "representations": (),
                "input_contracts": (),
            }
        manifest = pack.manifest
        if manifest.multiomics is not None:
            modalities = tuple(
                (item.modality.name, item.modality.ontology_id)
                for item in manifest.multiomics.modalities
            )
            namespaces = tuple(
                (
                    item.feature_namespace.name,
                    item.feature_namespace.version,
                    item.feature_semantics.id_format,
                )
                for item in manifest.multiomics.modalities
            )
            input_contracts = tuple(
                (
                    item.modality.name,
                    item.modality.ontology_id,
                    item.feature_namespace.name,
                    item.feature_namespace.version,
                    item.feature_semantics.id_format,
                )
                for item in manifest.multiomics.modalities
            )
            representations = ("matrix:X",)
        else:
            modalities = ((manifest.modality.name, manifest.modality.ontology_id),)
            id_format = (
                manifest.feature_semantics.id_format
                if manifest.feature_semantics is not None
                else {
                    "EnsemblGene": "ensembl_gene",
                    "NCBIGene": "ncbi_gene_curie",
                    "UniProtKB": "uniprot_protein",
                }.get(manifest.feature_namespace.name)
            )
            namespaces = (
                (
                    manifest.feature_namespace.name,
                    manifest.feature_namespace.version,
                    id_format,
                ),
            )
            input_contracts = (
                (
                    manifest.modality.name,
                    manifest.modality.ontology_id,
                    manifest.feature_namespace.name,
                    manifest.feature_namespace.version,
                    id_format,
                ),
            )
            representations = (
                ("matrix:X",)
                if manifest.matrix is not None
                else tuple(f"asset:{asset.media_type}" for asset in manifest.assets)
            )
        return {
            "taxon": manifest.taxon.ontology_id,
            "modalities": modalities,
            "assays": tuple(item[1] for item in modalities),
            "namespaces": namespaces,
            "representations": representations,
            "input_contracts": input_contracts,
        }

    @staticmethod
    def _cell_domain_matches(request: VirtualCellRequestV2, card: ModelCard) -> bool:
        domain = card.cell_domain
        context = request.cell_context
        cell_domain_declared = bool(
            domain.cell_type_ids or domain.cell_type_names
        )
        tissue_domain_declared = bool(domain.tissue_ids or domain.tissue_names)
        if context.cell_type_id is not None:
            cell_ok = context.cell_type_id in domain.cell_type_ids
        elif context.cell_type_name is not None:
            cell_ok = context.cell_type_name in domain.cell_type_names
        else:
            cell_ok = not cell_domain_declared or domain.allow_unspecified
        if context.tissue_id is not None:
            tissue_ok = context.tissue_id in domain.tissue_ids
        elif context.tissue_name is not None:
            tissue_ok = context.tissue_name in domain.tissue_names
        else:
            tissue_ok = not tissue_domain_declared or domain.allow_unspecified
        return cell_ok and tissue_ok

    @staticmethod
    def _wrapper_class(card: ModelCard):
        module_name, class_name = card.wrapper.rsplit(".", 1)
        module = importlib.import_module(module_name)
        wrapper_class = getattr(module, class_name)
        from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper

        if not isinstance(wrapper_class, type) or not issubclass(wrapper_class, ModelWrapper):
            raise TypeError(f"{card.wrapper} is not a ModelWrapper subclass")
        return wrapper_class

    def _evaluate_v1(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
        model_name: str,
        environment: EnvironmentSnapshot,
    ) -> CompatibilityReport:
        if not isinstance(request, VirtualCellRequestV2):
            raise TypeError("CapabilityRegistry.evaluate requires VirtualCellRequestV2")
        if pack is not None and not isinstance(pack, RegisteredPack):
            raise TypeError("pack must be a RegisteredPack produced by PackRegistry")
        if not isinstance(environment, EnvironmentSnapshot):
            raise TypeError("environment must be EnvironmentSnapshot")

        card = self.model_zoo.card(model_name)
        pack_dimensions = self._pack_dimensions(pack)
        card_modalities = {(item.name, item.ontology_id) for item in card.modality}
        card_namespaces = {
            (item.name, item.version, item.id_format)
            for item in card.feature_namespace
        }
        requested_outputs = request.task.requested_outputs or (
            request.output_modality.name,
        )
        requested_modality_in_pack = any(
            name == request.input_modality.name
            and (
                request.input_modality.ontology_id is None
                or ontology_id == request.input_modality.ontology_id
            )
            for name, ontology_id, *_ in pack_dimensions["input_contracts"]
        )
        requested_namespace_in_pack = (
            request.input_modality.feature_namespace is None
            or any(
                modality_name == request.input_modality.name
                and namespace_name
                == request.input_modality.feature_namespace
                and (
                    request.input_modality.ontology_id is None
                    or ontology_id == request.input_modality.ontology_id
                )
                for (
                    modality_name,
                    ontology_id,
                    namespace_name,
                    _namespace_version,
                    _id_format,
                ) in pack_dimensions["input_contracts"]
            )
        )

        checks: dict[str, bool] = {
            "model.status": card.status == "available",
            "pack.valid": pack is not None,
            "request.taxon": request.species.taxonomy_id in card.taxon,
            "pack.taxon": (
                pack is not None
                and pack_dimensions["taxon"] == request.species.taxonomy_id
                and pack_dimensions["taxon"] in card.taxon
            ),
            "request.modality": any(
                item.name == request.input_modality.name for item in card.modality
            ),
            "request.assay": (
                request.input_modality.ontology_id is None
                or request.input_modality.ontology_id in card.assay
            ),
            "request_pack.modality": requested_modality_in_pack,
            "pack.modality": bool(
                card_modalities.intersection(pack_dimensions["modalities"])
            ),
            "pack.assay": bool(set(card.assay).intersection(pack_dimensions["assays"])),
            "request.cell_domain": self._cell_domain_matches(request, card),
            "request.perturbation": request.perturbation.kind in card.perturbation,
            "request.task": request.task.task_type == card.task,
            "request.requested_outputs_unique": (
                len(set(request.task.requested_outputs))
                == len(request.task.requested_outputs)
            ),
            "request.output": all(item in card.output for item in requested_outputs)
            and request.output_modality.name in card.output,
            "request.feature_namespace": (
                request.input_modality.feature_namespace is None
                or any(
                    item.name == request.input_modality.feature_namespace
                    for item in card.feature_namespace
                )
            ),
            "request_pack.feature_namespace": requested_namespace_in_pack,
            "pack.feature_namespace": bool(
                card_namespaces.intersection(pack_dimensions["namespaces"])
            ),
            "pack.representation": bool(
                set(card.representation).intersection(
                    pack_dimensions["representations"]
                )
            ),
            "environment.dependencies": set(
                card.resources.python_dependencies
            ).issubset(set(environment.python_dependencies)),
            "environment.resources": set(card.resources.required).issubset(
                set(environment.resources)
            ),
            "environment.runtime_task": card.task in environment.runtime_tasks,
            "environment.runtime_output": all(
                output in environment.runtime_outputs
                for output in requested_outputs
            ),
        }

        reasons: list[str] = []
        reason_for_check = {
            "model.status": f"model.status:{card.status}",
            "pack.valid": "pack.unregistered",
            "request.taxon": "request.taxon",
            "pack.taxon": "pack.taxon",
            "request.modality": "request.modality",
            "request.assay": "request.assay",
            "request_pack.modality": "request_pack.modality",
            "pack.modality": "pack.modality",
            "pack.assay": "pack.assay",
            "request.cell_domain": "request.cell_domain",
            "request.perturbation": "request.perturbation",
            "request.task": "request.task",
            "request.requested_outputs_unique": (
                "request.requested_outputs_duplicates"
            ),
            "request.output": "request.output",
            "request.feature_namespace": "request.feature_namespace",
            "request_pack.feature_namespace": (
                "request_pack.feature_namespace"
            ),
            "pack.feature_namespace": "pack.feature_namespace",
            "pack.representation": "pack.representation",
        }
        for check, ok in checks.items():
            if not ok and check in reason_for_check:
                reasons.append(reason_for_check[check])
        for dependency in card.resources.python_dependencies:
            if dependency not in environment.python_dependencies:
                reasons.append(f"environment.dependency:{dependency}")
        for resource in card.resources.required:
            if resource not in environment.resources:
                reasons.append(f"environment.resource:{resource}")
        if card.task not in environment.runtime_tasks:
            reasons.append(f"environment.runtime_task:{card.task}")
        for output in requested_outputs:
            if output not in environment.runtime_outputs:
                reasons.append(f"environment.runtime_output:{output}")

        asset_paths: dict[str, str] = {}
        assets_ready = True
        for asset in card.assets:
            status = self.cache.check(
                card.name,
                asset.filename,
                sha256=asset.sha256,
            )
            if status.available:
                asset_paths[asset.filename] = status.path
            else:
                assets_ready = False
                code = (
                    "asset.missing"
                    if status.reason.startswith("asset_not_found")
                    else "asset.sha256"
                )
                reasons.append(f"{code}:{asset.filename}")
        checks["model.assets"] = assets_ready

        try:
            self._wrapper_class(card)
            wrapper_ready = True
        except Exception:  # noqa: BLE001 - import probes are a fail-closed gate
            wrapper_ready = False
            reasons.append("model.wrapper")
        checks["model.wrapper"] = wrapper_ready

        scope_checks = (
            "pack.valid",
            "request.taxon",
            "pack.taxon",
            "request.modality",
            "request.assay",
            "request_pack.modality",
            "pack.modality",
            "pack.assay",
            "request.cell_domain",
            "request.perturbation",
            "request.task",
            "request.requested_outputs_unique",
            "request.output",
            "request.feature_namespace",
            "request_pack.feature_namespace",
            "pack.feature_namespace",
            "pack.representation",
        )
        model_compatible = all(checks[name] for name in scope_checks)
        environment_compatible = (
            checks["environment.dependencies"]
            and checks["environment.resources"]
            and checks["environment.runtime_task"]
            and checks["environment.runtime_output"]
            and assets_ready
            and wrapper_ready
        )
        executable = (
            checks["model.status"]
            and model_compatible
            and environment_compatible
        )

        manifest = pack.manifest if pack is not None else None
        return CompatibilityReport(
            schema_version="vc.compatibility-report.v1",
            request_id=request.request_id,
            request_fingerprint=_canonical_fingerprint(request.to_dict()),
            model_name=card.name,
            model_version=card.version,
            model_fingerprint=card.fingerprint(),
            pack_id=manifest.pack_id if manifest is not None else None,
            pack_version=manifest.pack_version if manifest is not None else None,
            pack_fingerprint=pack.fingerprint if pack is not None else None,
            environment_fingerprint=environment.fingerprint(),
            pack_valid=pack is not None,
            model_compatible=model_compatible,
            environment_compatible=environment_compatible,
            assets_ready=assets_ready,
            wrapper_ready=wrapper_ready,
            executable=executable,
            scientifically_validated=False,
            checks=checks,
            reasons=reasons,
            asset_paths=asset_paths,
        )

    def evaluate(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
        model_name: str,
        environment: EnvironmentSnapshot,
    ) -> CompatibilityReport | CompatibilityReportV2:
        legacy = self._evaluate_v1(request, pack, model_name, environment)
        if self.registry_v2 is None:
            return legacy
        return self._evaluate_v2(request, pack, environment, legacy)

    def _evaluate_v2(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
        environment: EnvironmentSnapshot,
        legacy: CompatibilityReport,
    ) -> CompatibilityReportV2:
        assert self.registry_v2 is not None
        registry = self.registry_v2
        card = self.model_zoo.card(legacy.model_name)
        pack_fingerprint = pack.fingerprint if pack is not None else None
        model_releases = tuple(
            release
            for release in registry.releases
            if release.model_name == card.name
            and release.model_version == card.version
            and release.model_fingerprint == card.fingerprint()
        )
        exact_releases = tuple(
            release
            for release in model_releases
            if pack_fingerprint is not None
            and pack_fingerprint in release.pack_fingerprints
        )
        release = (
            exact_releases[0]
            if len(exact_releases) == 1
            else model_releases[0]
            if not exact_releases and len(model_releases) == 1
            else None
        )
        release_fingerprint = release.fingerprint() if release is not None else None
        capability_fingerprint = (
            release.capability_fingerprint() if release is not None else None
        )
        release_pack_match = bool(
            release is not None
            and pack_fingerprint is not None
            and pack_fingerprint in release.pack_fingerprints
        )

        state = registry.state(release_fingerprint) if release is not None else None
        cataloged = bool(state is not None and state.cataloged)
        registry_artifact_ready = bool(state is not None and state.artifact_ready)
        revoked = bool(state is not None and state.revoked)
        superseded_by = state.superseded_by if state is not None else None

        artifact_fingerprints = (
            release.artifact_fingerprints if release is not None else ()
        )
        artifacts = tuple(
            registry.artifact(fingerprint) for fingerprint in artifact_fingerprints
        )
        artifact_by_key = {artifact.cache_key: artifact for artifact in artifacts}
        asset_paths: dict[str, str] = {}
        assets_ready = bool(release is not None and artifacts)
        reasons = list(legacy.reasons)
        expected_keys = {
            f"{card.name}/{asset.filename}" for asset in card.assets
        }
        if set(artifact_by_key) != expected_keys:
            assets_ready = False
            reasons.append("artifact.binding")
        for asset in card.assets:
            key = f"{card.name}/{asset.filename}"
            artifact = artifact_by_key.get(key)
            if artifact is None or (
                artifact.legacy_incomplete
                or artifact.model_fingerprint != card.fingerprint()
                or artifact.sha256 != asset.sha256
                or artifact.media_type != asset.media_type
                or artifact.size_bytes is None
            ):
                assets_ready = False
                continue
            if artifact.safe_load_policy != "data_only":
                assets_ready = False
                reasons.append(f"artifact.safe_load_policy:{asset.filename}")
                continue
            status = self.cache.check(
                card.name,
                asset.filename,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            )
            if status.available:
                asset_paths[asset.filename] = status.path
            else:
                assets_ready = False
                code = (
                    "artifact.path_escape"
                    if status.reason == "asset_path_escape"
                    else "artifact.size"
                    if status.reason.startswith("size_mismatch")
                    else "artifact.sha256"
                    if status.reason.startswith("sha256_mismatch")
                    else "artifact.missing"
                )
                reasons.append(f"{code}:{asset.filename}")

        environment_fingerprint = (
            release.environment_fingerprint if release is not None else None
        )
        environment_identity_match = bool(
            environment.schema_version == "vc.environment.v2"
            and environment.identity is not None
            and environment_fingerprint == environment.identity.fingerprint()
        )
        adapter_fingerprints = (
            release.adapter_fingerprints if release is not None else ()
        )
        adapters = tuple(
            registry.adapter(fingerprint) for fingerprint in adapter_fingerprints
        )
        requested_outputs = request.task.requested_outputs or (
            request.output_modality.name,
        )
        try:
            runtime_adapter = self.adapter_registry.resolve_requested(
                request.task.task_type,
                requested_outputs,
            )
            adapter_compatible = bool(
                environment_identity_match
                and len(adapters) == 1
                and environment.identity is not None
                and environment.identity.adapter_fingerprints == adapter_fingerprints
                and adapter_fingerprints == (runtime_adapter.fingerprint(),)
                and not adapters[0].legacy_incomplete
                and adapters[0].task == request.task.task_type == card.task
                and adapters[0].outputs == tuple(requested_outputs)
                and self.adapter_registry.resolve_identity(adapters[0])
                is runtime_adapter
            )
        except (AdapterContractError, TypeError, ValueError):
            adapter_compatible = False

        evidence_fingerprints = (
            release.evidence_fingerprints if release is not None else ()
        )
        evidence_records = tuple(
            registry.evidence(fingerprint) for fingerprint in evidence_fingerprints
        )
        evidence_present = bool(
            evidence_records
            and pack_fingerprint is not None
            and any(
                evidence.pack_fingerprint == pack_fingerprint
                for evidence in evidence_records
            )
        )
        benchmark_passed = (
            all(evidence.benchmark_passed for evidence in evidence_records)
            if evidence_present
            else None
        )
        scientifically_validated = (
            all(evidence.scientifically_validated for evidence in evidence_records)
            if evidence_present
            else None
        )
        promotion_eligible = (
            all(evidence.promotion_eligible for evidence in evidence_records)
            if evidence_present
            else None
        )
        policy_fingerprint = release.policy_fingerprint if release is not None else None
        policy = (
            registry.policy(policy_fingerprint)
            if policy_fingerprint is not None
            else None
        )
        policy_present = policy is not None
        production_promoted = bool(
            policy is not None and policy.production_promoted
        )

        environment_checks = (
            legacy.checks["environment.dependencies"]
            and legacy.checks["environment.resources"]
            and legacy.checks["environment.runtime_task"]
            and legacy.checks["environment.runtime_output"]
        )
        environment_compatible = bool(
            environment_checks
            and environment_identity_match
            and adapter_compatible
            and assets_ready
            and legacy.wrapper_ready
        )
        release_native = bool(
            release is not None and release.migration_status == "native"
        )
        executable = bool(
            legacy.checks["model.status"]
            and release_native
            and release_pack_match
            and cataloged
            and registry_artifact_ready
            and not revoked
            and superseded_by is None
            and legacy.model_compatible
            and environment_compatible
            and evidence_present
            and benchmark_passed
            and scientifically_validated
            and promotion_eligible
            and policy_present
            and production_promoted
        )

        checks = dict(legacy.checks)
        checks.update(
            {
                "registry.release": release is not None,
                "registry.release_native": release_native,
                "registry.pack_binding": release_pack_match,
                "registry.cataloged": cataloged,
                "registry.artifact_ready": registry_artifact_ready,
                "registry.not_revoked": not revoked,
                "registry.not_superseded": superseded_by is None,
                "model.assets": assets_ready,
                "environment.identity": environment_identity_match,
                "environment.adapter": adapter_compatible,
                "evidence.present": evidence_present,
                "evidence.benchmark_passed": benchmark_passed is True,
                "evidence.scientifically_validated": scientifically_validated is True,
                "evidence.promotion_eligible": promotion_eligible is True,
                "policy.present": policy_present,
                "policy.production_promoted": production_promoted,
            }
        )
        if release is None:
            reasons.append(
                "registry.release_ambiguous"
                if len(model_releases) > 1
                else "registry.release_missing"
            )
        elif not release_native:
            reasons.append("registry.release_incomplete")
        if not release_pack_match:
            reasons.append("registry.pack_binding")
        if not cataloged:
            reasons.append("registry.not_cataloged")
        if not registry_artifact_ready:
            reasons.append("registry.artifact_not_ready")
        if revoked:
            reasons.append("registry.revoked")
        if superseded_by is not None:
            reasons.append("registry.superseded")
        if not environment_identity_match:
            reasons.append("environment.identity")
        if not adapter_compatible:
            reasons.append("adapter.identity")
        if not evidence_present:
            reasons.append("evidence.missing")
        elif not (
            benchmark_passed
            and scientifically_validated
            and promotion_eligible
        ):
            reasons.append("evidence.not_eligible")
        if not policy_present:
            reasons.append("policy.missing")
        elif not production_promoted:
            reasons.append("policy.not_promoted")

        manifest = pack.manifest if pack is not None else None
        return CompatibilityReportV2(
            schema_version="vc.compatibility-report.v2",
            request_id=request.request_id,
            request_fingerprint=_canonical_fingerprint(request.to_dict()),
            model_name=card.name,
            model_version=card.version,
            model_fingerprint=card.fingerprint(),
            release_fingerprint=release_fingerprint,
            capability_fingerprint=capability_fingerprint,
            pack_id=manifest.pack_id if manifest is not None else None,
            pack_version=manifest.pack_version if manifest is not None else None,
            pack_fingerprint=pack_fingerprint,
            environment_fingerprint=environment_fingerprint,
            environment_snapshot_fingerprint=environment.fingerprint(),
            artifact_fingerprints=artifact_fingerprints,
            adapter_fingerprints=adapter_fingerprints,
            evidence_fingerprints=evidence_fingerprints,
            policy_fingerprint=policy_fingerprint,
            cataloged=cataloged,
            artifact_ready=registry_artifact_ready,
            revoked=revoked,
            superseded_by=superseded_by,
            pack_valid=pack is not None,
            model_compatible=legacy.model_compatible,
            environment_compatible=environment_compatible,
            adapter_compatible=adapter_compatible,
            assets_ready=assets_ready,
            wrapper_ready=legacy.wrapper_ready,
            benchmark_passed=benchmark_passed,
            scientifically_validated=scientifically_validated,
            promotion_eligible=promotion_eligible,
            policy_present=policy_present,
            production_promoted=production_promoted,
            executable=executable,
            checks=checks,
            reasons=tuple(dict.fromkeys(reasons)),
            asset_paths=asset_paths,
        )

    def plan(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
        environment: EnvironmentSnapshot,
    ) -> ExecutionPlan | ExecutionPlanV2:
        reports = tuple(
            self.evaluate(request, pack, name, environment)
            for name in self.model_zoo.capability_names()
        )
        if self.registry_v2 is not None:
            v2_reports = tuple(
                report
                for report in reports
                if isinstance(report, CompatibilityReportV2)
            )
            if len(v2_reports) != len(reports):
                raise ValueError("v2 planning received a legacy compatibility report")
            steps_v2 = tuple(
                ExecutionStepV2(
                    schema_version="vc.execution-step.v2",
                    model_name=report.model_name,
                    model_version=report.model_version,
                    model_fingerprint=report.model_fingerprint,
                    release_fingerprint=report.release_fingerprint,
                    capability_fingerprint=report.capability_fingerprint,
                    artifact_fingerprints=report.artifact_fingerprints,
                    environment_fingerprint=report.environment_fingerprint,
                    adapter_fingerprints=report.adapter_fingerprints,
                    evidence_fingerprints=report.evidence_fingerprints,
                    policy_fingerprint=report.policy_fingerprint,
                    compatibility_fingerprint=report.fingerprint(),
                    wrapper=self.model_zoo.card(report.model_name).wrapper,
                    agent_name=report.model_name,
                    asset_paths=report.asset_paths,
                )
                for report in v2_reports
                if report.executable
                and report.release_fingerprint is not None
                and report.capability_fingerprint is not None
                and report.environment_fingerprint is not None
                and report.policy_fingerprint is not None
            )
            manifest = pack.manifest if pack is not None else None
            return ExecutionPlanV2.build(
                request_id=request.request_id,
                request_fingerprint=_canonical_fingerprint(request.to_dict()),
                pack_id=manifest.pack_id if manifest is not None else None,
                pack_version=manifest.pack_version if manifest is not None else None,
                pack_fingerprint=pack.fingerprint if pack is not None else None,
                environment_snapshot_fingerprint=environment.fingerprint(),
                reports=v2_reports,
                steps=steps_v2,
            )
        steps = tuple(
            ExecutionStep(
                model_name=report.model_name,
                model_version=report.model_version,
                model_fingerprint=report.model_fingerprint,
                compatibility_fingerprint=report.fingerprint(),
                wrapper=self.model_zoo.card(report.model_name).wrapper,
                agent_name=report.model_name,
                asset_paths=report.asset_paths,
            )
            for report in reports
            if report.executable
        )
        manifest = pack.manifest if pack is not None else None
        identity = {
            "request_id": request.request_id,
            "request_fingerprint": _canonical_fingerprint(request.to_dict()),
            "pack_fingerprint": pack.fingerprint if pack is not None else None,
            "environment_fingerprint": environment.fingerprint(),
            "reports": [report.fingerprint() for report in reports],
            "steps": [step.to_dict() for step in steps],
        }
        plan_hash = hashlib.sha256(
            json.dumps(
                identity,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        return ExecutionPlan(
            schema_version="vc.execution-plan.v1",
            plan_id=f"plan_{plan_hash[:24]}",
            request_id=request.request_id,
            request_fingerprint=identity["request_fingerprint"],
            pack_id=manifest.pack_id if manifest is not None else None,
            pack_version=manifest.pack_version if manifest is not None else None,
            pack_fingerprint=pack.fingerprint if pack is not None else None,
            environment_fingerprint=environment.fingerprint(),
            executable=bool(steps),
            legacy_adapter=False,
            steps=steps,
            reports=reports,
        )

    def instantiate(
        self,
        step: ExecutionStep | ExecutionStepV2,
        report: CompatibilityReport | CompatibilityReportV2,
        *,
        request: VirtualCellRequestV2 | None = None,
        pack: RegisteredPack | None = None,
    ):
        if isinstance(step, ExecutionStepV2) and isinstance(
            report, CompatibilityReportV2
        ):
            return self._instantiate_v2(
                step,
                report,
                request=request,
                pack=pack,
            )
        if not isinstance(step, ExecutionStep) or not isinstance(
            report, CompatibilityReport
        ):
            raise TypeError("instantiate requires validated execution contracts")
        card = self.model_zoo.card(step.model_name)
        if not report.executable or not (
            step.model_name == report.model_name == card.name
            and step.model_version == report.model_version == card.version
            and step.model_fingerprint
            == report.model_fingerprint
            == card.fingerprint()
            and step.compatibility_fingerprint == report.fingerprint()
            and step.wrapper == card.wrapper
            and step.agent_name == card.name
            and dict(step.asset_paths) == dict(report.asset_paths)
        ):
            raise ValueError("cannot instantiate an incompatible execution step")
        for asset in card.assets:
            status = self.cache.check(
                card.name,
                asset.filename,
                sha256=asset.sha256,
            )
            if (
                not status.available
                or status.path != step.asset_paths.get(asset.filename)
            ):
                raise ValueError("cannot instantiate with an unavailable model asset")
        wrapper_class = self._wrapper_class(card)
        instance = wrapper_class.from_capability(
            card=card,
            compatibility_report=report,
            asset_paths=step.asset_paths,
        )
        if not isinstance(instance, wrapper_class) or (
            instance.name != card.name
            or instance.model_version != card.version
        ):
            raise ValueError("wrapper returned an invalid capability instance")
        return instance

    def _instantiate_v2(
        self,
        step: ExecutionStepV2,
        report: CompatibilityReportV2,
        *,
        request: VirtualCellRequestV2 | None,
        pack: RegisteredPack | None,
    ):
        if self.registry_v2 is None:
            raise ValueError("cannot instantiate a v2 step without ModelRegistryV2")
        if not isinstance(request, VirtualCellRequestV2) or not isinstance(
            pack, RegisteredPack
        ):
            raise ValueError("v2 instantiation requires the exact request and registered Pack")
        card = self.model_zoo.card(step.model_name)
        release = self.registry_v2.release(step.release_fingerprint)
        state = self.registry_v2.state(step.release_fingerprint)
        if not report.executable or not (
            state.cataloged
            and state.artifact_ready
            and not state.revoked
            and state.superseded_by is None
            and step.model_name == report.model_name == release.model_name == card.name
            and step.model_version
            == report.model_version
            == release.model_version
            == card.version
            and step.model_fingerprint
            == report.model_fingerprint
            == release.model_fingerprint
            == card.fingerprint()
            and step.capability_fingerprint
            == report.capability_fingerprint
            == release.capability_fingerprint()
            and step.artifact_fingerprints
            == report.artifact_fingerprints
            == release.artifact_fingerprints
            and step.environment_fingerprint
            == report.environment_fingerprint
            == release.environment_fingerprint
            and step.adapter_fingerprints
            == report.adapter_fingerprints
            == release.adapter_fingerprints
            and step.evidence_fingerprints
            == report.evidence_fingerprints
            == release.evidence_fingerprints
            and step.policy_fingerprint
            == report.policy_fingerprint
            == release.policy_fingerprint
            and step.compatibility_fingerprint == report.fingerprint()
            and _canonical_fingerprint(request.to_dict())
            == report.request_fingerprint
            and pack.fingerprint == report.pack_fingerprint
            and step.wrapper == card.wrapper
            and step.agent_name == card.name
            and dict(step.asset_paths) == dict(report.asset_paths)
        ):
            raise ValueError("cannot instantiate an incompatible v2 execution step")
        for asset_fingerprint in release.artifact_fingerprints:
            artifact = self.registry_v2.artifact(asset_fingerprint)
            if artifact.safe_load_policy != "data_only":
                raise ValueError("cannot instantiate without an enforced safe load policy")
            prefix = f"{card.name}/"
            if not artifact.cache_key.startswith(prefix):
                raise ValueError("cannot instantiate an incorrectly bound artifact")
            filename = artifact.cache_key[len(prefix):]
            status = self.cache.check(
                card.name,
                filename,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            )
            if (
                not status.available
                or status.path != step.asset_paths.get(filename)
            ):
                raise ValueError("cannot instantiate with an unavailable model artifact")
        adapter_identities = tuple(
            self.registry_v2.adapter(fingerprint)
            for fingerprint in release.adapter_fingerprints
        )
        requested_outputs = request.task.requested_outputs or (
            request.output_modality.name,
        )
        try:
            runtime_adapter = self.adapter_registry.resolve_requested(
                request.task.task_type,
                requested_outputs,
            )
            if (
                len(adapter_identities) != 1
                or runtime_adapter.fingerprint() != release.adapter_fingerprints[0]
                or self.adapter_registry.resolve_identity(adapter_identities[0])
                is not runtime_adapter
            ):
                raise AdapterContractError("release adapter binding is not exact")
            prepared_input = runtime_adapter.prepare_input(
                request,
                pack=pack,
                compatibility_report=report,
            )
        except Exception as exc:  # noqa: BLE001 — third-party input adapter boundary
            raise AdapterContractError(
                f"cannot prepare an exact registered adapter input: {exc}"
            ) from exc
        wrapper_class = self._wrapper_class(card)
        instance = wrapper_class.from_capability(
            card=card,
            compatibility_report=report,
            asset_paths=step.asset_paths,
            runtime_adapter=runtime_adapter,
            prepared_input=prepared_input,
        )
        if not isinstance(instance, wrapper_class) or (
            instance.name != card.name
            or instance.model_version != card.version
        ):
            raise ValueError("wrapper returned an invalid capability instance")
        return instance
