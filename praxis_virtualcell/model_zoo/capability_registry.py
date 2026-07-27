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
from praxis_virtualcell.model_zoo.cache import ModelCache

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
    schema_version: Literal["vc.environment.v1"]
    python_dependencies: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    runtime_tasks: tuple[str, ...] = ("predict_delta_expression",)
    runtime_outputs: tuple[str, ...] = ("delta_expression",)

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


class CapabilityRegistry:
    """Evaluate strict model cards without routing, prediction, or scientific inference."""

    def __init__(self, model_zoo, cache: ModelCache) -> None:
        self.model_zoo = model_zoo
        self.cache = cache

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

    def evaluate(
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

    def plan(
        self,
        request: VirtualCellRequestV2,
        pack: RegisteredPack | None,
        environment: EnvironmentSnapshot,
    ) -> ExecutionPlan:
        reports = tuple(
            self.evaluate(request, pack, name, environment)
            for name in self.model_zoo.capability_names()
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
        step: ExecutionStep,
        report: CompatibilityReport,
    ):
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
