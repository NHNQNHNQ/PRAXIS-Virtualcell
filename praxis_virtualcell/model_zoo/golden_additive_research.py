"""First real, research-only Golden Norman model registration.

This module binds one exact held-out AHR+KLF1 task to the hash-locked Golden
Pack and additive baseline assets.  It never downloads data, changes the
default model zoo, grants scientific validation, or promotes production use.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.resources
import io
import json
import os
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from praxis_virtualcell.core.request_v2 import VirtualCellRequestV2
from praxis_virtualcell.data_packs.registry import PackRegistry, PreparedPackViewV1
from praxis_virtualcell.model_zoo.adapter_sdk import (
    AdapterContractError,
    AdapterInputContract,
    AdapterOutputContract,
    AdapterOutputEnvelope,
    AdapterRegistry,
    DeltaExpressionReferenceAdapter,
    PreparedAdapterInput,
    _reject_model_type_drift,
    _reject_undeclared_model_fields,
)
from praxis_virtualcell.model_zoo.cache import ModelCache
from praxis_virtualcell.model_zoo.capability_registry import (
    CompatibilityReportV2,
    EnvironmentSnapshot,
    ModelCard,
)
from praxis_virtualcell.model_zoo.registry import ModelZooRegistry
from praxis_virtualcell.model_zoo.registry_v2 import (
    ArtifactIdentity,
    EnvironmentIdentity,
    EnvironmentIdentityV2,
    ModelRegistryV2,
    ModelReleaseRecord,
    OperatorPolicyRecordV2,
    PackageIdentity,
    RegistryLifecycleEvent,
    ValidationEvidence,
)
from praxis_virtualcell.model_zoo.wrapper_registry import WrapperRegistry
from praxis_virtualcell.model_zoo.wrappers.base import ModelWrapper
from praxis_virtualcell.workflows.runtime_builder import DirectV2RuntimeFactory

PACK_ID = "norman-2019-k562-golden"
PACK_VERSION = "1.0.0"
PACK_FINGERPRINT = "42165e430bab3474cdc9e607770ff5e204608c4243f84e492c08e2c6442c55ee"
MODEL_NAME = "norman_additive_linear"
MODEL_VERSION = "1.0.0-research.1"
SOURCE_CARD_FINGERPRINT = "eaaf8e7cc3ee0c3c74eb492ac6df77fa2c7edf73576c190d7c9a59c613159b6b"
CONTRACT_FINGERPRINT = "f34afa761239abc97033c78bb9d0c29a1c36a4c7d1a106a9cbbaa805a5196ff5"
FEATURE_IDS_SHA256 = "ecca6c636629e35ae5f5a0ec6fe84c1a7983e1adb263fbbcaea70a0c5495b2b7"
MATCHED_CONTROL_SHA256 = "2fc6ba835e3a9353345651b9369abdd189c6017a854932c038b157faa4b378ae"
CONTROL_ASSIGNMENT_SHA256 = "8f09650026e297ce0e010120814230bc7de306364ab49316b7c102e836c6e3d5"
SOURCE_REAL_RUN_SHA256 = "fe82a306ff2ecdb42d2da9abc5fb9007c9c46ecf1051734789da5afb0598f52d"
AHR = "ENSG00000106546"
KLF1 = "ENSG00000105610"
CONDITION_ID = "AHR+KLF1"

_ARTIFACTS = {
    "baseline.json": (
        "b82dc7ab26c6f6fdef4414f6b05c51edb32b2a35e4c00f45824cc839ab9cf1a9",
        95682,
        "application/json",
    ),
    "linear_coefficients.npy": (
        "241210fb33b0abb86f923478870f9d19711c31e4a721fc5d60888d61900b86c4",
        4237928,
        "application/x-npy",
    ),
    "linear_intercept.npy": (
        "6a870efd9f97b599769069aec95bcf2f920acedf43aa1d24740a7e5b40e7fac2",
        40488,
        "application/x-npy",
    ),
}
_SOURCE_CARD = "registrations/golden_additive_source_card.yaml"
_RELEASE_PIN = "registrations/golden_additive_research_release.json"
_ARTIFACT_SNAPSHOT_BUDGET = {
    "schema_version": "vc.artifact-snapshot-budget-policy.v1",
    "max_live_snapshot_payload_bytes": sum(item[1] for item in _ARTIFACTS.values()),
    "max_snapshot_entries_per_execution": len(_ARTIFACTS),
    "retention_scope": "execution_only",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_source_tree_sha256() -> str:
    package_root = Path(__file__).parents[1]
    records: dict[str, str] = {}
    for path in sorted(package_root.rglob("*")):
        relative = path.relative_to(package_root)
        if (
            path.is_dir()
            or relative == Path("model_zoo") / _RELEASE_PIN
            or "tests" in relative.parts
            or "__pycache__" in relative.parts
            or path.name.startswith("._")
        ):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("Golden package source tree contains an unsafe entry")
        records[relative.as_posix()] = _file_sha256(path)
    if not records:
        raise ValueError("Golden package source tree is empty")
    return _fingerprint(records)


def _scope_fingerprint() -> str:
    return _fingerprint(
        {
            "schema_version": "vc.golden-additive-research-scope.v1",
            "pack_fingerprint": PACK_FINGERPRINT,
            "condition_id": CONDITION_ID,
            "partition": "test",
            "ordered_target_ids": [AHR, KLF1],
            "perturbation_action": "CRISPR activation",
            "dose_value": 1.0,
            "dose_unit": "1",
            "timepoint": "5d",
            "reference": "matched_split_control_mean_X",
            "feature_ids_sha256": FEATURE_IDS_SHA256,
        }
    )


def golden_ahr_klf1_request(
    request_id: str = "golden-norman-ahr-klf1-research",
) -> VirtualCellRequestV2:
    """Build the sole request authorized by this first research release."""

    return VirtualCellRequestV2.from_dict(
        {
            "schema_version": "vc.request.v2",
            "request_id": request_id,
            "species": {
                "schema_version": "vc.species-ref.v1",
                "taxonomy_id": "NCBITaxon:9606",
                "scientific_name": "Homo sapiens",
                "common_name": "human",
            },
            "cell_context": {
                "schema_version": "vc.cell-context.v1",
                "cell_type_name": "K562",
                "cell_type_id": None,
                "tissue_name": None,
                "tissue_id": None,
                "attributes": {
                    "cell_identity_id": "CVCL_0004",
                    "assembly_name": "GRCh38",
                    "assembly_accession": "GCA_000001405.15",
                    "assay_id": "EFO:0008913",
                    "feature_namespace_version": "Ensembl 84",
                    "feature_ids_sha256": FEATURE_IDS_SHA256,
                    "evaluation_scope": "combination",
                },
            },
            "input_modality": {
                "schema_version": "vc.modality.v1",
                "name": "scRNA",
                "ontology_id": "EFO:0008913",
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "output_modality": {
                "schema_version": "vc.modality.v1",
                "name": "delta_expression",
                "ontology_id": "PRAXISOUTPUT:delta_expression",
                "unit": None,
                "feature_namespace": "EnsemblGene",
            },
            "perturbation": {
                "schema_version": "vc.perturbation.v1",
                "kind": "gene_combination",
                "targets": [AHR, KLF1],
                "dose_value": 1.0,
                "dose_unit": "1",
                "timepoint": "5d",
            },
            "task": {
                "schema_version": "vc.task.v1",
                "task_type": "predict_delta_expression",
                "requested_outputs": ["delta_expression"],
            },
            "baseline_context": {
                "reference": "matched_split_control_mean_X",
                "source_control_condition": "ctrl",
                "matched_control_sha256": MATCHED_CONTROL_SHA256,
                "control_assignment_sha256": CONTROL_ASSIGNMENT_SHA256,
                "scope_fingerprint": _scope_fingerprint(),
            },
            "metadata": {},
            "constraints": {
                "condition_id": CONDITION_ID,
                "partition": "test",
                "source_real_run_sha256": SOURCE_REAL_RUN_SHA256,
                "execution_scope": "research_only",
            },
        }
    )


class GoldenAdditiveResearchAdapter(DeltaExpressionReferenceAdapter):
    """Exact path-free adapter for the first AHR+KLF1 research release."""

    adapter_id = "golden-additive-ahr-klf1-research"
    version = "1.0.0"
    input_contract = AdapterInputContract(
        schema_version="vc.adapter-input-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(1,),
        unit=None,
        pack_data_required=False,
        alignment_required=False,
    )
    output_contract = AdapterOutputContract(
        schema_version="vc.adapter-output-contract.v1",
        task="predict_delta_expression",
        output="delta_expression",
        value_type="float",
        shape=(5045,),
        unit=None,
        uncertainty_required=True,
        ood_required=True,
        abstain_allowed=True,
    )

    def prepare_input(
        self,
        request: VirtualCellRequestV2,
        *,
        pack=None,
        compatibility_report=None,
        **kwargs,
    ) -> PreparedAdapterInput:
        if kwargs:
            raise AdapterContractError("Golden research adapter accepts no caller-provided data")
        if type(request) is not VirtualCellRequestV2:
            raise TypeError("request must be an exact VirtualCellRequestV2")
        if type(pack) is not PreparedPackViewV1 or hasattr(pack, "root"):
            raise AdapterContractError("Golden research adapter requires a path-free Pack view")
        if type(compatibility_report) is not CompatibilityReportV2:
            raise AdapterContractError("Golden research adapter requires an exact compatibility report")
        try:
            observed_request = request
            _reject_undeclared_model_fields(request, "request")
            request = VirtualCellRequestV2.model_validate(request.model_dump(mode="python", serialize_as_any=True))
            _reject_model_type_drift(observed_request, request, "request")
            observed_report = compatibility_report
            _reject_undeclared_model_fields(compatibility_report, "compatibility report")
            compatibility_report = CompatibilityReportV2.from_dict(compatibility_report.to_dict())
            _reject_model_type_drift(
                observed_report,
                compatibility_report,
                "compatibility report",
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as exc:
            raise AdapterContractError("invalid Golden research binding") from exc

        if request.to_dict() != golden_ahr_klf1_request(request.request_id).to_dict():
            raise AdapterContractError("request is outside the exact AHR+KLF1 research scope")
        request_fingerprint = _fingerprint(request.to_dict())
        if not (
            pack.pack_id == PACK_ID
            and pack.pack_version == PACK_VERSION
            and pack.fingerprint == PACK_FINGERPRINT
            and pack.taxonomy_id == "NCBITaxon:9606"
            and pack.assembly_accession == "GCA_000001405.15"
            and compatibility_report.request_id == request.request_id
            and compatibility_report.request_fingerprint == request_fingerprint
            and compatibility_report.model_name == MODEL_NAME
            and compatibility_report.model_version == MODEL_VERSION
            and compatibility_report.model_fingerprint == _release_pin()["model_fingerprint"]
            and compatibility_report.pack_id == PACK_ID
            and compatibility_report.pack_version == PACK_VERSION
            and compatibility_report.pack_fingerprint == PACK_FINGERPRINT
            and compatibility_report.environment_fingerprint == _release_pin()["environment_fingerprint"]
            and compatibility_report.adapter_fingerprints == (self.fingerprint(),)
            and compatibility_report.artifact_fingerprints
            == tuple(item["fingerprint"] for item in _release_pin()["artifacts"])
        ):
            raise AdapterContractError("compatibility report is outside the Golden release")
        if not (
            compatibility_report.policy_present
            and compatibility_report.release_fingerprint == _release_pin()["release_fingerprint"]
            and compatibility_report.capability_fingerprint == _release_pin()["capability_fingerprint"]
            and compatibility_report.executable
            and compatibility_report.research_execution_authorized is True
            and compatibility_report.research_execution_scope == "research_only"
            and compatibility_report.evidence_fingerprints == (_release_pin()["evidence_fingerprint"],)
            and compatibility_report.policy_fingerprint == _release_pin()["policy_fingerprint"]
            and compatibility_report.production_promoted is False
            and compatibility_report.benchmark_passed is False
            and compatibility_report.scientifically_validated is False
            and compatibility_report.promotion_eligible is False
        ):
            raise AdapterContractError("Golden research policy state drift")

        return PreparedAdapterInput(
            schema_version="vc.prepared-adapter-input.v1",
            adapter_fingerprint=self.fingerprint(),
            input_contract_fingerprint=self.input_contract.fingerprint(),
            task=self.input_contract.task,
            output=self.input_contract.output,
            request_fingerprint=request_fingerprint,
            pack_fingerprint=pack.fingerprint,
            compatibility_fingerprint=compatibility_report.fingerprint(),
            model_input={
                "request_id": request.request_id,
                "targets": [AHR, KLF1],
                "perturbation_kind": "gene_combination",
                "condition_id": CONDITION_ID,
                "partition": "test",
                "perturbation_action": "CRISPR activation",
                "dose_value": 1.0,
                "dose_unit": "1",
                "timepoint": "5d",
                "baseline_reference": "matched_split_control_mean_X",
                "request_fingerprint": request_fingerprint,
                "pack_fingerprint": pack.fingerprint,
                "compatibility_fingerprint": compatibility_report.fingerprint(),
                "adapter_fingerprint": self.fingerprint(),
            },
            values=None,
            shape=None,
            unit=None,
            feature_contract=None,
            feature_contract_fingerprint=None,
            alignment_report=None,
        )

    def adapt_output(
        self,
        prepared: PreparedAdapterInput,
        raw_output: dict[str, Any],
    ) -> AdapterOutputEnvelope:
        envelope = super().adapt_output(prepared, raw_output)
        if envelope.abstain:
            if envelope.ood is None or not envelope.ood.detected:
                raise AdapterContractError("Golden abstention requires explicit OOD")
            return envelope
        metadata = envelope.to_dict()["projection_metadata"]
        if metadata != {
            "baseline": "additive_linear",
            "feature_ids_sha256": FEATURE_IDS_SHA256,
            "n_features": 5045,
            "unseen_train_targets": [],
            "value_type": "delta_expression",
        }:
            raise AdapterContractError("Golden prediction metadata drift")
        uncertainty = envelope.uncertainty
        if not (
            uncertainty is not None
            and uncertainty.available is False
            and uncertainty.method == "point_estimate"
            and uncertainty.calibrated is False
            and uncertainty.value is None
            and uncertainty.sigma is None
        ):
            raise AdapterContractError("Golden uncertainty state drift")
        if not (
            envelope.ood is not None
            and envelope.ood.detected is False
            and envelope.ood.dimensions == ()
            and envelope.ood.reason is None
        ):
            raise AdapterContractError("Golden OOD state drift")
        return envelope


def _predict_artifact_bytes(snapshots: dict[str, bytes], targets: tuple[str, ...]):
    import numpy as np

    if targets != (AHR, KLF1):
        raise ValueError("prediction is outside the registered AHR+KLF1 scope")
    if set(snapshots) != set(_ARTIFACTS) or any(not isinstance(value, bytes) for value in snapshots.values()):
        raise ValueError("broker did not provide the complete Golden artifact snapshot")
    for name, data in snapshots.items():
        if hashlib.sha256(data).hexdigest() != _ARTIFACTS[name][0]:
            raise ValueError(f"Golden artifact changed before execution: {name}")
    try:
        metadata = json.loads(snapshots["baseline.json"])
        coefficients = np.load(io.BytesIO(snapshots["linear_coefficients.npy"]), allow_pickle=False)
        intercept = np.load(io.BytesIO(snapshots["linear_intercept.npy"]), allow_pickle=False)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Golden artifact snapshot is invalid") from exc
    target_ids = metadata.get("target_ids")
    feature_ids = metadata.get("feature_ids")
    seen = metadata.get("seen_train_target_ids")
    if not (
        metadata.get("schema_version") == "vc.golden-baseline.v1"
        and metadata.get("baseline") == "additive_linear"
        and metadata.get("model_name") == MODEL_NAME
        and metadata.get("pack")
        == {
            "fingerprint": PACK_FINGERPRINT,
            "id": PACK_ID,
            "version": PACK_VERSION,
        }
        and metadata.get("contract_sha256") == CONTRACT_FINGERPRINT
        and isinstance(target_ids, list)
        and isinstance(feature_ids, list)
        and isinstance(seen, list)
        and _fingerprint(target_ids) == metadata.get("target_ids_sha256")
        and _fingerprint(feature_ids) == FEATURE_IDS_SHA256
        and coefficients.shape == (len(target_ids), 5045)
        and intercept.shape == (5045,)
        and coefficients.dtype == np.dtype("float64")
        and intercept.dtype == np.dtype("float64")
        and np.isfinite(coefficients).all()
        and np.isfinite(intercept).all()
        and all(target in target_ids for target in targets)
    ):
        raise ValueError("Golden artifact semantic identity drift")
    unseen = [target for target in targets if target not in seen]
    design = np.zeros(len(target_ids), dtype=np.float64)
    positions = {target: index for index, target in enumerate(target_ids)}
    for target in targets:
        design[positions[target]] = 1.0
    delta = intercept + design @ coefficients
    if delta.shape != (5045,) or not np.isfinite(delta).all():
        raise ValueError("Golden research prediction violates the output contract")
    return delta, unseen


def _predict_snapshot(asset_paths: dict[str, str], targets: tuple[str, ...]):
    try:
        snapshots = {name: Path(asset_paths[name]).read_bytes() for name in _ARTIFACTS}
    except (KeyError, OSError) as exc:
        raise ValueError("broker did not provide the complete Golden artifact set") from exc
    return _predict_artifact_bytes(snapshots, targets)


class GoldenAdditiveResearchWrapper(ModelWrapper):
    """Broker-bound wrapper that abstains on targets unseen during training."""

    name = MODEL_NAME
    artifact_snapshot_supported = True

    def declare_scope(self) -> dict:
        return {
            "species": ["human"],
            "cell_identity": "CVCL_0004",
            "module": "genetic_hub",
            "task": ["predict_delta_expression"],
            "perturbation": ["gene_combination"],
            "condition": [CONDITION_ID],
            "execution_scope": "research_only",
        }

    def run_prediction(self, model_input: dict) -> dict:
        if not isinstance(model_input, dict) or (
            tuple(model_input.get("targets", ())) != (AHR, KLF1)
            or model_input.get("condition_id") != CONDITION_ID
            or model_input.get("partition") != "test"
            or model_input.get("perturbation_action") != "CRISPR activation"
        ):
            raise ValueError("wrapper input is outside the registered AHR+KLF1 scope")
        delta, unseen = _predict_artifact_bytes(
            self.capability_asset_bytes,
            tuple(model_input["targets"]),
        )
        uncertainty = {
            "method": "point_estimate",
            "available": False,
            "calibrated": False,
            "value": None,
            "sigma": None,
            "reason": "additive baseline has no calibrated predictive uncertainty",
        }
        if unseen:
            return {
                "prediction": None,
                "uncertainty": uncertainty,
                "ood": {
                    "detected": True,
                    "dimensions": ["perturbation"],
                    "reason": "target_unseen_in_training",
                },
                "abstain": True,
                "abstain_reasons": ["golden_target_unseen_in_training"],
                "evidence": ["golden_norman_hash_locked_baseline"],
                "policy": {"execution_scope": "research_only"},
                "provenance": {
                    "model_version": self.model_version,
                    "scientifically_validated": False,
                    "production_promoted": False,
                },
            }
        return {
            "prediction": {
                "delta": delta.tolist(),
                "baseline": "additive_linear",
                "feature_ids_sha256": FEATURE_IDS_SHA256,
                "n_features": 5045,
                "value_type": "delta_expression",
                "unseen_train_targets": [],
            },
            "uncertainty": uncertainty,
            "ood": {"detected": False, "dimensions": [], "reason": None},
            "abstain": False,
            "abstain_reasons": [],
            "evidence": ["golden_norman_hash_locked_baseline"],
            "policy": {"execution_scope": "research_only"},
            "provenance": {
                "model_version": self.model_version,
                "scientifically_validated": False,
                "production_promoted": False,
            },
        }


@dataclass(frozen=True)
class GoldenAdditiveResearchRegistration:
    root: Path
    receipt: dict[str, Any]
    registry: ModelZooRegistry
    pack_registry: PackRegistry
    cache: ModelCache
    environment: EnvironmentSnapshot
    adapter: GoldenAdditiveResearchAdapter
    wrapper_registry: WrapperRegistry

    def factory(self) -> DirectV2RuntimeFactory:
        return DirectV2RuntimeFactory(
            registry=self.registry,
            cache=self.cache,
            pack_registry=self.pack_registry,
            environment=self.environment,
            adapter_registry=AdapterRegistry([self.adapter]),
            wrapper_registry=self.wrapper_registry,
        )


def _resource_text(name: str) -> str:
    try:
        return importlib.resources.files("praxis_virtualcell.model_zoo").joinpath(name).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError("Golden research package data is unavailable") from exc


def _research_card() -> ModelCard:
    try:
        value = yaml.safe_load(_resource_text(_SOURCE_CARD))
        source = ModelCard.from_dict(value["models"][MODEL_NAME])
    except (KeyError, TypeError, ValidationError, yaml.YAMLError) as exc:
        raise ValueError("invalid Golden research source card") from exc
    if source.fingerprint() != SOURCE_CARD_FINGERPRINT:
        raise ValueError("frozen P8 source card fingerprint drift")
    value = source.to_dict()
    value.update(
        {
            "version": MODEL_VERSION,
            "source": "local:golden-norman-research-release",
            "wrapper": ("praxis_virtualcell.model_zoo.golden_additive_research.GoldenAdditiveResearchWrapper"),
            "perturbation": ["gene_combination"],
            "requires": ["numpy", "yaml"],
            "resources": {
                "python_dependencies": ["numpy", "yaml"],
                "required": ["cpu"],
            },
            "reliability_policy": "research_only_exact_ahr_klf1_or_abstain",
            "provenance": {
                **value["provenance"],
                "source_card_fingerprint": SOURCE_CARD_FINGERPRINT,
                "authorized_condition": CONDITION_ID,
                "source_real_run_sha256": SOURCE_REAL_RUN_SHA256,
                "execution_scope": "research_only",
                "scientifically_validated": False,
                "production_promoted": False,
            },
        }
    )
    card = ModelCard.from_dict(value)
    if card.fingerprint() != _release_pin()["model_fingerprint"]:
        raise ValueError("Golden research card identity drift")
    return card


def _runtime_lock(adapter: GoldenAdditiveResearchAdapter) -> dict[str, Any]:
    packages = []
    for distribution, module in (
        ("numpy", "numpy"),
        ("pydantic", "pydantic"),
        ("pydantic-core", "pydantic_core"),
        ("praxis-virtualcell", "praxis_virtualcell"),
        ("pyyaml", "yaml"),
    ):
        module_value = __import__(module)
        module_version = getattr(module_value, "__version__", None)
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ValueError(f"{distribution} distribution metadata is unavailable") from exc
        if not isinstance(module_version, str) or not module_version or module_version != version:
            raise ValueError(f"{distribution} module/distribution version drift")
        if not version:
            raise ValueError(f"{distribution} runtime version is unavailable")
        packages.append({"name": distribution, "version": version})
    implementation_files = {
        "golden_additive_research.py": Path(__file__),
        "capability_registry.py": Path(__file__).with_name("capability_registry.py"),
        "registry_v2.py": Path(__file__).with_name("registry_v2.py"),
        "wrapper_registry.py": Path(__file__).with_name("wrapper_registry.py"),
        "wrappers/base.py": Path(__file__).with_name("wrappers") / "base.py",
        "core/runtime.py": Path(__file__).parents[1] / "core" / "runtime.py",
        "workflows/runtime_builder.py": Path(__file__).parents[1] / "workflows" / "runtime_builder.py",
    }
    return {
        "schema_version": "vc.golden-research-environment-lock.v1",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "cpu_architecture": platform.machine(),
        "packages": packages,
        "package_source_tree_sha256": _package_source_tree_sha256(),
        "selected_implementation_sha256": {name: _file_sha256(path) for name, path in implementation_files.items()},
        "resources": ["cpu"],
        "accelerators": [],
        "adapter_fingerprint": adapter.fingerprint(),
    }


def _release_pin() -> dict[str, Any]:
    try:
        value = json.loads(_resource_text(_RELEASE_PIN))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid Golden research release pin") from exc
    if not isinstance(value, dict) or value.get("schema_version") != ("vc.golden-additive-research-release-pin.v1"):
        raise ValueError("unsupported Golden research release pin")
    return value


def _strict_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Golden registration file is unavailable: {path.name}")

    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("non-finite JSON value")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid Golden registration file: {path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Golden registration file must contain an object: {path.name}")
    return value


def _validate_release_pin(
    receipt: dict[str, Any],
    runtime_lock: dict[str, Any],
) -> None:
    pin = _release_pin()
    expected = {
        **receipt,
        "schema_version": pin["schema_version"],
        "environment_lock_fingerprint": _fingerprint(runtime_lock),
        "source_real_run_sha256": SOURCE_REAL_RUN_SHA256,
        "runtime": {
            key: runtime_lock[key]
            for key in (
                "python_implementation",
                "python_version",
                "cpu_architecture",
                "packages",
            )
        },
    }
    if pin != expected:
        raise ValueError("Golden research release differs from the checked-in trust pin")


def _validate_source_run(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or _file_sha256(path) != SOURCE_REAL_RUN_SHA256:
        raise ValueError("source real-run receipt identity drift")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("source real-run receipt is unreadable") from exc
    if not (
        value.get("schema_version") == "vc.golden-condition-run.v1"
        and value.get("record_role") == "held_out_real_data_baseline_not_scientific_evidence"
        and value.get("pack") == {"fingerprint": PACK_FINGERPRINT, "id": PACK_ID, "version": PACK_VERSION}
        and value.get("condition", {}).get("id") == CONDITION_ID
        and value.get("condition", {}).get("partition") == "test"
        and value.get("condition", {}).get("targets") == [AHR, KLF1]
        and value.get("prediction", {}).get("feature_ids_sha256") == FEATURE_IDS_SHA256
        and value.get("states", {}).get("real_data_used") is True
        and value.get("states", {}).get("execution_performed") is True
        and value.get("states", {}).get("scientifically_validated") is False
        and value.get("states", {}).get("production_promoted") is False
        and value.get("states", {}).get("benchmark_evidence_created") is False
        and value.get("states", {}).get("policy_changed") is False
    ):
        raise ValueError("source real-run receipt exceeds the research evidence ceiling")
    return value


def _artifact_identities(card: ModelCard, cache: ModelCache) -> tuple[ArtifactIdentity, ...]:
    records = []
    for asset in card.assets:
        try:
            sha256, size_bytes, media_type = _ARTIFACTS[asset.filename]
        except KeyError as exc:
            raise ValueError("research card contains an unregistered artifact") from exc
        if (asset.sha256, asset.media_type) != (sha256, media_type):
            raise ValueError("research card artifact identity drift")
        path = cache.asset_path(card.name, asset.filename)
        status = cache.check(
            card.name,
            asset.filename,
            sha256=sha256,
            size_bytes=size_bytes,
        )
        if path.is_symlink() or not status.available or status.path is None:
            raise ValueError(f"model artifact unavailable: {asset.filename}")
        records.append(
            ArtifactIdentity.from_dict(
                {
                    "schema_version": "vc.model-artifact.v1",
                    "artifact_id": f"{card.name}:{asset.filename}",
                    "model_fingerprint": card.fingerprint(),
                    "uri": None,
                    "cache_key": f"{card.name}/{asset.filename}",
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                    "media_type": media_type,
                    "license": "CC0-1.0",
                    "source": "Golden Norman deterministic training partition",
                    "safe_load_policy": "data_only",
                    "legacy_incomplete": False,
                }
            )
        )
    if len(records) != len(_ARTIFACTS):
        raise ValueError("research release requires exactly three artifacts")
    return tuple(records)


def _release(
    card: ModelCard,
    pack_fingerprint: str,
    artifacts: tuple[ArtifactIdentity, ...],
    environment: EnvironmentIdentity,
    adapter: GoldenAdditiveResearchAdapter,
    evidence_fingerprints: tuple[str, ...],
    policy_fingerprint: str | None,
) -> ModelReleaseRecord:
    return ModelReleaseRecord.from_dict(
        {
            "schema_version": "vc.model-release.v1",
            "release_id": f"{MODEL_NAME}@{MODEL_VERSION}",
            "model_name": card.name,
            "model_version": card.version,
            "model_fingerprint": card.fingerprint(),
            "pack_fingerprints": [pack_fingerprint],
            "artifact_fingerprints": [item.fingerprint() for item in artifacts],
            "environment_fingerprint": environment.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "evidence_fingerprints": list(evidence_fingerprints),
            "policy_fingerprint": policy_fingerprint,
            "migration_status": "native",
            "legacy_status": None,
            "incomplete_reasons": [],
        }
    )


def _technical_evidence(
    source_run: dict[str, Any],
    request: VirtualCellRequestV2,
    card: ModelCard,
    pack,
    environment: EnvironmentIdentity,
    adapter: GoldenAdditiveResearchAdapter,
    delta: list[float],
) -> dict[str, Any]:
    delta_sha256 = _fingerprint(delta)
    if source_run["prediction"].get("sha256") != delta_sha256:
        raise ValueError("exact adapter replay differs from the retained real run")
    return {
        "schema_version": "vc.golden-research-technical-evidence.v1",
        "record_role": "artifact_replay_conformance_not_scientific_evidence",
        "source_real_run_sha256": SOURCE_REAL_RUN_SHA256,
        "request_fingerprint": _fingerprint(request.to_dict()),
        "pack_fingerprint": pack.fingerprint,
        "model_fingerprint": card.fingerprint(),
        "environment_fingerprint": environment.fingerprint(),
        "adapter_fingerprint": adapter.fingerprint(),
        "prediction_sha256": delta_sha256,
        "source_prediction_exact_match": True,
        "n_features": 5045,
        "feature_ids_sha256": FEATURE_IDS_SHA256,
        "benchmark_passed": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }


def register_golden_additive_research(
    *,
    pack_root: str | Path,
    model_cache_root: str | Path,
    source_real_run: str | Path,
    output_dir: str | Path,
) -> GoldenAdditiveResearchRegistration:
    """Validate, register, and persist the first real research-only model."""

    raw_output = Path(output_dir)
    if raw_output.is_symlink() or os.path.lexists(raw_output):
        raise ValueError("registration output must be a new non-symlink path")
    output = raw_output.resolve()
    if not output.is_absolute() or not output.parent.is_dir():
        raise ValueError("registration output parent must already exist")
    raw_pack = Path(pack_root)
    raw_cache = Path(model_cache_root)
    if raw_pack.is_symlink() or raw_cache.is_symlink():
        raise ValueError("Pack and cache roots must not be symlinks")
    pack_root = raw_pack.resolve(strict=True)
    model_cache_root = raw_cache.resolve(strict=True)
    raw_source_run = Path(source_real_run)
    if raw_source_run.is_symlink():
        raise ValueError("source real-run receipt must not be a symlink")
    source_real_run = raw_source_run.resolve(strict=True)

    source_run = _validate_source_run(source_real_run)
    card = _research_card()
    adapter = GoldenAdditiveResearchAdapter()
    cache = ModelCache(root=str(model_cache_root))
    artifacts = _artifact_identities(card, cache)
    packs = PackRegistry()
    manifest = packs.register(pack_root)
    pack = packs.record(PACK_ID, PACK_VERSION)
    if manifest.fingerprint() != PACK_FINGERPRINT or pack.fingerprint != PACK_FINGERPRINT:
        raise ValueError("Golden Pack fingerprint drift")

    runtime_lock = _runtime_lock(adapter)
    package_records = tuple(PackageIdentity(**item) for item in runtime_lock["packages"])
    environment_identity = EnvironmentIdentityV2.from_dict(
        {
            "schema_version": "vc.model-environment.v2",
            "environment_id": "golden-norman-research-local-cpu",
            "python_version": runtime_lock["python_version"],
            "cpu_architecture": runtime_lock["cpu_architecture"],
            "packages": [item.to_dict() for item in package_records],
            "lock_digest": _fingerprint(runtime_lock),
            "image_digest": None,
            "resources": ["cpu"],
            "accelerators": [],
            "adapter_fingerprints": [adapter.fingerprint()],
            "legacy_incomplete": False,
            "artifact_snapshot_budget_policy": _ARTIFACT_SNAPSHOT_BUDGET,
        }
    )
    environment = EnvironmentSnapshot.from_dict(
        {
            "schema_version": "vc.environment.v3",
            "python_dependencies": ["numpy", "yaml"],
            "resources": ["cpu"],
            "runtime_tasks": ["predict_delta_expression"],
            "runtime_outputs": ["delta_expression"],
            "identity": environment_identity.to_dict(),
        }
    )
    asset_paths = {filename: str(cache.asset_path(card.name, filename)) for filename in _ARTIFACTS}
    delta, unseen = _predict_snapshot(asset_paths, (AHR, KLF1))
    if unseen:
        raise ValueError("authorized Golden targets were not seen during training")
    request = golden_ahr_klf1_request()
    technical_evidence = _technical_evidence(
        source_run,
        request,
        card,
        pack,
        environment_identity,
        adapter,
        delta.tolist(),
    )
    technical_evidence_sha256 = _fingerprint(technical_evidence)
    evidence = ValidationEvidence.from_dict(
        {
            "schema_version": "vc.model-validation-evidence.v1",
            "evidence_id": "norman-additive-ahr-klf1-artifact-replay",
            "pack_fingerprint": pack.fingerprint,
            "model_fingerprint": card.fingerprint(),
            "environment_fingerprint": environment_identity.fingerprint(),
            "adapter_fingerprints": [adapter.fingerprint()],
            "protocol_fingerprint": CONTRACT_FINGERPRINT,
            "baseline_fingerprint": _ARTIFACTS["baseline.json"][0],
            "metric_name": "exact_artifact_replay_match",
            "metric_direction": "higher_is_better",
            "result_sha256": technical_evidence_sha256,
            "benchmark_passed": False,
            "scientifically_validated": False,
            "promotion_eligible": False,
            "legacy_incomplete": False,
            "binding_errors": [],
        }
    )
    release_without_policy = _release(
        card,
        pack.fingerprint,
        artifacts,
        environment_identity,
        adapter,
        (evidence.fingerprint(),),
        None,
    )
    policy = OperatorPolicyRecordV2.from_dict(
        {
            "schema_version": "vc.model-operator-policy.v2",
            "policy_id": "norman-additive-ahr-klf1-local-research",
            "capability_fingerprint": release_without_policy.capability_fingerprint(),
            "evidence_fingerprints": [evidence.fingerprint()],
            "production_promoted": False,
            "research_execution_authorized": True,
            "research_execution_scope": "research_only",
            "decision_kind": "operator_decision",
            "operator_id": "local-project-operator",
            "decided_at": "2026-08-12T00:00:00Z",
            "reason": (
                "Local non-clinical AHR+KLF1 research execution only; no scientific validation or production promotion"
            ),
        }
    )
    release = _release(
        card,
        pack.fingerprint,
        artifacts,
        environment_identity,
        adapter,
        (evidence.fingerprint(),),
        policy.fingerprint(),
    )
    cataloged = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "norman-additive-ahr-klf1-cataloged",
            "sequence": 1,
            "previous_event_fingerprint": None,
            "release_fingerprint": release.fingerprint(),
            "action": "cataloged",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-12T00:00:01Z",
            "operator_id": "local-project-operator",
            "reason": "Catalog exact Golden research-only release",
        }
    )
    ready = RegistryLifecycleEvent.from_dict(
        {
            "schema_version": "vc.model-registry-event.v1",
            "event_id": "norman-additive-ahr-klf1-artifact-ready",
            "sequence": 2,
            "previous_event_fingerprint": cataloged.fingerprint(),
            "release_fingerprint": release.fingerprint(),
            "action": "artifact_ready",
            "target_release_fingerprint": None,
            "recorded_at": "2026-08-12T00:00:02Z",
            "operator_id": "local-project-operator",
            "reason": "All three local data-only artifacts passed exact size and SHA-256 checks",
        }
    )
    registry_v2 = ModelRegistryV2.from_dict(
        {
            "schema_version": "vc.model-registry.v2",
            "artifacts": [item.to_dict() for item in artifacts],
            "environments": [environment_identity.to_dict()],
            "adapters": [adapter.identity().to_dict()],
            "evidence_records": [evidence.to_dict()],
            "policy_records": [policy.to_dict()],
            "releases": [release.to_dict()],
            "lifecycle_events": [cataloged.to_dict(), ready.to_dict()],
        }
    )
    receipt = {
        "schema_version": "vc.golden-additive-research-registration.v1",
        "model_name": card.name,
        "model_version": card.version,
        "model_fingerprint": card.fingerprint(),
        "release_fingerprint": release.fingerprint(),
        "capability_fingerprint": release.capability_fingerprint(),
        "registry_fingerprint": registry_v2.fingerprint(),
        "pack_fingerprint": pack.fingerprint,
        "environment_fingerprint": environment_identity.fingerprint(),
        "adapter_fingerprint": adapter.fingerprint(),
        "evidence_fingerprint": evidence.fingerprint(),
        "policy_fingerprint": policy.fingerprint(),
        "technical_evidence_sha256": technical_evidence_sha256,
        "artifacts": [
            {
                "artifact_id": item.artifact_id,
                "fingerprint": item.fingerprint(),
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "safe_load_policy": item.safe_load_policy,
            }
            for item in artifacts
        ],
        "cataloged": True,
        "artifact_ready": True,
        "research_execution_authorized": True,
        "research_execution_scope": "research_only",
        "benchmark_passed": False,
        "scientifically_validated": False,
        "promotion_eligible": False,
        "production_promoted": False,
    }
    _validate_release_pin(receipt, runtime_lock)

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        (temporary / "registry.yaml").write_text(
            yaml.safe_dump(
                {
                    "models": {card.name: card.to_dict()},
                    "registry_v2": registry_v2.to_dict(),
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        for filename, value in (
            ("environment-lock.json", runtime_lock),
            ("technical-evidence.json", technical_evidence),
            ("registration.json", receipt),
        ):
            (temporary / filename).write_bytes(_canonical_bytes(value) + b"\n")

        zoo = ModelZooRegistry(registry_path=str(temporary / "registry.yaml"))
        wrappers = WrapperRegistry()
        wrappers.register(card.wrapper, GoldenAdditiveResearchWrapper)
        candidate = GoldenAdditiveResearchRegistration(
            root=temporary,
            receipt=receipt,
            registry=zoo,
            pack_registry=packs,
            cache=cache,
            environment=environment,
            adapter=adapter,
            wrapper_registry=wrappers,
        )
        smoke = (
            candidate.factory()
            .build()
            .run_workflow_v2(
                request,
                pack_id=PACK_ID,
                pack_version=PACK_VERSION,
            )
        )
        values = (smoke.get("prediction") or {}).get("values")
        if not (
            smoke.get("abstain") is False
            and smoke.get("models_used") == [MODEL_NAME]
            and smoke.get("execution_scope") == "research_only"
            and smoke.get("scientifically_validated") is False
            and isinstance(values, list)
            and len(values) == 5045
            and _fingerprint(values) == technical_evidence["prediction_sha256"]
            and smoke.get("provenance", {}).get("execution_plan", {}).get("reports", [{}])[0].get("production_promoted")
            is False
        ):
            raise ValueError("final Golden Direct-v2 registration smoke failed")
        if os.path.lexists(output):
            raise ValueError("registration output appeared during construction")
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    final_zoo = ModelZooRegistry(registry_path=str(output / "registry.yaml"))
    return GoldenAdditiveResearchRegistration(
        root=output,
        receipt=receipt,
        registry=final_zoo,
        pack_registry=packs,
        cache=cache,
        environment=environment,
        adapter=adapter,
        wrapper_registry=wrappers,
    )


def load_golden_additive_research(
    *,
    registration_root: str | Path,
    pack_root: str | Path,
    model_cache_root: str | Path,
) -> GoldenAdditiveResearchRegistration:
    """Reopen one exact checked-in research release for CLI/API execution."""

    raw_registration = Path(registration_root)
    raw_pack = Path(pack_root)
    raw_cache = Path(model_cache_root)
    if any(path.is_symlink() for path in (raw_registration, raw_pack, raw_cache)):
        raise ValueError("Golden runtime roots must not be symlinks")
    registration = raw_registration.resolve(strict=True)
    pack_root = raw_pack.resolve(strict=True)
    model_cache_root = raw_cache.resolve(strict=True)
    if not registration.is_dir() or not pack_root.is_dir() or not model_cache_root.is_dir():
        raise ValueError("Golden runtime roots must be directories")

    adapter = GoldenAdditiveResearchAdapter()
    runtime_lock = _runtime_lock(adapter)
    stored_lock = _strict_json_object(registration / "environment-lock.json")
    receipt = _strict_json_object(registration / "registration.json")
    technical_evidence = _strict_json_object(registration / "technical-evidence.json")
    if stored_lock != runtime_lock:
        raise ValueError("Golden registration environment lock differs from this runtime")
    _validate_release_pin(receipt, runtime_lock)
    if not (
        _fingerprint(technical_evidence) == receipt["technical_evidence_sha256"]
        and technical_evidence.get("record_role") == "artifact_replay_conformance_not_scientific_evidence"
        and technical_evidence.get("benchmark_passed") is False
        and technical_evidence.get("scientifically_validated") is False
        and technical_evidence.get("promotion_eligible") is False
        and technical_evidence.get("production_promoted") is False
    ):
        raise ValueError("Golden technical evidence identity or status drift")

    registry_path = registration / "registry.yaml"
    if registry_path.is_symlink() or not registry_path.is_file():
        raise ValueError("Golden registry is unavailable")
    zoo = ModelZooRegistry(registry_path=str(registry_path))
    registry_v2 = zoo.registry_v2
    if not (
        isinstance(registry_v2, ModelRegistryV2)
        and registry_v2.fingerprint() == receipt["registry_fingerprint"]
        and zoo.names() == [MODEL_NAME]
        and zoo.capability_names() == [MODEL_NAME]
    ):
        raise ValueError("Golden registry identity drift")
    card = _research_card()
    if zoo.card(MODEL_NAME).fingerprint() != card.fingerprint():
        raise ValueError("Golden registry card identity drift")

    cache = ModelCache(root=str(model_cache_root))
    artifacts = _artifact_identities(card, cache)
    if tuple(item.fingerprint() for item in artifacts) != tuple(item["fingerprint"] for item in receipt["artifacts"]):
        raise ValueError("Golden runtime artifact identity drift")

    packs = PackRegistry()
    manifest = packs.register(pack_root)
    pack = packs.record(PACK_ID, PACK_VERSION)
    if manifest.fingerprint() != PACK_FINGERPRINT or pack.fingerprint != PACK_FINGERPRINT:
        raise ValueError("Golden runtime Pack identity drift")

    if len(registry_v2.environments) != 1:
        raise ValueError("Golden registry must contain exactly one environment")
    environment_identity = registry_v2.environments[0]
    if (
        type(environment_identity) is not EnvironmentIdentityV2
        or environment_identity.fingerprint() != receipt["environment_fingerprint"]
    ):
        raise ValueError("Golden runtime environment identity drift")
    environment = EnvironmentSnapshot.from_dict(
        {
            "schema_version": "vc.environment.v3",
            "python_dependencies": ["numpy", "yaml"],
            "resources": ["cpu"],
            "runtime_tasks": ["predict_delta_expression"],
            "runtime_outputs": ["delta_expression"],
            "identity": environment_identity.to_dict(),
        }
    )
    wrappers = WrapperRegistry()
    wrappers.register(card.wrapper, GoldenAdditiveResearchWrapper)
    return GoldenAdditiveResearchRegistration(
        root=registration,
        receipt=receipt,
        registry=zoo,
        pack_registry=packs,
        cache=cache,
        environment=environment,
        adapter=adapter,
        wrapper_registry=wrappers,
    )
